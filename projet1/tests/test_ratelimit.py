"""Phase 6 — limitation du débit : réponse 429 explicite sur les routes sensibles.

Le seuil des tests est de 5 requêtes/minute (voir `tests/conftest.py`).
"""

LOGIN = {"email": "marchand@test.bj", "password": "motdepasse123"}


def test_le_bourrage_sur_login_finit_en_429(client, registered):
    codes = [client.post("/api/v1/auth/login", json=LOGIN).status_code for _ in range(6)]

    assert 429 in codes
    assert codes.count(429) >= 1


def test_la_reponse_429_est_explicite_et_indique_le_delai(client, registered):
    for _ in range(6):
        response = client.post("/api/v1/auth/login", json=LOGIN)

    assert response.status_code == 429
    assert "Trop de requêtes" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) >= 1


def test_l_inscription_est_limitee_aussi(client):
    codes = []
    for index in range(6):
        codes.append(
            client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Boutique",
                    "email": f"bourrage{index}@test.bj",
                    "password": "motdepasse123",
                },
            ).status_code
        )

    assert 429 in codes


def test_les_routes_de_paiement_sont_limitees(client, api_headers):
    payload = {"amount": 1000, "operator": "mtn", "test_number": "01970000"}
    codes = [
        client.post("/api/v1/payments", json=payload, headers=api_headers).status_code
        for _ in range(6)
    ]

    assert 429 in codes
