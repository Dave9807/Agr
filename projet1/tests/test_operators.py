"""Tests de la route publique /api/v1/operators."""


def test_operators_retourne_200(client):
    response = client.get("/api/v1/operators")

    assert response.status_code == 200


def test_operators_liste_les_trois_operateurs(client):
    body = client.get("/api/v1/operators").json()

    ids = [operator["id"] for operator in body]
    assert ids == ["mtn", "moov", "celtiis"]


def test_operators_chaque_operateur_a_son_nom(client):
    body = client.get("/api/v1/operators").json()

    noms = {operator["id"]: operator["name"] for operator in body}
    assert noms["mtn"] == "MTN Mobile Money"
    assert noms["moov"] == "Moov Money"
    assert noms["celtiis"] == "Celtiis Cash"
