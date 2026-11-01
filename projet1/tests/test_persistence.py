"""Phase 6 — persistance : les données survivent au redémarrage.

On simule un redémarrage en vidant la mémoire vive (cache du service et
sessions) : seules les données réellement écrites en base doivent subsister.
"""

from app.services import auth, payments

PASSWORD = "motdepasse123"


def _create(client, headers):
    return client.post(
        "/api/v1/payments",
        json={
            "amount": 7000,
            "operator": "moov",
            "merchant_reference": "CMD-PERSIST",
            "test_number": "01970000",
        },
        headers=headers,
    ).json()


def test_une_transaction_survit_a_un_redemarrage(client, api_headers):
    created = _create(client, api_headers)

    payments._transactions.clear()  # simule la perte de la mémoire vive

    response = client.get(f"/api/v1/payments/{created['reference']}", headers=api_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["reference"] == created["reference"]
    assert body["status"] == "CREATED"
    assert body["amount"] == 7000


def test_un_statut_terminal_survit_a_un_redemarrage(client, api_headers):
    created = _create(client, api_headers)
    client.post(
        f"/api/v1/payments/{created['reference']}/decision",
        json={"decision": "CONFIRM", "decision_token": created["decision_token"]},
    )

    payments._transactions.clear()

    body = client.get(
        f"/api/v1/payments/{created['reference']}", headers=api_headers
    ).json()

    assert body["status"] == "SUCCEEDED"
    assert body["is_final"] is True


def test_un_compte_survit_a_un_redemarrage(client, registered):
    auth._sessions.clear()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["access_token"].startswith("sess_")


def test_la_cle_secrete_reste_valide_apres_redemarrage(client, registered):
    auth._sessions.clear()
    payments._transactions.clear()

    response = client.post(
        "/api/v1/payments",
        json={"amount": 1000, "operator": "mtn", "test_number": "01970000"},
        headers={"Authorization": f"Bearer {registered['secret_key']}"},
    )

    assert response.status_code == 201, response.text
