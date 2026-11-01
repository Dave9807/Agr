"""Tests du cycle de vie d'un paiement : création, consultation, décision.

Le parcours testé est celui du cahier des charges : créer → consulter →
le client confirme → consulter → le statut a évolué.
"""

import pytest

SUCCESS_NUMBER = "01970000"
OPERATOR_DECLINED_NUMBER = "01970001"
INSUFFICIENT_FUNDS_NUMBER = "01970002"
PENDING_NUMBER = "01970003"
UNKNOWN_NUMBER = "01979999"


def _payload(**overrides):
    payload = {
        "amount": 5000,
        "operator": "mtn",
        "merchant_reference": "CMD-2026-001",
        "test_number": SUCCESS_NUMBER,
    }
    payload.update(overrides)
    return payload


def _create(client, headers, **overrides):
    return client.post("/api/v1/payments", json=_payload(**overrides), headers=headers)


def _decide(client, reference, token, decision="CONFIRM"):
    return client.post(
        f"/api/v1/payments/{reference}/decision",
        json={"decision": decision, "decision_token": token},
    )


# --- Création -----------------------------------------------------------------


def test_creation_renvoie_201_et_le_statut_initial(client, api_headers):
    response = _create(client, api_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reference"].startswith("3dp_tx_")
    assert body["status"] == "CREATED"
    assert body["is_final"] is False
    assert body["mode"] == "SIMULATION"
    assert body["decision_token"].startswith("3dp_dec_")
    assert body["amount"] == 5000
    assert body["currency"] == "XOF"
    assert body["operator"] == "mtn"
    assert body["merchant_reference"] == "CMD-2026-001"
    assert body["test_number"] == SUCCESS_NUMBER
    # Le propriétaire de la transaction (merchant_id) ne sort jamais de l'API.
    assert "merchant_id" not in body


def test_http_201_ne_signifie_pas_paiement_reussi(client, api_headers):
    """Leçon centrale : code HTTP (201) ≠ statut métier (CREATED, pas SUCCEEDED)."""
    body = _create(client, api_headers).json()

    assert body["status"] != "SUCCEEDED"


def test_creation_sans_cle_api_renvoie_401(client):
    response = _create(client, headers={})

    assert response.status_code == 401
    assert response.json()["detail"] == "En-tête Authorization manquant."


def test_creation_avec_jeton_de_session_renvoie_401(client, registered):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": registered["email"], "password": "motdepasse123"},
    )
    assert login.status_code == 200

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = _create(client, headers)

    assert response.status_code == 401
    assert "Clé API secrète attendue" in response.json()["detail"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"operator": "orange"},
        {"test_number": "123"},
        {"test_number": "0197000a"},
        {"currency": "EUR"},
    ],
)
def test_creation_refuse_un_corps_invalide(client, api_headers, overrides):
    assert _create(client, api_headers, **overrides).status_code == 422


def test_creation_avec_champ_obligatoire_manquant_renvoie_422(client, api_headers):
    """Un champ obligatoire absent du corps (ici `test_number`) → 422."""
    payload = _payload()
    payload.pop("test_number")

    response = client.post("/api/v1/payments", json=payload, headers=api_headers)

    assert response.status_code == 422


def test_chaque_creation_a_une_reference_unique(client, api_headers):
    first = _create(client, api_headers).json()
    second = _create(client, api_headers).json()

    assert first["reference"] != second["reference"]


# --- Consultation -------------------------------------------------------------


def test_consultation_renvoie_la_transaction(client, api_headers):
    created = _create(client, api_headers).json()

    response = client.get(f"/api/v1/payments/{created['reference']}", headers=api_headers)

    assert response.status_code == 200
    assert response.json()["reference"] == created["reference"]
    # Le jeton de décision n'est jamais réaffiché après la création.
    assert "decision_token" not in response.json()


def test_consultation_reference_inconnue_renvoie_404(client, api_headers):
    response = client.get("/api/v1/payments/3dp_tx_inexistante", headers=api_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction introuvable."


def test_consultation_sans_cle_api_renvoie_401(client, api_headers):
    created = _create(client, api_headers).json()

    response = client.get(f"/api/v1/payments/{created['reference']}")

    assert response.status_code == 401


def test_un_compte_ne_voit_pas_la_transaction_d_un_autre(client, api_headers):
    created = _create(client, api_headers).json()

    autre = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Boutique Concurrente",
            "email": "concurrent@test.bj",
            "password": "motdepasse123",
        },
    ).json()
    autre_headers = {"Authorization": f"Bearer {autre['secret_key']}"}

    response = client.get(
        f"/api/v1/payments/{created['reference']}", headers=autre_headers
    )

    # 404 et non 403 : un compte ne doit même pas savoir que la référence existe.
    assert response.status_code == 404


# --- Décision : succès et refus du client ------------------------------------


def test_confirmation_conduit_a_succeeded(client, api_headers):
    created = _create(client, api_headers).json()

    response = _decide(client, created["reference"], created["decision_token"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["is_final"] is True
    assert body["reason"] is None


def test_refus_du_client_donne_declined_by_customer(client, api_headers):
    created = _create(client, api_headers).json()

    response = _decide(
        client, created["reference"], created["decision_token"], decision="DECLINE"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "DECLINED_BY_CUSTOMER"
    assert body["reason"] == "CUSTOMER_DECLINED"
    assert body["is_final"] is True


def test_refus_du_client_n_appelle_pas_l_operateur(client, api_headers):
    # Numéro de succès : si l'opérateur était appelé malgré le refus,
    # le statut deviendrait SUCCEEDED. Ce test prouve qu'il ne l'est pas.
    created = _create(client, api_headers, test_number=SUCCESS_NUMBER).json()

    body = _decide(
        client, created["reference"], created["decision_token"], decision="DECLINE"
    ).json()

    assert body["status"] == "DECLINED_BY_CUSTOMER"


# --- Décision : résultats de l'opérateur simulé ------------------------------


@pytest.mark.parametrize(
    ("test_number", "status_attendu", "reason"),
    [
        (SUCCESS_NUMBER, "SUCCEEDED", None),
        (OPERATOR_DECLINED_NUMBER, "REJECTED_BY_OPERATOR", "OPERATOR_DECLINED"),
        (INSUFFICIENT_FUNDS_NUMBER, "REJECTED_BY_OPERATOR", "INSUFFICIENT_FUNDS"),
        (UNKNOWN_NUMBER, "REJECTED_BY_OPERATOR", "INVALID_TEST_NUMBER"),
    ],
)
def test_confirmation_applique_les_regles_du_numero_de_test(
    client, api_headers, test_number, status_attendu, reason
):
    created = _create(client, api_headers, test_number=test_number).json()

    body = _decide(client, created["reference"], created["decision_token"]).json()

    assert body["status"] == status_attendu
    assert body["reason"] == reason


def test_numero_d_attente_donne_processing_et_non_un_succes(client, api_headers):
    created = _create(client, api_headers, test_number=PENDING_NUMBER).json()

    body = _decide(client, created["reference"], created["decision_token"]).json()

    assert body["status"] == "PROCESSING"
    assert body["is_final"] is False


@pytest.mark.parametrize("operator", ["mtn", "moov", "celtiis"])
def test_memes_resultats_quel_que_soit_l_operateur(client, api_headers, operator):
    created = _create(
        client, api_headers, operator=operator, test_number=OPERATOR_DECLINED_NUMBER
    ).json()

    body = _decide(client, created["reference"], created["decision_token"]).json()

    assert body["status"] == "REJECTED_BY_OPERATOR"
    assert body["reason"] == "OPERATOR_DECLINED"


# --- Décision : garde-fous ----------------------------------------------------


def test_decision_avec_un_jeton_invalide_renvoie_401(client, api_headers):
    created = _create(client, api_headers).json()

    response = _decide(client, created["reference"], "3dp_dec_totalement_faux")

    assert response.status_code == 401
    assert "Jeton de décision" in response.json()["detail"]


def test_decision_sans_jeton_renvoie_422(client, api_headers):
    created = _create(client, api_headers).json()

    response = client.post(
        f"/api/v1/payments/{created['reference']}/decision",
        json={"decision": "CONFIRM"},
    )

    assert response.status_code == 422


def test_une_transaction_ne_peut_etre_decidee_deux_fois(client, api_headers):
    created = _create(client, api_headers).json()
    _decide(client, created["reference"], created["decision_token"])

    # Deuxième tentative, avec le même jeton pourtant valide à l'origine.
    response = _decide(client, created["reference"], created["decision_token"])

    assert response.status_code == 409
    assert "déjà traitée" in response.json()["detail"]


def test_le_jeton_d_une_autre_transaction_est_refuse(client, api_headers):
    premiere = _create(client, api_headers).json()
    seconde = _create(client, api_headers).json()

    response = _decide(client, seconde["reference"], premiere["decision_token"])

    assert response.status_code == 401
    # La première transaction reste intacte.
    assert (
        client.get(
            f"/api/v1/payments/{premiere['reference']}", headers=api_headers
        ).json()["status"]
        == "CREATED"
    )


def test_decision_sur_reference_inconnue_renvoie_404(client, api_headers):
    response = _decide(client, "3dp_tx_inexistante", "3dp_dec_quelconque")

    assert response.status_code == 404


# --- Parcours complet ---------------------------------------------------------


def test_parcours_complet_creation_decision_consultation(client, api_headers):
    created = _create(client, api_headers).json()
    assert created["status"] == "CREATED"

    before = client.get(
        f"/api/v1/payments/{created['reference']}", headers=api_headers
    ).json()
    assert before["status"] == "CREATED"
    assert before["is_final"] is False

    decided = _decide(client, created["reference"], created["decision_token"]).json()
    assert decided["status"] == "SUCCEEDED"

    after = client.get(
        f"/api/v1/payments/{created['reference']}", headers=api_headers
    ).json()
    assert after["status"] == "SUCCEEDED"
    assert after["is_final"] is True
    assert after["updated_at"] >= after["created_at"]
