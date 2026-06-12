from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


# Putanja do SQLite baze
DB_PATH = Path(__file__).resolve().parent / "data" / "dashboard.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"


# Konektovanje na SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class za modele
Base = declarative_base()
