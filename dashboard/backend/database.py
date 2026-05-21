from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


# Putanja do SQLite baze
DATABASE_URL = "sqlite:///./data/dashboard.db"


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