"""Phase 8 — tableau de bord : isolation, transactions, clés, réglages."""

PAYLOAD = {"amount": 1500, "operator": "moov", "test_number": "01970000"}


def _create(client, headers):
    return client.post("/api/v1/payments", json=PAYLOAD, headers=headers).json()


def test_le_tableau_de_bord_exige_une_session(client):
    response = client.get("/api/v1/dashboard/transactions")

    assert response.status_code == 401


def test_la_cle_secrete_n_ouvre_pas_le_tableau_de_bord(client, api_headers):
    response = client.get("/api/v1/dashboard/transactions", headers=api_headers)

    assert response.status_code == 401


def test_le_tableau_de_bord_liste_mes_transactions(client, api_headers, session_headers):
    _create(client, api_headers)

    response = client.get("/api/v1/dashboard/transactions", headers=session_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_le_tableau_de_bord_ne_montre_pas_les_transactions_des_autres(
    client, api_headers, session_headers, second_merchant
):
    _create(client, api_headers)
    autre = {"Authorization": f"Bearer {second_merchant['secret_key']}"}
    _create(client, autre)

    response = client.get("/api/v1/dashboard/transactions", headers=session_headers)

    assert len(response.json()) == 1
    assert response.json()[0]["merchant_reference"] is None


def test_le_detail_d_une_transaction_d_un_autre_compte_renvoie_404(
    client, api_headers, session_headers, second_merchant
):
    autre = {"Authorization": f"Bearer {second_merchant['secret_key']}"}
    created = _create(client, autre)

    response = client.get(
        f"/api/v1/dashboard/transactions/{created['reference']}", headers=session_headers
    )

    assert response.status_code == 404


def test_les_cles_affichent_la_cle_publique_jamais_la_secrete(
    client, registered, session_headers
):
    response = client.get("/api/v1/dashboard/keys", headers=session_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["public_key"] == registered["public_key"]
    assert registered["secret_key"] not in str(body)


def test_la_rotation_depuis_le_tableau_de_bord_revoque_l_ancienne_cle(
    client, registered, session_headers
):
    ancienne = registered["secret_key"]

    response = client.post("/api/v1/dashboard/keys/rotate", headers=session_headers)

    assert response.status_code == 200
    nouvelle = response.json()["secret_key"]
    assert nouvelle != ancienne
    assert (
        client.post(
            "/api/v1/payments",
            json=PAYLOAD,
            headers={"Authorization": f"Bearer {ancienne}"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/payments",
            json=PAYLOAD,
            headers={"Authorization": f"Bearer {nouvelle}"},
        ).status_code
        == 201
    )


def test_les_reglages_montrent_le_compte_et_l_url_de_webhook(
    client, session_headers
):
    response = client.get("/api/v1/dashboard/settings", headers=session_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "marchand@test.bj"
    assert body["webhook_url"] is None
    assert body["mode"] == "SIMULATION"


def test_on_peut_enregistrer_puis_effacer_l_url_de_webhook(client, session_headers):
    first = client.patch(
        "/api/v1/dashboard/settings",
        json={"webhook_url": "https://example.com/hook"},
        headers=session_headers,
    )
    assert first.status_code == 200
    assert first.json()["webhook_url"] == "https://example.com/hook"

    second = client.patch(
        "/api/v1/dashboard/settings",
        json={"webhook_url": None},
        headers=session_headers,
    )
    assert second.status_code == 200
    assert second.json()["webhook_url"] is None
