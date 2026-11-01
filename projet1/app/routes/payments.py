"""Routes du cycle de vie d'un paiement simulé.

    POST /api/v1/payments                     clé secrète 3dp_sec_…  -> 201
    GET  /api/v1/payments/{reference}         clé secrète 3dp_sec_…  -> 200 | 404
    POST /api/v1/payments/{reference}/decision  jeton de décision     -> 200 | 401 | 404 | 409

La route de décision n'exige **pas** de clé marchand : le client payeur n'a
aucun compte 3DPAY et n'appelle jamais l'API avec une clé. Sa preuve est le
`decision_token` remis à la création, à usage unique.

Le code HTTP décrit la requête ; le statut métier décrit le paiement. Un
`201 Created` peut donc contenir `"status": "CREATED"`, et un `200 OK`
peut contenir `"status": "PROCESSING"` (résultat non définitif).
"""

from fastapi import APIRouter, Depends, Header, status

from app.config import settings
from app.deps import require_api_key
from app.models import statuses
from app.models.schemas import (
    DecisionIn,
    PaymentCreatedOut,
    PaymentIn,
    PaymentOut,
)
from app.services import payments
from app.services.ratelimit import limiter

router = APIRouter(prefix="/api/v1", tags=["Paiements"])

# Limitation du débit sur les routes de paiement (phase 6).
_payment_limit = Depends(limiter("payments", settings.rate_limit_payments_per_minute))

_DECISION_NOTICE = (
    "Jeton de décision du client, affiché une seule fois. "
    "Placez-le dans le lien de votre widget : il autorise une seule décision."
)

_PUBLIC_FIELDS = (
    "reference",
    "status",
    "reason",
    "message",
    "amount",
    "currency",
    "operator",
    "merchant_reference",
    "test_number",
    "created_at",
    "updated_at",
)


def _as_out(transaction: dict) -> PaymentOut:
    """Vue publique d'une transaction (jamais `merchant_id` ni de secret)."""
    return PaymentOut(
        **{field: transaction[field] for field in _PUBLIC_FIELDS},
        is_final=statuses.is_final(transaction["status"]),
    )


@router.post(
    "/payments",
    response_model=PaymentCreatedOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_payment_limit],
    summary="Créer un paiement simulé",
    description=(
        "Crée une transaction au statut `CREATED` et renvoie sa référence. "
        "Le `decision_token` sert au client payeur pour confirmer ou refuser. "
        "Un `201` ne signifie pas que le paiement est réussi. "
        "En-tête optionnel `Idempotency-Key` pour éviter les doublons."
    ),
)
def create_payment(
    payload: PaymentIn,
    account: dict = Depends(require_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PaymentCreatedOut:
    transaction, decision_token = payments.create(
        account=account,
        amount=payload.amount,
        currency=payload.currency,
        operator=payload.operator,
        merchant_reference=payload.merchant_reference,
        test_number=payload.test_number,
        idempotency_key=idempotency_key,
    )
    return PaymentCreatedOut(
        **_as_out(transaction).model_dump(),
        decision_token=decision_token,
        notice=_DECISION_NOTICE,
    )


@router.get(
    "/payments/{reference}",
    response_model=PaymentOut,
    dependencies=[_payment_limit],
    summary="Consulter un paiement",
    description=(
        "Retourne le statut courant de la transaction. "
        "Une référence inconnue — ou appartenant à un autre compte — renvoie `404`."
    ),
)
def get_payment(
    reference: str,
    account: dict = Depends(require_api_key),
) -> PaymentOut:
    return _as_out(payments.get_for_merchant(account, reference))


@router.post(
    "/payments/{reference}/decision",
    response_model=PaymentOut,
    dependencies=[_payment_limit],
    summary="Décision du client payeur",
    description=(
        "Le client confirme (`CONFIRM`) ou refuse (`DECLINE`) depuis le widget. "
        "Une confirmation interroge l'opérateur simulé ; un refus n'appelle "
        "jamais l'opérateur. Exige le `decision_token` remis à la création "
        "(`401` s'il est invalide ou déjà utilisé, `409` si la transaction est "
        "déjà traitée)."
    ),
)
def decide_payment(reference: str, payload: DecisionIn) -> PaymentOut:
    transaction = payments.decide(
        reference=reference,
        decision_token=payload.decision_token,
        decision=payload.decision,
    )
    return _as_out(transaction)
