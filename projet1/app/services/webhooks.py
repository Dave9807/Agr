"""Webhooks signés vers le site marchand (phase 7).

Mécanisme calqué sur les vrais agrégateurs (voir `AUTH_ET_BENCHMARK.md` §6.4) :

- `POST` JSON vers l'URL déclarée par le marchand ;
- payload `{event, reference, status, amount, occurred_at}` ;
- en-tête **`X-3DPay-Signature`** = HMAC-SHA256 du corps (secret partagé) ;
- le marchand doit répondre **2xx**, sinon **retry ×5** journalisé ;
- **protection SSRF** : aucune URL interne/privée n'est acceptée ;
- chaque tentative est conservée dans le journal (`webhook_deliveries`).
"""

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import time
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.errors import WebhookError
from app.models.entities import Merchant, WebhookDelivery, now, to_iso

logger = logging.getLogger("3dpay.webhooks")

#: Statut métier → nom d'événement (vocabulaire `transaction.*`).
EVENT_BY_STATUS: dict[str, str] = {
    "SUCCEEDED": "transaction.succeeded",
    "DECLINED_BY_CUSTOMER": "transaction.declined",
    "REJECTED_BY_OPERATOR": "transaction.failed",
    "FAILED": "transaction.failed",
    "EXPIRED": "transaction.failed",
}

SIGNATURE_HEADER = "X-3DPay-Signature"


# --- Signature ----------------------------------------------------------------


def sign(body: bytes) -> str:
    """Calcule la signature HMAC-SHA256 du corps (format `sha256=<hex>`)."""
    digest = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def verify(body: bytes, signature: str) -> bool:
    """Vérifie une signature reçue (comparaison à temps constant)."""
    return hmac.compare_digest(sign(body), signature)


# --- Protection SSRF ----------------------------------------------------------


def validate_url(url: str) -> str:
    """Refuse un schéma inattendu et, si la protection est active, toute URL
    pointant vers une adresse interne, privée ou locale."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise WebhookError(422, "URL de webhook invalide : http(s) attendu.")

    host = parsed.hostname
    if not host:
        raise WebhookError(422, "URL de webhook invalide : hôte manquant.")

    if not settings.webhook_block_private:
        return url

    if host.lower() in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise WebhookError(422, "URL interne ou locale refusée (protection SSRF).")

    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise WebhookError(422, "Nom d'hôte du webhook introuvable.") from exc

    for raw in addresses:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise WebhookError(422, "URL interne ou privée refusée (protection SSRF).")

    return url


# --- Livraison ----------------------------------------------------------------


def _http_post(url: str, body: bytes, headers: dict) -> tuple[int | None, str]:
    """Transport HTTP réel. Remplaçable dans les tests (monkeypatch)."""
    try:
        with httpx.Client(timeout=settings.webhook_timeout_seconds) as client:
            response = client.post(url, content=body, headers=headers)
            return response.status_code, response.text[:500]
    except Exception as exc:  # réseau, DNS, timeout…
        return None, f"{type(exc).__name__}: {exc}"


def build_payload(transaction: dict, event: str) -> bytes:
    """Corps JSON du webhook (vocabulaire stable, montant inclus)."""
    payload = {
        "event": event,
        "reference": transaction["reference"],
        "status": transaction["status"],
        "amount": transaction["amount"],
        "occurred_at": to_iso(now()),
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()


def notify_transaction(transaction: dict, event: str) -> WebhookDelivery | None:
    """Prépare, envoie et journalise le webhook d'une transaction.

    Retourne `None` si le marchand n'a pas configuré d'URL. Lève `WebhookError`
    si l'URL est refusée (protection SSRF) — l'appelant décide quoi en faire.
    """
    session = SessionLocal()
    try:
        merchant = session.get(Merchant, transaction["merchant_id"])
        if merchant is None or not merchant.webhook_url:
            logger.info(
                "transaction %s : aucun webhook configuré",
                transaction["reference"],
            )
            return None

        validate_url(merchant.webhook_url)

        body = build_payload(transaction, event)
        signature = sign(body)
        delivery = WebhookDelivery(
            merchant_id=merchant.id,
            reference=transaction["reference"],
            event=event,
            url=merchant.webhook_url,
            payload=body.decode(),
            signature=signature,
            attempts=0,
            state="pending",
        )
        session.add(delivery)
        session.commit()
        session.refresh(delivery)
    finally:
        session.close()

    return deliver(delivery.id, body, signature)


def deliver(delivery_id: int, body: bytes, signature: str) -> WebhookDelivery:
    """Envoie le webhook avec retry : succès dès un 2xx, sinon ×5 puis abandon."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "3DPay-Webhooks/1.0 (SIMULATION)",
        SIGNATURE_HEADER: signature,
    }
    max_attempts = max(1, settings.webhook_max_attempts)

    session = SessionLocal()
    try:
        delivery = session.get(WebhookDelivery, delivery_id)
        if delivery is None:  # pragma: no cover - cas impossible en pratique
            raise WebhookError(404, "Livraison de webhook introuvable.")

        for attempt in range(1, max_attempts + 1):
            status_code, response_text = _http_post(delivery.url, body, headers)
            delivery.attempts = attempt
            delivery.status_code = status_code
            delivery.response_body = response_text
            delivery.updated_at = now()

            if status_code is not None and 200 <= status_code < 300:
                delivery.state = "delivered"
                logger.info(
                    "webhook %s → %s : 2xx (tentative %s)",
                    delivery.event,
                    delivery.url,
                    attempt,
                )
                break

            logger.warning(
                "webhook %s → %s : échec tentative %s/%s (statut=%s)",
                delivery.event,
                delivery.url,
                attempt,
                max_attempts,
                status_code,
            )
            if attempt < max_attempts and settings.webhook_retry_delay_seconds > 0:
                time.sleep(settings.webhook_retry_delay_seconds)
        else:
            delivery.state = "failed"
            logger.error(
                "webhook %s → %s : abandon après %s tentatives",
                delivery.event,
                delivery.url,
                max_attempts,
            )

        session.commit()
        session.refresh(delivery)
        return delivery
    finally:
        session.close()


def journal_for_merchant(merchant_id: int) -> list[WebhookDelivery]:
    """Journal des webhooks d'un compte, du plus récent au plus ancien."""
    session = SessionLocal()
    try:
        return list(
            session.scalars(
                select(WebhookDelivery)
                .where(WebhookDelivery.merchant_id == merchant_id)
                .order_by(WebhookDelivery.id.desc())
            )
        )
    finally:
        session.close()
