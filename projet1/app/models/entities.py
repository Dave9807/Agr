"""Tables SQLAlchemy — la persistance du projet (phase 6).

Quatre tables :

- `merchants`           : comptes des développeurs/marchands (libre-service) ;
- `transactions`       : une demande de paiement et son statut courant ;
- `webhook_deliveries` : journal des notifications envoyées (phase 7) ;
- `idempotency_records`: prévention des doubles traitements.

Les dates sont stockées en UTC **naïf** (sans fuseau) : format portable entre
SQLite (dev) et PostgreSQL (prod). La sérialisation API réinjecte `+00:00`.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now() -> datetime:
    """Horodatage UTC sans fuseau (compatible SQLite et PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_iso(value: datetime | None) -> str:
    """Sérialise une date au format utilisé par l'API (`…+00:00`)."""
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


class Merchant(Base):
    """Compte marchand : propriétaire des clés, transactions et webhooks."""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    public_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    secret_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Transaction(Base):
    """Une demande de paiement simulée et son statut métier."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    merchant_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    operator: Mapped[str] = mapped_column(String(20))
    test_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)
    reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    message: Mapped[str] = mapped_column(String(255), default="")
    # Empreinte SHA-256 du jeton de décision du client (jamais le jeton en clair).
    decision_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class WebhookDelivery(Base):
    """Journal des tentatives d'envoi de webhook vers le marchand."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    reference: Mapped[str] = mapped_column(String(40), index=True)
    event: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(String(500))
    payload: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(String(80))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class IdempotencyRecord(Base):
    """Clé d'idempotence **scopée par marchand** (`merchant_id` + `key`)."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("merchant_id", "key", name="uq_idempotency_merchant_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    transaction_reference: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
