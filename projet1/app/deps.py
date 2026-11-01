"""Dépendances FastAPI : lecture et contrôle des en-têtes d'authentification.

Ces fonctions sont appelées automatiquement par FastAPI via Depends()
avant même d'exécuter le code de la route.

Deux types de jetons sont reconnus, tous transmis dans le même en-tête :

    Authorization: Bearer <jeton>

    3dp_sec_…  -> clé secrète d'API      (appels machine -> machine)
    sess_…     -> jeton de session       (tableau de bord, tests)

Le schéma HTTPBearer (et non un simple paramètre "Authorization") est
indispensable : c'est lui qui déclenche le bouton « Authorize » de
Swagger UI et garantit que l'en-tête est bien transmis. Un paramètre
brut nommé "Authorization" est ignoré par Swagger UI.
"""

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth import (
    AuthError,
    authenticate_api_key,
    get_session_account,
)

# Schéma de sécurité unique : présent dans le document OpenAPI comme
# "bearerHTTP", il affiche le cadenas Authorize sur /docs.
_bearer_scheme = HTTPBearer(
    auto_error=False,
    description=(
        "Collez votre jeton sans le préfixe « Bearer » (ajouté automatiquement) :\n"
        "- `sess_…` : jeton de session (routes /auth/me et /auth/logout)\n"
        "- `3dp_sec_…` : clé secrète d'API (routes protégées, ex. /keys/rotate)"
    ),
)


def _extract_bearer(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    """Contrôle l'en-tête Authorization et retourne le jeton nu.

    Trois situations, trois messages distincts (jamais d'erreur 500) :
    - en-tête absent          -> 401 "En-tête Authorization manquant."
    - schéma autre que Bearer -> 401 "Format attendu : …"
    - jeton vide              -> 401 "Format attendu : …"
    """
    raw_header = request.headers.get("Authorization")
    if not raw_header:
        raise AuthError(401, "En-tête Authorization manquant.")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError(401, "Format attendu : Authorization: Bearer <jeton>.")

    token = credentials.credentials.strip()
    if not token:
        raise AuthError(401, "Format attendu : Authorization: Bearer <jeton>.")
    return token


def current_session_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> str:
    """Valide le format d'un jeton de session `sess_…` et le retourne."""
    token = _extract_bearer(request, credentials)
    if not token.startswith("sess_"):
        raise AuthError(401, "Jeton de session attendu (sess_...).")
    return token


def require_session(
    token: str = Depends(current_session_token),
) -> dict:
    """Compte marchand identifié par session — pour /auth/me et /auth/logout."""
    return get_session_account(token)


def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> dict:
    """Compte marchand identifié par clé secrète — pour les routes API protégées."""
    token = _extract_bearer(request, credentials)
    if not token.startswith("3dp_sec_"):
        raise AuthError(401, "Clé API secrète attendue (3dp_sec_...).")
    return authenticate_api_key(token)
