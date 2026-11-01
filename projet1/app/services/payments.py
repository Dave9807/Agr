"""Service des transactions — **persisté en base** (phase 6).

Le contrat public de la phase 4/5 est conservé à l'identique (`create`,
`get_for_merchant`, `decide`, `apply_transition`, `PaymentError`, `reset`) :
les routes, les tests et la machine à statuts n'ont pas changé. Seul le
stockage change : un dictionnaire vivant (identité stable, pratique pour les
tests) **adossé à SQLAlchemy** qui reste la source de vérité.

Règles appliquées ici :

- une transaction appartient à **un** compte marchand (`merchant_id`) : une
  référence créée par un autre compte est traitée comme inexistante (`404`) ;
- le **client payeur n'a aucun compte** 3DPAY : sa décision est authentifiée
  par un `decision_token` à usage unique, remis à la création et stocké haché
  (SHA-256) ;
- refus client (`DECLINED_BY_CUSTOMER`) et rejet opérateur
  (`REJECTED_BY_OPERATOR`) restent deux statuts distincts ;
- toute transition passe par la machine à statuts (`app/models/statuses.py`) ;
- les webhooks (phase 7) sont déclenchés sur les statuts terminaux ;
- l'expiration (`EXPIRED`) est paresseuse : à la lecture d'une transaction
  dont le délai (`TRANSACTION_TTL_MINUTES`) est dépassé.
"""

import hashlib
import logging
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.errors import AppError
from app.models import statuses
from app.models.entities import Transaction, now, to_iso
from app.operators import get_operator
from app.operators.base import (
    DECLINED,
    FAILED,
    INSUFFICIENT_FUNDS,
    INVALID_TEST_NUMBER,
    PENDING,
    SUCCESS,
)
from app.services import idempotency, webhooks

logger = logging.getLogger("3dpay.payments")

REFERENCE_PREFIX = "3dp_tx_"
DECISION_TOKEN_PREFIX = "3dp_dec_"

CONFIRM = "CONFIRM"
DECLINE = "DECLINE"
DECISIONS = (CONFIRM, DECLINE)

# Traduction « vocabulaire opérateur » → « statut métier de l'agrégateur ».
# Un statut d'attente (`PROCESSING`) n'est jamais traduit en succès.
_STATUS_BY_OUTCOME: dict[str, tuple[str, str | None]] = {
    SUCCESS: (statuses.SUCCEEDED, None),
    DECLINED: (statuses.REJECTED_BY_OPERATOR, "OPERATOR_DECLINED"),
    INSUFFICIENT_FUNDS: (statuses.REJECTED_BY_OPERATOR, "INSUFFICIENT_FUNDS"),
    INVALID_TEST_NUMBER: (statuses.REJECTED_BY_OPERATOR, "INVALID_TEST_NUMBER"),
    PENDING: (statuses.PROCESSING, None),
    FAILED: (statuses.FAILED, "OPERATOR_ERROR"),
}

#: Alias public (documentation, page des numéros de test).
STATUS_BY_OUTCOME = _STATUS_BY_OUTCOME


class PaymentError(AppError):
    """Erreur métier d'un paiement, portant son propre code HTTP."""


# --- Cache d'objets vivants ---------------------------------------------------
#
# Les tests et la machine à statuts manipulent la transaction comme un dict
# (identité stable). Ce cache garantit que `create`, `decide` et
# `apply_transition` travaillent sur le MÊME objet ; la base reste la source
# de vérité (rechargement à froid, après redémarrage).

_transactions: dict[str, dict] = {}


@contextmanager
def _db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def reset() -> None:
    """Vide le cache **et** la base — réservé aux tests."""
    _transactions.clear()
    from app import db as database

    database.reset_db()


# --- Opérations ---------------------------------------------------------------


def create(
    *,
    account: dict,
    amount: int,
    currency: str,
    operator: str,
    merchant_reference: str | None,
    test_number: str,
    idempotency_key: str | None = None,
) -> tuple[dict, str]:
    """Crée une transaction au statut `CREATED`.

    Retourne `(transaction, decision_token)`. Le jeton en clair n'est
    retourné qu'ici : seul son SHA-256 est conservé.

    Avec une `Idempotency-Key` déjà vue (même corps), la transaction
    d'origine est renvoyée — jamais dupliquée — avec un nouveau jeton de
    décision valide (l'ancien est invalidé).
    """
    request_hash = idempotency.fingerprint(
        {
            "amount": amount,
            "currency": currency,
            "operator": operator,
            "merchant_reference": merchant_reference,
            "test_number": test_number,
        }
    )

    if idempotency_key:
        with _db() as db:
            reference = idempotency.find(
                db, account["id"], idempotency_key, request_hash
            )
        if reference is not None:
            transaction = _load(reference)
            if transaction is not None:
                logger.info("idempotence : clé %s rejouée → %s", idempotency_key, reference)
                return transaction, _renew_decision_token(transaction)

    timestamp = now()
    decision_token = DECISION_TOKEN_PREFIX + secrets.token_urlsafe(24)
    transaction = {
        "merchant_id": account["id"],
        "reference": _new_reference(),
        "amount": amount,
        "currency": currency,
        "merchant_reference": merchant_reference,
        "operator": operator,
        "test_number": test_number,
        "status": statuses.CREATED,
        "reason": None,
        "message": (
            "Transaction créée : en attente de la décision du client "
            "(confirmation ou refus)."
        ),
        "decision_token_hash": _hash(decision_token),
        "created_at": to_iso(timestamp),
        "updated_at": to_iso(timestamp),
    }

    with _db() as db:
        row = Transaction(
            reference=transaction["reference"],
            merchant_id=account["id"],
            amount=amount,
            currency=currency,
            merchant_reference=merchant_reference,
            operator=operator,
            test_number=test_number,
            status=statuses.CREATED,
            reason=None,
            message=transaction["message"],
            decision_token_hash=transaction["decision_token_hash"],
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(row)
        if idempotency_key:
            idempotency.remember(
                db, account["id"], idempotency_key, request_hash, row.reference
            )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if idempotency_key:
                existing = idempotency.find(
                    db, account["id"], idempotency_key, request_hash
                )
                if existing is not None:
                    loaded = _load(existing)
                    if loaded is not None:
                        return loaded, _renew_decision_token(loaded)
            raise PaymentError(
                409, "Conflit lors de la création : réessayez la requête."
            ) from exc
        db.refresh(row)
        transaction["id"] = row.id

    _transactions[transaction["reference"]] = transaction
    logger.info(
        "transaction %s créée (marchand %s, %s %s, opérateur %s)",
        transaction["reference"],
        account["id"],
        amount,
        currency,
        operator,
    )
    return transaction, decision_token


def get_for_merchant(account: dict, reference: str) -> dict:
    """Transaction du compte `account`, sinon `404` (y compris si elle est à un autre)."""
    transaction = _load(reference)
    if transaction is None or transaction["merchant_id"] != account["id"]:
        raise PaymentError(404, "Transaction introuvable.")
    _expire_if_needed(transaction)
    return transaction


def list_for_merchant(account: dict) -> list[dict]:
    """Toutes les transactions du compte, de la plus récente à la plus ancienne."""
    with _db() as db:
        rows = db.scalars(
            select(Transaction)
            .where(Transaction.merchant_id == account["id"])
            .order_by(Transaction.id.desc())
        ).all()
    transactions = [_row_to_dict(row) for row in rows]
    for transaction in transactions:
        _transactions.setdefault(transaction["reference"], transaction)
        _expire_if_needed(_transactions[transaction["reference"]])
    return transactions


def decide(
    reference: str,
    decision_token: str,
    decision: str,
    forced_outcome: str | None = None,
) -> dict:
    """Enregistre la décision du client et, si elle est positive, interroge l'opérateur.

    - référence inconnue                  -> `404`
    - transaction déjà traitée            -> `409`
    - jeton invalide, déjà utilisé ou
      lié à une autre transaction         -> `401`
    - refus du client                     -> `DECLINED_BY_CUSTOMER`, sans opérateur
    - confirmation                        -> résultat de l'opérateur simulé
    """
    if decision not in DECISIONS:
        raise ValueError(f"Décision inconnue : {decision!r}.")

    transaction = _load(reference)
    if transaction is None:
        raise PaymentError(404, "Transaction introuvable.")

    _expire_if_needed(transaction)

    if transaction["status"] not in statuses.ACTIONABLE_STATUSES:
        raise PaymentError(
            409,
            f"Transaction déjà traitée (statut {transaction['status']}).",
        )

    if transaction.get("decision_token_hash") != _hash(decision_token):
        raise PaymentError(401, "Jeton de décision invalide ou déjà utilisé.")

    # Jeton à usage unique : consommé avant d'appeler l'opérateur.
    transaction["decision_token_hash"] = None
    _save(transaction)

    if decision == DECLINE:
        apply_transition(
            transaction,
            statuses.DECLINED_BY_CUSTOMER,
            "CUSTOMER_DECLINED",
            "Paiement refusé par le client : aucun appel à l'opérateur n'a été effectué.",
        )
        _notify(transaction)
        return transaction

    result = get_operator(transaction["operator"]).process(
        transaction["test_number"], forced_outcome
    )
    status, reason = _STATUS_BY_OUTCOME[result.outcome]
    apply_transition(transaction, status, reason, result.message)
    _notify(transaction)
    return transaction


def apply_transition(
    transaction: dict, status: str, reason: str | None, message: str
) -> None:
    """Applique une transition de statut en la faisant valider par la machine.

    Toute transition absente de `statuses.ALLOWED_TRANSITIONS` est rejetée ici
    (`409`) : c'est le point de contrôle unique, quel que soit le chemin qui
    produit le nouveau statut.
    """
    current = transaction["status"]
    if not statuses.can_transition(current, status):
        raise PaymentError(
            409,
            f"Transition interdite : {current} -> {status}.",
        )

    transaction["status"] = status
    transaction["reason"] = reason
    transaction["message"] = message
    transaction["updated_at"] = to_iso(now())
    _save(transaction)
    logger.info(
        "transaction %s : %s → %s%s",
        transaction["reference"],
        current,
        status,
        f" ({reason})" if reason else "",
    )


# --- Persistance --------------------------------------------------------------


def _new_reference() -> str:
    """Référence stable et unique, lisible dans une URL."""
    return REFERENCE_PREFIX + secrets.token_hex(8)


def _hash(value: str) -> str:
    """Empreinte SHA-256 d'une chaîne (hexdigest)."""
    return hashlib.sha256(value.encode()).hexdigest()


def _row_to_dict(row: Transaction) -> dict:
    """Représentation interne (dict) d'une ligne de la base."""
    return {
        "id": row.id,
        "merchant_id": row.merchant_id,
        "reference": row.reference,
        "amount": row.amount,
        "currency": row.currency,
        "merchant_reference": row.merchant_reference,
        "operator": row.operator,
        "test_number": row.test_number,
        "status": row.status,
        "reason": row.reason,
        "message": row.message,
        "decision_token_hash": row.decision_token_hash,
        "created_at": to_iso(row.created_at),
        "updated_at": to_iso(row.updated_at),
    }


def _load(reference: str) -> dict | None:
    """Charge une transaction (cache d'abord, puis base)."""
    if reference in _transactions:
        return _transactions[reference]

    with _db() as db:
        row = db.scalar(select(Transaction).where(Transaction.reference == reference))
        if row is None:
            return None
        transaction = _row_to_dict(row)

    _transactions[reference] = transaction
    return transaction


def _save(transaction: dict) -> None:
    """Écrit l'état courant du dict dans la base (insert ou update)."""
    created = datetime.fromisoformat(transaction["created_at"]).replace(tzinfo=None)
    updated = datetime.fromisoformat(transaction["updated_at"]).replace(tzinfo=None)

    with _db() as db:
        row = db.scalar(
            select(Transaction).where(
                Transaction.reference == transaction["reference"]
            )
        )
        if row is None:
            row = Transaction(
                reference=transaction["reference"],
                merchant_id=transaction["merchant_id"],
                amount=transaction["amount"],
                currency=transaction["currency"],
                merchant_reference=transaction["merchant_reference"],
                operator=transaction["operator"],
                test_number=transaction["test_number"],
                status=transaction["status"],
                reason=transaction["reason"],
                message=transaction["message"],
                decision_token_hash=transaction.get("decision_token_hash"),
                created_at=created,
                updated_at=updated,
            )
            db.add(row)
        else:
            row.status = transaction["status"]
            row.reason = transaction["reason"]
            row.message = transaction["message"]
            row.decision_token_hash = transaction.get("decision_token_hash")
            row.updated_at = updated
        db.commit()
        db.refresh(row)
        transaction["id"] = row.id


def _renew_decision_token(transaction: dict) -> str:
    """Émet un nouveau jeton de décision (rejeu idempotent) et invalide l'ancien."""
    token = DECISION_TOKEN_PREFIX + secrets.token_urlsafe(24)
    transaction["decision_token_hash"] = _hash(token)
    _save(transaction)
    return token


# --- Expiration ---------------------------------------------------------------


def _expire_if_needed(transaction: dict) -> bool:
    """Expire une transaction restée en attente au-delà du délai configuré."""
    if transaction["status"] not in statuses.ACTIONABLE_STATUSES:
        return False

    created = datetime.fromisoformat(transaction["created_at"])
    created = created.replace(tzinfo=None) if created.tzinfo else created
    deadline = created + timedelta(minutes=max(1, settings.transaction_ttl_minutes))
    if now() <= deadline:
        return False

    try:
        apply_transition(
            transaction,
            statuses.EXPIRED,
            "TRANSACTION_EXPIRED",
            "Délai de paiement dépassé : la demande a expiré.",
        )
    except PaymentError:
        return False
    _notify(transaction)
    return True


# --- Webhooks (phase 7) -------------------------------------------------------


def _notify(transaction: dict) -> None:
    """Envoie le webhook d'un statut terminal — ne casse jamais la réponse API."""
    event = webhooks.EVENT_BY_STATUS.get(transaction["status"])
    if event is None:
        return
    try:
        webhooks.notify_transaction(transaction, event)
    except Exception as exc:  # le webhook ne doit jamais faire échouer un paiement
        logger.error(
            "transaction %s : échec de l'envoi du webhook (%s)",
            transaction["reference"],
            exc,
        )


# --- Sérialisation ------------------------------------------------------------


def to_public(transaction: dict) -> dict:
    """Vue publique d'une transaction (jamais `merchant_id` ni de secret)."""
    return {
        "reference": transaction["reference"],
        "status": transaction["status"],
        "is_final": statuses.is_final(transaction["status"]),
        "reason": transaction["reason"],
        "message": transaction["message"],
        "amount": transaction["amount"],
        "currency": transaction["currency"],
        "operator": transaction["operator"],
        "merchant_reference": transaction["merchant_reference"],
        "test_number": transaction["test_number"],
        "created_at": transaction["created_at"],
        "updated_at": transaction["updated_at"],
        "mode": "SIMULATION",
    }
