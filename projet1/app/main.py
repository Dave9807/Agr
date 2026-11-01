"""Point d'entrée de l'API 3DPAY.

Lancement :
    uvicorn app.main:app --reload
Puis ouvrir http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.errors import AppError, RateLimitError
from app.routes import auth, dashboard, health, operators, pages
from app.routes import payments as payment_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("3dpay")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Crée les tables manquantes au démarrage (idempotent)."""
    init_db()
    logger.info(
        "3DPAY API démarrée — env=%s, base=%s", settings.app_env, settings.database_url
    )
    yield


app = FastAPI(
    title="3DPAY API",
    description=(
        "Agrégateur de paiement Mobile Money SIMULÉ (MTN Mobile Money, "
        "Moov Money, Celtiis Cash). Aucun argent réel ne circule. "
        "Deux authentifications distinctes : session `sess_…` (tableau de bord) "
        "et clé secrète `3dp_sec_…` (serveur marchand). Le client payeur n'a "
        "aucun compte : sa décision est prouvée par un `decision_token` à usage unique."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Routes publiques
app.include_router(health.router)
app.include_router(operators.router)
app.include_router(auth.router)

# Cycle de vie des paiements
app.include_router(payment_routes.router)

# Tableau de bord (session)
app.include_router(dashboard.router)

# Pages HTML de démonstration
app.include_router(pages.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Transforme toute erreur métier en réponse JSON structurée.

    `AuthError`, `PaymentError`, `IdempotencyError`, `WebhookError` et
    `RateLimitError` en héritent : un seul point de traduction, donc des
    réponses homogènes (`401`, `403`, `404`, `409`, `422`, `429`).
    """
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "mode": settings.simulation_label},
        headers=headers,
    )
