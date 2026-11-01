"""Point d'entrée des opérateurs simulés.

Un module par opérateur (`mtn`, `moov`, `celtiis`), tous construits sur les
mêmes règles : schéma commun, résultats pilotés par le numéro de test.
"""

from types import ModuleType

from app.operators import celtiis, moov, mtn

_OPERATORS: dict[str, ModuleType] = {
    mtn.OPERATOR_ID: mtn,
    moov.OPERATOR_ID: moov,
    celtiis.OPERATOR_ID: celtiis,
}


def get_operator(operator_id: str) -> ModuleType:
    """Retourne le module de l'opérateur demandé.

    Lève `ValueError` si l'identifiant est inconnu — la validation Pydantic
    (`Literal["mtn", "moov", "celtiis"]`) l'interdit normalement en amont.
    """
    try:
        return _OPERATORS[operator_id]
    except KeyError:
        raise ValueError(f"Opérateur inconnu : {operator_id!r}.") from None
