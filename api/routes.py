import datetime
from celery.result import AsyncResult
from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app.db import SessionLocal
from app.models import TaskLog
from worker.tasks import download_month


router = APIRouter()


class BatchRequest(BaseModel):
    symbol: str
    start: str
    end: str
    interval: str = "1m"

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
        task = download_month.delay(req.symbol, current.year, current.month)
        tasks.append({"year": current.year, "month": current.month, "task_id": task.id})
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)

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
