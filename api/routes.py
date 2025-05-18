import datetime
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from kubernetes import client, config

from app.db import SessionLocal
from app.models import TaskLog, PairStreamerStatus
from worker.tasks import download_month


# Load Kubernetes configuration
config.load_incluster_config()

router = APIRouter()


class BatchRequest(BaseModel):
    symbol: str
    start: str
    end: str
    interval: str = "1m"
    update: bool = False

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str):
        # the format should be like 'BTC-USDT'
        if not v or "-" not in v:
            raise ValueError("Symbol must be in the format 'SYMBOL-QUOTE'")

    @field_validator("start", "end")
    @classmethod
    def validate_date_format(cls, v: any):
        try:
            datetime.datetime.strptime(v, "%m-%y")
        except ValueError as exc:
            raise ValueError(f"Date '{v}' must be in the format MM-YY") from exc
        return v


@router.post("/ingest")
def ingest(req: BatchRequest):
    tasks = []

    current = datetime.datetime.strptime(req.start, "%m-%y")
    end = datetime.datetime.strptime(req.end, "%m-%y")

    while current <= end:
        task = download_month.delay(
            req.symbol, current.year, current.month, update=req.update
        )
        tasks.append({"year": current.year, "month": current.month, "task_id": task.id})
        if current.month == 12:
            current = datetime.datetime(current.year + 1, 1, 1)
        else:
            current = datetime.datetime(current.year, current.month + 1, 1)

    return {"status": "submitted", "tasks": tasks}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": str(result.result) if result.ready() else None,
    }


@router.get("/logs")
def get_logs():
    db = SessionLocal()
    logs = db.query(TaskLog).order_by(TaskLog.start_time.desc()).all()
    return [log.to_dict() for log in logs]


@router.patch("/streamer/status/{pair}")
def manage_streamer_status(pair: str, status: str):
    """Gérer le statut d'un pair-tick-streamer : créer ou activer si 'activate', désactiver si 'deactivate'."""
    if status not in ["activate", "deactivate"]:
        raise HTTPException(
            status_code=400, detail="Le statut doit être 'activate' ou 'deactivate'."
        )
    pair = pair.upper()
    k8s_apps_v1 = client.AppsV1Api()
    deployment_name = f"pair-tick-streamer-{pair.lower()}"
    namespace = "data-ingestion"
    db = SessionLocal()

    try:
        # Vérifier si le déploiement existe
        try:
            deployment = k8s_apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )
            exists = True
        except client.exceptions.ApiException as e:
            if e.status == 404:
                exists = False
            else:
                raise

        if status == "activate":
            if exists:
                # Mettre à jour le nombre de replicas à 1
                deployment.spec.replicas = 1
                k8s_apps_v1.patch_namespaced_deployment(
                    name=deployment_name, namespace=namespace, body=deployment
                )
                # DB update
                pair_status = db.query(PairStreamerStatus).filter_by(pair=pair).first()
                if pair_status:
                    pair_status.status = status
                    pair_status.updated_at = datetime.datetime.utcnow()
                else:
                    pair_status = PairStreamerStatus(pair=pair, status=status)
                    db.add(pair_status)
                db.commit()
                return {"status": "success", "message": f"Streamer activé pour {pair}."}
            else:
                # Créer le déploiement via la fonction utilitaire
                deployment = create_k8s_deployment(pair)
                k8s_apps_v1.create_namespaced_deployment(
                    namespace=namespace, body=deployment
                )
                # DB update
                pair_status = db.query(PairStreamerStatus).filter_by(pair=pair).first()
                if pair_status:
                    pair_status.status = status
                    pair_status.updated_at = datetime.datetime.utcnow()
                else:
                    pair_status = PairStreamerStatus(pair=pair, status=status)
                    db.add(pair_status)
                db.commit()
                return {
                    "status": "success",
                    "message": f"Streamer créé et activé pour {pair}.",
                }

        elif status == "deactivate":
            if exists:
                # Mettre à jour le nombre de replicas à 0
                deployment.spec.replicas = 0
                k8s_apps_v1.patch_namespaced_deployment(
                    name=deployment_name, namespace=namespace, body=deployment
                )
                # DB update
                pair_status = db.query(PairStreamerStatus).filter_by(pair=pair).first()
                if pair_status:
                    pair_status.status = status
                    pair_status.updated_at = datetime.datetime.utcnow()
                else:
                    pair_status = PairStreamerStatus(pair=pair, status=status)
                    db.add(pair_status)
                db.commit()
                return {
                    "status": "success",
                    "message": f"Streamer désactivé pour {pair}.",
                }
            else:
                return {
                    "status": "success",
                    "message": f"Aucun déploiement trouvé pour {pair}, aucune action effectuée.",
                }
    finally:
        db.close()


def create_k8s_deployment(pair: str):
    """Créer un déploiement Kubernetes pour un pair-tick-streamer."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"pair-tick-streamer-{pair.lower()}",
            "namespace": "data-ingestion",
            "labels": {
                "app": "pair-tick-streamer",
                "pair": pair.lower(),
            },
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "pair-tick-streamer",
                    "pair": pair.lower(),
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "pair-tick-streamer",
                        "pair": pair.lower(),
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "tick-streamer",
                            "image": "harbor.home.badre2dine.dev/trading_data_ingest/data-ingest-streamer:latest",
                            "imagePullPolicy": "IfNotPresent",
                            "env": [
                                {"name": "PAIR", "value": pair.upper()},
                                {"name": "REDIS_HOST", "value": "redis-master"},
                                {"name": "REDIS_PORT", "value": "6379"},
                            ],
                            "resources": {
                                "requests": {"cpu": "10m", "memory": "50Mi"},
                                "limits": {"cpu": "100m", "memory": "128Mi"},
                            },
                        }
                    ],
                    "imagePullSecrets": [{"name": "harbor-creds"}],
                },
            },
        },
    }


@router.get("/streamer/status")
def list_streamer_status():
    db = SessionLocal()
    try:
        return [
            {"pair": s.pair, "status": s.status, "updated_at": s.updated_at}
            for s in db.query(PairStreamerStatus).all()
        ]
    finally:
        db.close()
