"""Routes d'authentification : inscription, connexion, session, rotation de clé.

Routes publiques :   /auth/register, /auth/login
Routes protégées :   /auth/me, /auth/logout  (jeton sess_…)
                     /keys/rotate            (clé secrète 3dp_sec_…)
"""

from fastapi import APIRouter, Depends, status

from app.config import settings
from app.deps import current_session_token, require_api_key, require_session
from app.models.schemas import (
    LoginIn,
    MessageOut,
    RegisterIn,
    RegisterOut,
    SecretKeyOut,
    SessionOut,
)
from app.services import auth
from app.services.ratelimit import limiter

router = APIRouter(prefix="/api/v1", tags=["Authentification"])

# Limitation du débit sur l'inscription et la connexion (phase 6).
_auth_limit = Depends(limiter("auth", settings.rate_limit_auth_per_minute))

_SECRET_NOTICE = (
    "Clé secrète affichée une seule fois. "
    "Stockez-la dans votre .env : elle ne sera plus récupérable."
)

_ACCOUNT_PUBLIC_FIELDS = ("id", "name", "email", "public_key", "status", "created_at")


@router.post(
    "/auth/register",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_auth_limit],
    summary="Inscrire un site marchand",
    description=(
        "Crée un compte et génère les deux clés. "
        "La clé secrète n'est affichée qu'une seule fois."
    ),
)
def register(payload: RegisterIn) -> RegisterOut:
    account, secret_key = auth.register(
        name=payload.name,
        email=payload.email,
        password=payload.password,
    )
    return RegisterOut(**account, secret_key=secret_key, notice=_SECRET_NOTICE)


@router.post(
    "/auth/login",
    response_model=SessionOut,
    dependencies=[_auth_limit],
    summary="Ouvrir une session",
    description=(
        "Vérifie e-mail + mot de passe et renvoie un jeton de session "
        "`sess_…` valable 24 h. À transmettre en `Authorization: Bearer`."
    ),
)
def login(payload: LoginIn) -> SessionOut:
    _, token = auth.login(email=payload.email, password=payload.password)
    return SessionOut(
        access_token=token,
        expires_in=int(auth.SESSION_TTL.total_seconds()),
    )


@router.get(
    "/auth/me",
    response_model=dict,
    summary="Compte courant",
    description="Retourne le compte identifié par le jeton de session.",
)
def me(account: dict = Depends(require_session)) -> dict:
    return {field: account[field] for field in _ACCOUNT_PUBLIC_FIELDS}


@router.post(
    "/auth/logout",
    response_model=MessageOut,
    summary="Fermer la session",
    description="Révoque immédiatement le jeton de session transmis.",
)
def logout(token: str = Depends(current_session_token)) -> MessageOut:
    auth.logout(token)
    return MessageOut(detail="Session fermée.")


@router.post(
    "/keys/rotate",
    response_model=SecretKeyOut,
    summary="Régénérer la clé secrète",
    description=(
        "Valide avec la clé secrète actuelle (`3dp_sec_…`), en génère une "
        "nouvelle et invalide l'ancienne immédiatement."
    ),
)
def rotate_key(account: dict = Depends(require_api_key)) -> SecretKeyOut:
    new_secret = auth.rotate_secret(account)
    return SecretKeyOut(secret_key=new_secret, notice=_SECRET_NOTICE)
