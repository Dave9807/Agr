"""Phase 8 — pages HTML de démonstration (boutique, widget, numéros de test)."""

import pytest


@pytest.mark.parametrize(
    "path",
    ["/", "/demo/boutique", "/demo/widget", "/demo/numeros-de-test"],
)
def test_les_pages_s_affichent(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert "SIMULATION" in response.text


def test_la_page_des_numeros_liste_les_scenarios(client):
    body = client.get("/demo/numeros-de-test").text

    assert "01970000" in body
    assert "01970001" in body
    assert "01970002" in body
    assert "01970003" in body
    assert "SUCCEEDED" in body


def test_la_boutique_et_le_widget_sont_relies(client):
    boutique = client.get("/demo/boutique").text
    widget = client.get("/demo/widget").text

    assert "/api/v1/payments" in boutique
    assert "decision_token" in boutique
    assert "/decision" in widget
