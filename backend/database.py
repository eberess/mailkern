import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Configuration de la base de données à partir des variables d'environnement
POSTGRES_USER = os.getenv("POSTGRES_USER", "mailkern")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mailkern")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mailkern")

# Construction de l'URL de connexion
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Création du moteur SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Désactive le pooling pour éviter les problèmes de connexion
    echo=False  # À mettre à True pour déboguer les requêtes SQL
)

# Création de la factory de sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base déclarative pour les modèles
Base = declarative_base()


def get_db():
    """
    Générateur pour obtenir une session de base de données.
    À utiliser comme dépendance FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Crée toutes les tables définies dans les modèles.
    À appeler au démarrage de l'application.
    """
    Base.metadata.create_all(bind=engine)
