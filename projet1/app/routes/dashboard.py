"""Tableau de bord (session) : transactions, webhooks, clés, réglages.

Isolation stricte : chaque requête est filtrée par `merchant_id`. Un compte
ne voit **jamais** les transactions, webhooks ou clés d'un autre.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_session
from app.models.entities import Merchant, to_iso
from app.models.schemas import (
    DashboardSettingsIn,
    DashboardSettingsOut,
    PaymentOut,
    PublicKeyOut,
    SecretKeyOut,
    WebhookDeliveryOut,
)
from app.services import auth, payments, webhooks

router = APIRouter(prefix="/api/v1/dashboard", tags=["Tableau de bord"])

_KEY_NOTICE = (
    "La clé secrète n'est affichée qu'une seule fois : conservez-la "
    "immédiatement, le tableau de bord ne pourra plus la retrouver."
)


def _settings_out(merchant: Merchant) -> DashboardSettingsOut:
    return DashboardSettingsOut(
        name=merchant.name,
        email=merchant.email,
        public_key=merchant.public_key,
        webhook_url=merchant.webhook_url,
        status=merchant.status,
    )


@router.get(
    "/transactions",
    response_model=list[PaymentOut],
    summary="Mes transactions",
    description="Transactions du compte connecté, de la plus récente à la plus ancienne.",
)
def my_transactions(account: dict = Depends(require_session)):
    return [
        PaymentOut(**payments.to_public(transaction))
        for transaction in payments.list_for_merchant(account)
    ]


@router.get(
    "/transactions/{reference}",
    response_model=PaymentOut,
    summary="Détail d'une de mes transactions",
    description="Une référence d'un autre compte renvoie `404`.",
)
def my_transaction(reference: str, account: dict = Depends(require_session)):
    transaction = payments.get_for_merchant(account, reference)
    return PaymentOut(**payments.to_public(transaction))


@router.get(
    "/webhooks",
    response_model=list[WebhookDeliveryOut],
    summary="Journal des webhooks",
    description="Tentatives d'envoi (URL, statut HTTP, nombre d'essais, réponse).",
)
def webhook_journal(account: dict = Depends(require_session)):
    return [
        WebhookDeliveryOut(
            id=delivery.id,
            reference=delivery.reference,
            event=delivery.event,
            url=delivery.url,
            state=delivery.state,
            attempts=delivery.attempts,
            status_code=delivery.status_code,
            response_body=delivery.response_body,
            created_at=to_iso(delivery.created_at),
        )
        for delivery in webhooks.journal_for_merchant(account["id"])
    ]


@router.get(
    "/settings",
    response_model=DashboardSettingsOut,
    summary="Mes réglages",
)
def get_settings(
    account: dict = Depends(require_session),
    db: Session = Depends(get_db),
) -> DashboardSettingsOut:
    merchant = db.get(Merchant, account["id"])
    return _settings_out(merchant)


@router.patch(
    "/settings",
    response_model=DashboardSettingsOut,
    summary="Modifier l'URL de webhook",
    description="L'URL est contrôlée : une adresse interne/privée est refusée (`422`).",
)
def update_settings(
    payload: DashboardSettingsIn,
    account: dict = Depends(require_session),
    db: Session = Depends(get_db),
) -> DashboardSettingsOut:
    merchant = db.get(Merchant, account["id"])
    if payload.webhook_url is None or not payload.webhook_url.strip():
        merchant.webhook_url = None
    else:
        merchant.webhook_url = webhooks.validate_url(payload.webhook_url.strip())

    db.commit()
    db.refresh(merchant)
    return _settings_out(merchant)


@router.get(
    "/keys",
    response_model=PublicKeyOut,
    summary="Mes clés",
    description="La clé publique est affichable ; la clé secrète ne l'est jamais.",
)
def show_keys(account: dict = Depends(require_session)) -> PublicKeyOut:
    return PublicKeyOut(
        public_key=account["public_key"],
        notice="La clé secrète n'est jamais réaffichable : régénérez-la si besoin.",
    )


@router.post(
    "/keys/rotate",
    response_model=SecretKeyOut,
    summary="Régénérer la clé secrète depuis le tableau de bord",
    description="L'ancienne clé est immédiatement révoquée.",
)
def rotate_from_dashboard(account: dict = Depends(require_session)) -> SecretKeyOut:
    return SecretKeyOut(secret_key=auth.rotate_secret(account), notice=_KEY_NOTICE)
