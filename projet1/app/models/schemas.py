"""Schémas Pydantic : validation des entrées et format des réponses JSON.

Pydantic refuse toute requête qui ne respecte pas ces modèles → réponse 422.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Motif simple d'adresse e-mail : tout avant @, tout après, un point obligatoire.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# Numéro de test : 8 chiffres. Ces numéros sont FICTIFS (voir docs/NUMEROS_DE_TEST.md).
TEST_NUMBER_PATTERN = r"^\d{8}$"


class HealthOut(BaseModel):
    """Réponse de la route /health."""

    status: str
    service: str
    version: str
    mode: str


class OperatorOut(BaseModel):
    """Un opérateur Mobile Money simulé."""

    id: str
    name: str
    country: str


class RegisterIn(BaseModel):
    """Corps attendu pour l'inscription d'un site marchand."""

    name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    """Corps attendu pour la connexion."""

    email: str = Field(pattern=EMAIL_PATTERN, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class AccountOut(BaseModel):
    """Informations publiques d'un compte marchand (jamais de secret)."""

    id: int
    name: str
    email: str
    public_key: str
    status: str
    created_at: str


class RegisterOut(AccountOut):
    """Réponse d'inscription : le compte PLUS la clé secrète (affichée 1 seule fois)."""

    secret_key: str
    notice: str


class SessionOut(BaseModel):
    """Réponse de connexion : jeton de session opaque."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SecretKeyOut(BaseModel):
    """Nouvelle clé secrète après rotation."""

    secret_key: str
    notice: str


class MessageOut(BaseModel):
    """Réponse de confirmation simple."""

    detail: str


class PaymentIn(BaseModel):
    """Corps attendu pour créer un paiement."""

    amount: int = Field(ge=1, le=10_000_000, description="Montant entier, en FCFA.")
    currency: Literal["XOF"] = "XOF"
    operator: Literal["mtn", "moov", "celtiis"] = Field(
        description="Opérateur choisi par le client sur le site marchand."
    )
    merchant_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Référence de la commande côté marchand (facultative).",
    )
    test_number: str = Field(
        pattern=TEST_NUMBER_PATTERN,
        description=(
            "Numéro de test à 8 chiffres, fictif. Il choisit le scénario "
            "(succès, refus, solde insuffisant, attente) — voir docs/NUMEROS_DE_TEST.md."
        ),
    )


class PaymentOut(BaseModel):
    """État enregistré d'une transaction.

    `status` est le statut métier, indépendant du code HTTP de la réponse.
    `is_final` évite de présenter un statut d'attente comme un succès.
    """

    reference: str
    status: str
    is_final: bool
    reason: str | None = None
    message: str
    amount: int
    currency: str
    operator: str
    merchant_reference: str | None = None
    test_number: str
    created_at: str
    updated_at: str
    mode: str = "SIMULATION"


class PaymentCreatedOut(PaymentOut):
    """Réponse de création : l'état PLUS le jeton de décision du client.

    Le jeton est affiché une seule fois et ne concerne que le client payeur :
    le marchand le place dans le lien de son widget de paiement.
    """

    decision_token: str
    notice: str


class DecisionIn(BaseModel):
    """Corps attendu pour la décision du client payeur."""

    decision: Literal["CONFIRM", "DECLINE"] = Field(
        description="CONFIRM = le client confirme ; DECLINE = le client refuse."
    )
    decision_token: str = Field(
        min_length=1,
        max_length=200,
        description="Jeton remis à la création de la transaction (usage unique).",
    )


# --- Tableau de bord ----------------------------------------------------------


class PublicKeyOut(BaseModel):
    """Clé publique du compte (affichable, sans risque)."""

    public_key: str
    notice: str


class WebhookDeliveryOut(BaseModel):
    """Une ligne du journal des webhooks (phase 7)."""

    id: int
    reference: str
    event: str
    url: str
    state: str
    attempts: int
    status_code: int | None = None
    response_body: str | None = None
    created_at: str


class DashboardSettingsOut(BaseModel):
    """Réglages du compte marchand."""

    name: str
    email: str
    public_key: str
    webhook_url: str | None = None
    status: str
    mode: str = "SIMULATION"


class DashboardSettingsIn(BaseModel):
    """Champs modifiables depuis le tableau de bord."""

    webhook_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL publique qui recevra les webhooks signés.",
    )
