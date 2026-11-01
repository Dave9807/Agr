"""Route publique : vérification de l'état de l'API (sans authentification)."""

from fastapi import APIRouter

from app.models.schemas import HealthOut

router = APIRouter(tags=["Système"])


@router.get(
    "/api/v1/health",
    response_model=HealthOut,
    summary="Santé de l'API",
    description="Route publique. Indique que l'API répond correctement.",
)
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        service="3DPAY API",
        version="1.0.0",
        mode="SIMULATION",
    )
