"""Tests du module d'authentification : inscription, connexion, sessions, clés."""


# --- Inscription --------------------------------------------------------------


def test_register_renvoie_201_avec_les_deux_cles(client):
    body = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Boutique Test",
            "email": "marchand@test.bj",
            "password": "motdepasse123",
        },
    ).json()

    assert body["public_key"].startswith("3dp_pub_")
    assert body["secret_key"].startswith("3dp_sec_")
    assert body["email"] == "marchand@test.bj"


def test_register_sans_champ_obligatoire_renvoie_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Boutique Test", "email": "marchand@test.bj"},
    )

    assert response.status_code == 422


def test_register_email_invalide_renvoie_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Boutique", "email": "pas-un-email", "password": "motdepasse123"},
    )

    assert response.status_code == 422


def test_register_doublon_renvoie_409(registered, client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Autre boutique",
            "email": "marchand@test.bj",
            "password": "autremotdepasse",
        },
    )

    assert response.status_code == 409


def test_register_ne_renvoie_jamais_le_mot_de_passe(registered):
    assert "password" not in registered
    assert "password_hash" not in registered


# --- Connexion ----------------------------------------------------------------


def test_login_valide_renvoie_un_jeton_sess(registered, client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "marchand@test.bj", "password": "motdepasse123"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"].startswith("sess_")


def test_login_mauvais_mot_de_passe_renvoie_401(registered, client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "marchand@test.bj", "password": "fauxmotdepasse"},
    )

    assert response.status_code == 401


def test_login_email_inconnu_renvoie_le_meme_401(registered, client):
    """Même code que le mauvais mot de passe : pas d'énumération de comptes."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inconnu@test.bj", "password": "motdepasse123"},
    )

    assert response.status_code == 401


# --- Session /me --------------------------------------------------------------


def test_me_avec_session_renvoie_le_compte(registered, client):
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "marchand@test.bj", "password": "motdepasse123"},
    ).json()["access_token"]

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "marchand@test.bj"


def test_me_sans_authorization_renvoie_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_avec_clé_secrète_renvoie_401(registered, client):
    """La clé secrète n'ouvre pas les routes de session : mauvais type de jeton."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registered['secret_key']}"},
    )

    assert response.status_code == 401


# --- Déconnexion --------------------------------------------------------------


def logout_and_check(client, token):
    """Helper : déconnexion puis vérification que la session est bien morte."""
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_logout_rend_la_session_inutilisable(registered, client):
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "marchand@test.bj", "password": "motdepasse123"},
    ).json()["access_token"]

    logout_and_check(client, token)


# --- Rotation de clé ----------------------------------------------------------


def test_rotate_renvoie_une_nouvelle_cle_valide(registered, client):
    headers = {"Authorization": f"Bearer {registered['secret_key']}"}

    response = client.post("/api/v1/keys/rotate", headers=headers)

    assert response.status_code == 200
    nouvelle = response.json()["secret_key"]
    assert nouvelle.startswith("3dp_sec_")
    assert nouvelle != registered["secret_key"]


def test_ancienne_cle_rejetee_apres_rotation(registered, client):
    ancienne = registered["secret_key"]
    client.post("/api/v1/keys/rotate", headers={"Authorization": f"Bearer {ancienne}"})

    response = client.post(
        "/api/v1/keys/rotate", headers={"Authorization": f"Bearer {ancienne}"}
    )

    assert response.status_code == 401


def test_rotate_sans_clé_renvoie_401(client):
    response = client.post("/api/v1/keys/rotate")

    assert response.status_code == 401


def test_cle_factice_renvoie_401(client):
    response = client.post(
        "/api/v1/keys/rotate",
        headers={"Authorization": "Bearer 3dp_sec_tresFactice123"},
    )

    assert response.status_code == 401
