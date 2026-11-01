"""Limitation du débit (rate limiting) — fenêtre glissante en mémoire.

Protège les routes sensibles (`/auth/*`, `/payments`) contre le bourrage
et la force brute : au-delà du seuil, réponse **429** avec `Retry-After`.

Implémentation volontairement sans dépendance externe (le plan prévoyait
`slowapi` ; une fenêtre glissante maison suffit pour un MVP et évite une
dépendance supplémentaire). Les seuils viennent du `.env`.
"""

import time
from collections import deque

from fastapi import Request

from app.config import settings
from app.errors import RateLimitError

WINDOW_SECONDS = 60

# (portée, client) -> horodatages des requêtes de la fenêtre courante
_hits: dict[tuple[str, str], deque[float]] = {}


def reset() -> None:
    """Vide les compteurs — réservé aux tests."""
    _hits.clear()


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "inconnu"


def limiter(scope: str, limit: int):
    """Fabrique une dépendance FastAPI de limitation pour une portée donnée."""

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled or limit <= 0:
            return

        monotonic_now = time.monotonic()
        key = (scope, _client_key(request))
        bucket = _hits.setdefault(key, deque())

        while bucket and monotonic_now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, int(WINDOW_SECONDS - (monotonic_now - bucket[0])))
            raise RateLimitError(retry_after)

        bucket.append(monotonic_now)

    return dependency
