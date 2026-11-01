"""Authentification — comptes **persistés** (table `merchants`).

Interface conservée depuis la phase 3 (les routes et dépendances ne changent
pas) ; seule l'implémentation change : les comptes survivent désormais au
redémarrage du serveur (phase 6).

Deux niveaux, jamais confondus :

1. **Humain** (tableau de bord) : e-mail + mot de passe (**bcrypt**) → jeton
   de session opaque `sess_…` valable 24 h ;
2. **Machine** (serveur du marchand) : clé secrète `3dp_sec_…`, stockée en
   **SHA-256**, affichée une seule fois.

Les sessions restent en mémoire : ce sont des jetons éphémères, comme une
session de navigateur. Les comptes, eux, sont durables.
"""

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.errors import AuthError
from app.models.entities import Merchant, now, to_iso

SESSION_TTL = timedelta(hours=settings.session_ttl_hours)

PUBLIC_KEY_PREFIX = "3dp_pub_"
SECRET_KEY_PREFIX = "3dp_sec_"
SESSION_PREFIX = "sess_"

# Jeton de session -> {"merchant_id": int, "expires_at": datetime}
_sessions: dict[str, dict] = {}


@contextmanager
def _db() -> Iterator[Session]:
    """Session courte gérée par le service (les routes n'ont pas à la fournir)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- Utilitaires --------------------------------------------------------------


def _hash(value: str) -> str:
    """Empreinte SHA-256 (hexdigest) — utilisée pour les clés secrètes."""
    return hashlib.sha256(value.encode()).hexdigest()


def _bcrypt_hash(password: str) -> str:
    """Hache un mot de passe avec bcrypt (bcrypt s'arrête à 72 octets)."""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def _bcrypt_check(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def reset() -> None:
    """Vide sessions **et** base — réservé aux tests."""
    _sessions.clear()
    from app import db as database

    database.reset_db()


def public_payload(merchant: Merchant) -> dict:
    """Champs publics d'un compte (jamais de secret)."""
    return {
        "id": merchant.id,
        "name": merchant.name,
        "email": merchant.email,
        "public_key": merchant.public_key,
        "status": merchant.status,
        "created_at": to_iso(merchant.created_at),
    }


# --- Comptes ------------------------------------------------------------------


def register(name: str, email: str, password: str) -> tuple[dict, str]:
    """Crée un compte marchand et retourne (compte public, clé secrète).

    La clé secrète n'est retournée qu'ici : seule son empreinte SHA-256 est
    conservée, elle est donc irrécupérable ensuite.
    """
    email = email.strip().lower()

    with _db() as db:
        if db.scalar(select(Merchant).where(Merchant.email == email)) is not None:
            raise AuthError(409, "Un compte existe déjà avec cet e-mail.")

        secret_key = SECRET_KEY_PREFIX + secrets.token_urlsafe(32)
        merchant = Merchant(
            name=name.strip(),
            email=email,
            password_hash=_bcrypt_hash(password),
            public_key=PUBLIC_KEY_PREFIX + secrets.token_urlsafe(16),
            secret_key_hash=_hash(secret_key),
            status="active",
            created_at=now(),
        )
        db.add(merchant)
        try:
            db.commit()
        except IntegrityError as exc:  # course entre deux inscriptions
            db.rollback()
            raise AuthError(409, "Un compte existe déjà avec cet e-mail.") from exc

        db.refresh(merchant)
        return public_payload(merchant), secret_key


def login(email: str, password: str) -> tuple[dict, str]:
    """Vérifie les identifiants et ouvre une session.

    Message identique que l'e-mail existe ou non : pas d'énumération de comptes.
    """
    email = email.strip().lower()

    with _db() as db:
        merchant = db.scalar(select(Merchant).where(Merchant.email == email))
        if merchant is None or not _bcrypt_check(password, merchant.password_hash):
            raise AuthError(401, "Identifiants invalides.")
        if merchant.status != "active":
            raise AuthError(403, "Compte suspendu.")
        payload = public_payload(merchant)

    token = SESSION_PREFIX + secrets.token_urlsafe(32)
    _sessions[token] = {
        "merchant_id": payload["id"],
        "expires_at": datetime.now(timezone.utc) + SESSION_TTL,
    }
    return payload, token


# --- Vérifications d'accès ----------------------------------------------------


def authenticate_api_key(token: str) -> dict:
    """Valide une clé secrète `3dp_sec_…` et retourne le compte public."""
    with _db() as db:
        merchant = db.scalar(
            select(Merchant).where(Merchant.secret_key_hash == _hash(token))
        )
        if merchant is None:
            raise AuthError(401, "Clé API invalide.")
        if merchant.status != "active":
            raise AuthError(403, "Compte suspendu.")
        return public_payload(merchant)


def get_session_account(token: str) -> dict:
    """Valide un jeton de session et retourne le compte public."""
    session = _sessions.get(token)
    if session is None or session["expires_at"] <= datetime.now(timezone.utc):
        _sessions.pop(token, None)
        raise AuthError(401, "Session invalide ou expirée.")

    with _db() as db:
        merchant = db.get(Merchant, session["merchant_id"])
        if merchant is None:
            _sessions.pop(token, None)
            raise AuthError(401, "Session invalide ou expirée.")
        return public_payload(merchant)


def logout(token: str) -> None:
    """Révoque une session (silencieux si le jeton est déjà parti)."""
    _sessions.pop(token, None)


def rotate_secret(account: dict) -> str:
    """Génère une nouvelle clé secrète et invalide immédiatement l'ancienne."""
    new_secret = SECRET_KEY_PREFIX + secrets.token_urlsafe(32)
    with _db() as db:
        merchant = db.get(Merchant, account["id"])
        if merchant is None:
            raise AuthError(401, "Clé API invalide.")
        merchant.secret_key_hash = _hash(new_secret)
        db.commit()
    return new_secret
