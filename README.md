# Trading Data Ingest

Un système distribué pour la collecte, le stockage et l'analyse de données historiques de trading de cryptomonnaies.

## Description du projet

Ce projet fournit une architecture complète pour télécharger et stocker des données historiques de trading (OHLCV) depuis différentes sources comme KuCoin et Binance. Les données sont stockées dans un format Parquet efficace et compressé, organisées par paire de trading, intervalle et période.

L'application se compose de deux services principaux:
- **API FastAPI**: Fournit des endpoints pour déclencher les tâches de téléchargement et consulter leur statut
- **Worker Celery**: Exécute les tâches de téléchargement en arrière-plan, permettant un traitement asynchrone et distribué

## Fonctionnalités principales

- Téléchargement de données historiques OHLCV depuis plusieurs exchanges
- Stockage efficace des données au format Parquet avec compression zstd
- Architecture distribuée avec API REST et workers asynchrones
- Suivi des tâches et logging des opérations dans une base de données PostgreSQL
- Déploiement facile via Docker et Kubernetes

## Structure du projet

```
├── api/                      # Service API REST FastAPI
│   ├── dockerfile            # Dockerfile pour le service API
│   ├── main.py               # Point d'entrée principal FastAPI
│   └── routes.py             # Définition des routes de l'API
│
├── app/                      # Logique principale de l'application
│   ├── db.py                 # Configuration de la base de données
│   ├── downloader.py         # Module de téléchargement des données
│   ├── models.py             # Modèles SQLAlchemy
│   └── tasks_loger.py        # Utilitaire de journalisation des tâches
│
├── data/                     # Répertoire de données (organisé par paire/intervalle/période)
│   ├── BTC-USDC/             # Format KuCoin
│   │   └── 1m/               # Intervalle 1 minute
│   │       └── YYYY-MM.parquet  # Fichiers organisés par année-mois
│   └── BTCUSDT/              # Format Binance
│       └── 1m/
│           └── YYYY-MM.parquet
│
├── k8s/                      # Configuration Kubernetes
│   ├── api-deployment.yaml   # Déploiement du service API
│   ├── api-ingress.yaml      # Ingress pour l'API
│   ├── celery-worker-deployment.yaml  # Déploiement des workers Celery
│   ├── namespace.yaml        # Namespace Kubernetes
│   ├── parquet-hostpath-pv-pvc.yaml  # Stockage persistant pour les données
│   ├── rabbitmq-ingress.yaml # Ingress pour RabbitMQ
│   └── ScaledObject.yaml     # Configuration de l'auto-scaling
│
├── worker/                   # Service worker Celery
│   ├── celery_app.py         # Configuration de l'application Celery
│   ├── dockerfile            # Dockerfile pour les workers
│   └── tasks.py              # Définition des tâches Celery
│
├── .env                      # Variables d'environnement (non versionné)
├── .github/workflows/docker-build.yml  # CI/CD pour la construction d'images Docker
├── migrate.py                # Script d'initialisation de la base de données
├── requirements.txt          # Dépendances Python
├── run.py                    # Point d'entrée principal pour l'application
└── t.py                      # Script de test
```

## Installation et configuration

### Prérequis
- Python 3.11+
- PostgreSQL
- RabbitMQ (pour Celery)

### Configuration de l'environnement

1. Cloner le dépôt:
```bash
git clone https://github.com/votre-user/trading_data_ingest.git
cd trading_data_ingest
```

2. Créer un environnement virtuel:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

3. Installer les dépendances:
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement:
Créez un fichier `.env` à la racine du projet avec le contenu suivant:
```
DATABASE_URL=postgresql://username:password@localhost:5432/trading_data
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```

5. Initialiser la base de données:
```bash
python migrate.py
```

### Démarrage des services

1. Démarrer l'API:
```bash
python -m uvicorn run:app --host 0.0.0.0 --port 8000
```

2. Démarrer le worker Celery:
```bash
celery -A worker.tasks worker --concurrency=5 --loglevel=info
```

## Utilisation de l'API

### Télécharger des données historiques

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "start": "01-22", "end": "12-22", "interval": "1m"}'
```

### Vérifier l'état d'une tâche

```bash
curl http://localhost:8000/status/{task_id}
```

### Consulter les logs des tâches

```bash
curl http://localhost:8000/logs
```

## Déploiement avec Docker

1. Construire les images Docker:
```bash
docker build -t trading-data-api:latest -f api/dockerfile .
docker build -t trading-data-worker:latest -f worker/dockerfile .
```

2. Déployer avec Docker Compose ou Kubernetes (voir les fichiers de configuration dans le dossier k8s/).

## License

MIT