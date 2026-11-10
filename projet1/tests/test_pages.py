"""Phase 8 — pages HTML de démonstration (boutique, widget, numéros de test)."""

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/demo/inscription",
        "/demo/connexion",
        "/demo/espace",
        "/demo/boutique",
        "/demo/widget",
        "/demo/numeros-de-test",
    ],
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


def test_les_pages_de_demo_presentent_le_parcours_et_les_scenarios(client):
    home = client.get("/").text
    registration = client.get("/demo/inscription").text
    shop = client.get("/demo/boutique").text
    widget = client.get("/demo/widget").text
    numbers = client.get("/demo/numeros-de-test").text

    assert "class=\"steps\"" in home
    assert "class=\"journey-step active\"" in registration
    assert "Créer votre compte" in registration
    assert "class=\"shop-layout\"" in shop
    assert "class=\"journey-step complete\"" in widget
    assert "id=\"result-stage\"" in widget
    assert "class=\"table-wrap\"" in numbers
    assert "01970003" in shop


def test_la_cle_de_demo_n_est_pas_stockee_dans_le_navigateur(client):
    shop = client.get("/demo/boutique").text

    assert 'id="secret" type="password"' in shop
    assert "localStorage" not in shop


def test_le_widget_ne_injecte_pas_de_contenu_dynamique_en_html(client):
    widget = client.get("/demo/widget").text

    assert "innerHTML" not in widget
    assert "replaceChildren(statusBadge)" in widget
    assert "window.location.hash" in widget


def test_inscription_demo_utilise_le_contrat_api_et_affiche_la_cle_une_fois(client):
    registration = client.get("/demo/inscription").text

    assert "fetch('/api/v1/auth/register'" in registration
    assert "data.secret_key" in registration
    assert "Compte prêt. Copiez votre clé avant de continuer." in registration


def test_l_accueil_propose_compte_et_connexion_aux_visiteurs(client):
    home = client.get("/").text
    navigation = home.split("<nav>", 1)[1].split("</nav>", 1)[0]

    assert "[hidden] { display: none !important; }" in home
    assert 'href="/demo/inscription"' not in navigation
    assert 'href="/demo/connexion"' not in navigation
    landing = home.split('<section class="home-grid">', 1)[1]
    assert 'data-auth="guest" href="/demo/connexion"' in landing
    assert 'data-auth="guest" href="/demo/inscription"' in home
    assert 'data-auth="signed-in" href="/demo/espace" hidden' in home


def test_la_navigation_s_adapte_a_l_etat_de_session(client):
    home = client.get("/").text
    registration = client.get("/demo/inscription").text
    login = client.get("/demo/connexion").text

    assert "setAuthenticated(Boolean(token))" in home
    assert "fetch('/api/v1/auth/me'" in home
    assert "response.status === 401" in home
    assert "sessionStorage.removeItem('3dp_session')" in home
    assert "['/demo/connexion', '/demo/inscription'].includes(window.location.pathname)" in home
    assert 'id="register-stage" data-auth="guest"' in registration
    assert 'class="auth-layout" data-auth="guest"' in login
    assert 'data-action="logout"' in home
    assert "fetch('/api/v1/auth/logout'" in home


def test_la_connexion_demo_utilise_le_contrat_de_session(client):
    login = client.get("/demo/connexion").text

    assert "fetch('/api/v1/auth/login'" in login
    assert "sessionStorage.setItem('3dp_session', data.access_token)" in login
    assert 'autocomplete="current-password"' in login
    assert 'href="/demo/inscription"' in login


def test_l_espace_marchand_charge_les_donnees_de_session(client):
    workspace = client.get("/demo/espace").text

    assert "sessionStorage.getItem('3dp_session')" in workspace
    assert "'Authorization': 'Bearer ' + sessionToken" in workspace
    assert "api('/api/v1/auth/me')" in workspace
    assert "api('/api/v1/dashboard/transactions')" in workspace
    assert "api('/api/v1/dashboard/webhooks')" in workspace
    assert "api('/api/v1/dashboard/keys')" in workspace
    assert "api('/api/v1/dashboard/settings')" in workspace
    assert "method: 'PATCH'" in workspace
    assert "JSON.stringify({ webhook_url: webhookInput.value.trim() || null })" in workspace
    assert "Notifications désactivées." in workspace
    assert "les adresses locales ou privées sont refusées" in workspace
    assert "sessionStorage.removeItem('3dp_session')" in workspace
    assert "innerHTML" not in workspace
