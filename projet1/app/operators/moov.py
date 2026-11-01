"""Opérateur simulé Moov Money (Bénin).

Aucun appel à Moov n'est effectué : le module applique les règles communes de
`app/operators/base.py` (pilotées par le numéro de test).
"""

from app.operators.base import OperatorResult, simulate

OPERATOR_ID = "moov"
DISPLAY_NAME = "Moov Money"


def process(test_number: str, forced_outcome: str | None = None) -> OperatorResult:
    """Résultat simulé Moov pour ce numéro de test."""
    return simulate(OPERATOR_ID, test_number, forced_outcome)
