"""Phase 7 — webhooks signés : HMAC, retry ×5, journal et protection SSRF.

Le transport HTTP est remplacé (`_http_post`) : les tests ne dépendent
d'aucun réseau et restent déterministes.
"""

import pytest

from app.config import settings
from app.services import webhooks

PAYLOAD = {"amount": 4200, "operator": "mtn", "test_number": "01970000"}


def _set_webhook(client, session_headers, url):
    return client.patch(
        "/api/v1/dashboard/settings",
        json={"webhook_url": url},
        headers=session_headers,
    )


def _pay_and_confirm(client, api_headers):
    created = client.post("/api/v1/payments", json=PAYLOAD, headers=api_headers).json()
    return client.post(
        f"/api/v1/payments/{created['reference']}/decision",
        json={"decision": "CONFIRM", "decision_token": created["decision_token"]},
    ).json()


# --- Signature ----------------------------------------------------------------


def test_signature_deterministe_et_verifiable():
    body = b'{"event":"transaction.succeeded"}'

    signature = webhooks.sign(body)

    assert signature.startswith("sha256=")
    assert webhooks.verify(body, signature) is True
    assert webhooks.verify(body + b"x", signature) is False


def test_la_signature_depend_du_secret(monkeypatch):
    body = b"{}"
    before = webhooks.sign(body)

    monkeypatch.setattr(settings, "webhook_secret", "un-autre-secret")

    assert webhooks.sign(body) != before


# --- Livraison ----------------------------------------------------------------


def test_un_marchand_qui_repond_2xx_recoit_un_seul_envoi(
    client, api_headers, session_headers, monkeypatch
):
    assert _set_webhook(client, session_headers, "http://example.com/hook").status_code == 200

    appels = []

    def faux_post(url, body, headers):
        appels.append(url)
        return 200, "ok"

    monkeypatch.setattr(webhooks, "_http_post", faux_post)

    _pay_and_confirm(client, api_headers)

    journal = client.get("/api/v1/dashboard/webhooks", headers=session_headers).json()
    assert len(appels) == 1
    assert len(journal) == 1
    assert journal[0]["event"] == "transaction.succeeded"
    assert journal[0]["attempts"] == 1
    assert journal[0]["state"] == "delivered"
    assert journal[0]["status_code"] == 200


def test_un_marchand_muet_recoit_cinq_tentatives(
    client, api_headers, session_headers, monkeypatch
):
    _set_webhook(client, session_headers, "http://example.com/hook")

    appels = []

    def faux_post(url, body, headers):
        appels.append(url)
        return 500, "boom"

    monkeypatch.setattr(webhooks, "_http_post", faux_post)

    _pay_and_confirm(client, api_headers)

    journal = client.get("/api/v1/dashboard/webhooks", headers=session_headers).json()
    assert len(appels) == settings.webhook_max_attempts == 5
    assert journal[0]["attempts"] == 5
    assert journal[0]["state"] == "failed"
    assert journal[0]["status_code"] == 500


def test_un_refus_client_declenche_un_webhook_declined(
    client, api_headers, session_headers, monkeypatch
):
    _set_webhook(client, session_headers, "http://example.com/hook")
    monkeypatch.setattr(webhooks, "_http_post", lambda *args: (204, ""))

    created = client.post("/api/v1/payments", json=PAYLOAD, headers=api_headers).json()
    client.post(
        f"/api/v1/payments/{created['reference']}/decision",
        json={"decision": "DECLINE", "decision_token": created["decision_token"]},
    )

    journal = client.get("/api/v1/dashboard/webhooks", headers=session_headers).json()
    assert journal[0]["event"] == "transaction.declined"


def test_sans_url_de_webhook_aucune_livraison(
    client, api_headers, session_headers
):
    _pay_and_confirm(client, api_headers)

    journal = client.get("/api/v1/dashboard/webhooks", headers=session_headers).json()
    assert journal == []


def test_le_get_de_consultation_reste_le_repli(
    client, api_headers, session_headers, monkeypatch
):
    """Même si le webhook échoue, le marchand peut toujours consulter."""
    _set_webhook(client, session_headers, "http://example.com/hook")
    monkeypatch.setattr(webhooks, "_http_post", lambda *args: (None, "timeout"))

    transaction = _pay_and_confirm(client, api_headers)

    response = client.get(f"/api/v1/payments/{transaction['reference']}", headers=api_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCEEDED"


# --- Protection SSRF ----------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9999/hook",
        "http://localhost/hook",
        "http://192.168.1.10/hook",
        "http://10.0.0.5/hook",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/hook",
    ],
)
def test_une_url_interne_est_refusee(
    client, session_headers, monkeypatch, url
):
    monkeypatch.setattr(settings, "webhook_block_private", True)

    response = _set_webhook(client, session_headers, url)

    assert response.status_code == 422
    assert "SSRF" in response.json()["detail"] or "invalide" in response.json()["detail"]


def test_une_url_publique_est_acceptee(client, session_headers, monkeypatch):
    monkeypatch.setattr(settings, "webhook_block_private", True)
    # Résolution DNS simulée : le test ne dépend d'aucun accès réseau.
    monkeypatch.setattr(
        webhooks.socket,
        "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    response = _set_webhook(client, session_headers, "https://example.com/hook")

    assert response.status_code == 200
    assert response.json()["webhook_url"] == "https://example.com/hook"
