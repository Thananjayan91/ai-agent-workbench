from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)
    _connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from backend import models  # noqa: F401  (ensure models are registered before create_all)

    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
