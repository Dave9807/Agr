"""Opérateur simulé Celtiis Cash (Bénin).

Aucun appel à Celtiis n'est effectué : le module applique les règles communes
de `app/operators/base.py` (pilotées par le numéro de test).
"""

from app.operators.base import OperatorResult, simulate

OPERATOR_ID = "celtiis"
DISPLAY_NAME = "Celtiis Cash"


def process(test_number: str, forced_outcome: str | None = None) -> OperatorResult:
    """Résultat simulé Celtiis pour ce numéro de test."""
    return simulate(OPERATOR_ID, test_number, forced_outcome)
