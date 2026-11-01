"""Règles communes à l'opérateur Mobile Money simulé.

Aucune API opérateur réelle n'est appelée, aucun numéro réel n'est demandé :
le résultat d'un paiement est décidé par le **numéro de test** transmis par
le marchand.

Règles (mode « règles ») : un seul numéro fictif, commun aux trois
opérateurs, donc MTN, Moov et Celtiis renvoient le **même** résultat pour un
même numéro. Les valeurs sont publiées dans `docs/NUMEROS_DE_TEST.md`.

Mode « contrôlé » : `forced_outcome` force un résultat pour les tests et les
démonstrations. Il n'est **jamais** exposé par une route HTTP (F13 : un
mécanisme de forçage reste un outil de test, pas une fonction publique
d'intégration) ; seul du code interne — ici les tests — peut l'utiliser.
"""

from dataclasses import dataclass

# --- Résultats possibles de l'opérateur simulé -------------------------------

SUCCESS = "SUCCESS"
DECLINED = "DECLINED"
INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
PENDING = "PENDING"
INVALID_TEST_NUMBER = "INVALID_TEST_NUMBER"
FAILED = "FAILED"


@dataclass(frozen=True)
class OperatorResult:
    """Réponse de l'opérateur simulé.

    `outcome` est le vocabulaire de l'opérateur ; la traduction en statut
    métier de l'agrégateur est faite par `app/services/payments.py`.
    """

    outcome: str
    reason: str | None
    message: str


# --- Numéros de test (mode règles) -------------------------------------------

TEST_SCENARIOS: dict[str, OperatorResult] = {
    "01970000": OperatorResult(
        outcome=SUCCESS,
        reason=None,
        message="Paiement accepté par l'opérateur simulé.",
    ),
    "01970001": OperatorResult(
        outcome=DECLINED,
        reason="OPERATOR_DECLINED",
        message="Paiement refusé par l'opérateur simulé.",
    ),
    "01970002": OperatorResult(
        outcome=INSUFFICIENT_FUNDS,
        reason="INSUFFICIENT_FUNDS",
        message="Solde Mobile Money insuffisant (simulation).",
    ),
    "01970003": OperatorResult(
        outcome=PENDING,
        reason=None,
        message="Résultat non définitif : l'opérateur simulé n'a pas encore répondu.",
    ),
}

# Numéro inconnu : choix sûr, jamais un succès inventé. Le marchand reçoit un
# refus explicite qui renvoie vers la documentation des numéros de test.
INVALID_TEST_NUMBER_RESULT = OperatorResult(
    outcome=INVALID_TEST_NUMBER,
    reason="INVALID_TEST_NUMBER",
    message=(
        "Numéro de test inconnu : aucun scénario associé. "
        "Voir docs/NUMEROS_DE_TEST.md."
    ),
)

# --- Mode contrôlé (outil de test, jamais exposé par HTTP) -------------------

FORCED_OUTCOMES: dict[str, OperatorResult] = {
    SUCCESS: OperatorResult(
        outcome=SUCCESS,
        reason=None,
        message="Succès forcé (mode contrôlé).",
    ),
    DECLINED: OperatorResult(
        outcome=DECLINED,
        reason="OPERATOR_DECLINED",
        message="Refus opérateur forcé (mode contrôlé).",
    ),
    INSUFFICIENT_FUNDS: OperatorResult(
        outcome=INSUFFICIENT_FUNDS,
        reason="INSUFFICIENT_FUNDS",
        message="Solde insuffisant forcé (mode contrôlé).",
    ),
    PENDING: OperatorResult(
        outcome=PENDING,
        reason=None,
        message="Attente forcée (mode contrôlé).",
    ),
    FAILED: OperatorResult(
        outcome=FAILED,
        reason="OPERATOR_ERROR",
        message="Échec technique forcé (mode contrôlé).",
    ),
}


def simulate(
    operator_id: str,
    test_number: str,
    forced_outcome: str | None = None,
) -> OperatorResult:
    """Retourne le résultat simulé pour un numéro de test.

    `forced_outcome` (mode contrôlé) prend le pas sur les règles ; une valeur
    inconnue lève `ValueError` plutôt que de produire un résultat au hasard.
    """
    if forced_outcome is not None:
        result = FORCED_OUTCOMES.get(forced_outcome)
        if result is None:
            raise ValueError(f"Résultat forcé inconnu : {forced_outcome!r}.")
    else:
        result = TEST_SCENARIOS.get(test_number)

    if result is None:
        return INVALID_TEST_NUMBER_RESULT

    # L'opérateur est rappelé dans le message pour tracer l'origine.
    return OperatorResult(
        outcome=result.outcome,
        reason=result.reason,
        message=f"[{operator_id}] {result.message}",
    )
