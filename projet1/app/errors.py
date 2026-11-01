"""Erreurs applicatives portant leur code HTTP.

Un seul gestionnaire dans `main.py` les transforme en réponses JSON
structurées `{"detail": "..."}` : le code HTTP reste distinct du contenu
métier, conformément au cahier des charges.
"""


class AppError(Exception):
    """Erreur métier avec son code HTTP."""

    status_code: int = 400

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class AuthError(AppError):
    """401 (jeton absent/invalide) ou 403 (compte suspendu)."""


class TransactionError(AppError):
    """404 (référence inconnue) ou 409 (transition interdite)."""


class IdempotencyError(AppError):
    """409 : clé d'idempotence réutilisée avec une requête différente."""


class WebhookError(AppError):
    """422 : URL de webhook refusée (protection SSRF, schéma invalide…)."""


class RateLimitError(AppError):
    """429 : trop de requêtes sur une route sensible."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            429,
            "Trop de requêtes sur cette route : réessayez dans "
            f"{retry_after} seconde(s).",
        )
        self.retry_after = retry_after
