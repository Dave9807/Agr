"""Tests de la route publique /api/v1/health."""


def test_health_retourne_200(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_health_signale_la_simulation(client):
    body = client.get("/api/v1/health").json()

    assert body["status"] == "ok"
    assert body["mode"] == "SIMULATION"
    assert body["service"] == "3DPAY API"
