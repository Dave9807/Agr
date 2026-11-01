"""Idempotence des créations de paiement (`Idempotency-Key`).

Règle : la clé est **scopée par marchand** — deux marchands peuvent
réutiliser la même valeur sans conflit. Une requête rejouée avec la même
clé et le même corps renvoie la transaction d'origine (aucune duplication) ;
avec un corps différent, elle est rejetée en **409**.
"""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import IdempotencyError
from app.models.entities import IdempotencyRecord


def fingerprint(payload) -> str:
    """Empreinte stable du corps de la requête (détecte un rejeu divergent).

    Accepte un modèle Pydantic ou un simple dictionnaire.
    """
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")
    else:
        data = dict(payload)

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def find(db: Session, merchant_id: int, key: str, request_hash: str) -> str | None:
    """Retourne la référence déjà associée à la clé, ou `None` si inconnue."""
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.merchant_id == merchant_id,
            IdempotencyRecord.key == key,
        )
    )
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise IdempotencyError(
            409,
            "Clé d'idempotence déjà utilisée avec une requête différente.",
        )
    return record.transaction_reference


def remember(
    db: Session,
    merchant_id: int,
    key: str,
    request_hash: str,
    reference: str,
) -> IdempotencyRecord:
    """Mémorise la clé et la transaction qu'elle a produite."""
    record = IdempotencyRecord(
        merchant_id=merchant_id,
        key=key,
        request_hash=request_hash,
        transaction_reference=reference,
    )
    db.add(record)
    return record
