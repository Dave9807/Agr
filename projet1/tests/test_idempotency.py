"""Phase 6 — idempotence : une requête rejouée ne crée jamais deux transactions."""

PAYLOAD = {
    "amount": 3000,
    "operator": "mtn",
    "merchant_reference": "CMD-IDEM",
    "test_number": "01970000",
}


def _post(client, headers, payload=None, key="cle-001"):
    return client.post(
        "/api/v1/payments",
        json=payload or PAYLOAD,
        headers={**headers, "Idempotency-Key": key},
    )


def test_rejouer_la_meme_requete_renvoie_la_meme_transaction(client, api_headers):
    first = _post(client, api_headers)
    second = _post(client, api_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["reference"] == second.json()["reference"]


def test_rejouer_ne_cree_qu_une_transaction_en_base(client, api_headers, session_headers):
    _post(client, api_headers)
    _post(client, api_headers)

    transactions = client.get("/api/v1/dashboard/transactions", headers=session_headers)

    assert len(transactions.json()) == 1


def test_le_rejeu_renvoie_un_jeton_de_decision_utilisable(client, api_headers):
    _post(client, api_headers)
    replay = _post(client, api_headers).json()

    response = client.post(
        f"/api/v1/payments/{replay['reference']}/decision",
        json={"decision": "CONFIRM", "decision_token": replay["decision_token"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUCCEEDED"


def test_meme_cle_avec_un_corps_different_renvoie_409(client, api_headers):
    _post(client, api_headers)

    other = dict(PAYLOAD, amount=9999)
    response = _post(client, api_headers, payload=other)

    assert response.status_code == 409
    assert "idempotence" in response.json()["detail"].lower()


def test_deux_sans_cle_creent_deux_transactions(client, api_headers):
    first = client.post("/api/v1/payments", json=PAYLOAD, headers=api_headers)
    second = client.post("/api/v1/payments", json=PAYLOAD, headers=api_headers)

    assert first.json()["reference"] != second.json()["reference"]


def test_la_cle_d_idempotence_est_propre_a_chaque_marchand(
    client, api_headers, second_merchant
):
    first = _post(client, api_headers)

    autre_headers = {"Authorization": f"Bearer {second_merchant['secret_key']}"}
    second = _post(client, autre_headers)

    assert first.json()["reference"] != second.json()["reference"]
