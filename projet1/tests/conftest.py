"""Configuration partagée des tests : client HTTP + isolation des données.

Les variables d'environnement sont posées **avant** l'import de
l'application : `app.config` les lit au chargement du module. La base SQLite
en mémoire (avec un pool partagé) garantit que chaque exécution de tests
ne touche jamais la base de développement `3dpay.db`.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("WEBHOOK_BLOCK_PRIVATE", "false")
os.environ.setdefault("WEBHOOK_SECRET", "secret-de-test-uniquement")
os.environ.setdefault("WEBHOOK_RETRY_DELAY_SECONDS", "0")
os.environ.setdefault("RATE_LIMIT_AUTH_PER_MINUTE", "5")
os.environ.setdefault("RATE_LIMIT_PAYMENTS_PER_MINUTE", "5")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import auth, payments, ratelimit  # noqa: E402

MERCHANT = {
    "name": "Boutique Test",
    "email": "marchand@test.bj",
    "password": "motdepasse123",
}


@pytest.fixture()
def client():
    """Client de test FastAPI, avec une base vierge pour chaque test."""
    auth.reset()
    payments.reset()
    ratelimit.reset()
    with TestClient(app) as test_client:
        yield test_client
    auth.reset()
    payments.reset()
    ratelimit.reset()


@pytest.fixture()
def registered(client):
    """Compte de test déjà inscrit, tel que renvoyé par l'API."""
    response = client.post("/api/v1/auth/register", json=MERCHANT)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def api_headers(registered):
    """En-tête d'authentification machine (clé secrète)."""
    return {"Authorization": f"Bearer {registered['secret_key']}"}


@pytest.fixture()
def session_headers(client, registered):
    """En-tête de session (tableau de bord)."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": MERCHANT["email"], "password": MERCHANT["password"]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def second_merchant(client):
    """Un second compte, pour vérifier l'isolation des données."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Deuxième Boutique",
            "email": "autre@test.bj",
            "password": "autremotdepasse",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_payment(client, api_headers, **overrides) -> dict:
    """Helper : crée un paiement avec des valeurs par défaut valides."""
    payload = {
        "amount": 2500,
        "currency": "XOF",
        "order_reference": "CMD-001",
        "operator": "mtn",
        "phone": "+22997000001",
    }
    payload.update(overrides)
    response = client.post("/api/v1/payments", json=payload, headers=api_headers)
    assert response.status_code == 201, response.text
    return response.json()
