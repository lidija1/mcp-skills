from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


# Putanja do SQLite baze
DB_PATH = Path(__file__).resolve().parent / "data" / "dashboard.db"
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except Exception:
    pass
DATABASE_URL = os.environ.get("DASHBOARD_DATABASE_URL") or os.environ.get("DATABASE_URL") or f"sqlite:///{DB_PATH.as_posix()}"
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}


# Konektovanje na aktivnu bazu
engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
)


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class za modele
Base = declarative_base()
