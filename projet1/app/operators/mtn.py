"""Opérateur simulé MTN Mobile Money (Bénin).

Aucun appel à MTN n'est effectué : le module applique les règles communes de
`app/operators/base.py` (pilotées par le numéro de test).
"""

from app.operators.base import OperatorResult, simulate

OPERATOR_ID = "mtn"
DISPLAY_NAME = "MTN Mobile Money"


def process(test_number: str, forced_outcome: str | None = None) -> OperatorResult:
    """Résultat simulé MTN pour ce numéro de test."""
    return simulate(OPERATOR_ID, test_number, forced_outcome)
