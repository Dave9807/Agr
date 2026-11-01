"""Connexion à la base de données (SQLAlchemy 2.x).

DEV / tests : SQLite (fichier local ou base en mémoire).
PROD        : PostgreSQL — il suffit de changer `DATABASE_URL`.

Le moteur est créé une seule fois au chargement du module.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    """Classe de base de toutes les tables."""


def _build_engine(url: str):
    options: dict = {}
    if url.startswith("sqlite"):
        # SQLite + FastAPI/TestClient : plusieurs threads partagent la connexion.
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            # Une base en mémoire doit être partagée entre toutes les sessions.
            options["poolclass"] = StaticPool
    return create_engine(url, **options)


engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : ouvre une session et la referme systématiquement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée les tables manquantes (idempotent)."""
    from app.models import entities  # noqa: F401  (enregistre les tables)

    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Détruit puis recrée le schéma — **réservé aux tests**."""
    from app.models import entities  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
