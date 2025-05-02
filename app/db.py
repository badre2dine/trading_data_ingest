import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env s'il existe
load_dotenv()

# Utiliser la variable d'environnement DATABASE_URL ou utiliser SQLite par défaut
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./task_logs.db")

# Configurer les options de connexion en fonction du type de base de données
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
