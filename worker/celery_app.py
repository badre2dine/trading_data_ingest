import os
from celery import Celery
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Utiliser la variable d'environnement ou la valeur par défaut
broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")

celery_app = Celery(
    "worker",
    broker=broker_url,
)
