"""Route publique : liste des opérateurs Mobile Money simulés."""

from fastapi import APIRouter

from app.models.schemas import OperatorOut
from app.operators.registry import OPERATORS

router = APIRouter(tags=["Opérateurs"])


@router.get(
    "/api/v1/operators",
    response_model=list[OperatorOut],
    summary="Lister les opérateurs disponibles",
    description="Route publique. Renvoie MTN Mobile Money, Moov Money et Celtiis Cash.",
)
def list_operators() -> list[OperatorOut]:
    return OPERATORS
