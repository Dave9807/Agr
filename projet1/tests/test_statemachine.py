"""Machine à statuts (phase 5) : transitions acceptées et transitions rejetées.

Test de validation de la roadmap : `SUCCEEDED -> CREATED` est **rejeté**, et
chaque transition légale de la table est **acceptée**.

Règles d'or couvertes ici :
- refus du client (`DECLINED_BY_CUSTOMER`) ≠ rejet de l'opérateur
  (`REJECTED_BY_OPERATOR`) ;
- un statut d'attente n'est jamais présenté comme un succès ;
- code HTTP ≠ statut métier : ces tests portent sur des **statuts**, pas sur
  les codes de réponse (ceux-ci sont couverts par `test_payments.py`).
"""

import pytest

from app.models import statuses
from app.services import payments

STATUTS_DU_CAHIER = {
    "CREATED",
    "AWAITING_CUSTOMER_ACTION",
    "PROCESSING",
    "SUCCEEDED",
    "DECLINED_BY_CUSTOMER",
    "REJECTED_BY_OPERATOR",
    "EXPIRED",
    "FAILED",
}


def _create(**overrides):
    """Crée une transaction de test (retourne le couple `(transaction, jeton)`)."""
    payload = {
        "account": {"id": 1},
        "amount": 1000,
        "currency": "XOF",
        "operator": "mtn",
        "merchant_reference": None,
        "test_number": "01970000",
    }
    payload.update(overrides)
    return payments.create(**payload)


@pytest.fixture(autouse=True)
def clean_store():
    payments.reset()
    yield
    payments.reset()


# --- La table ---------------------------------------------------------------


def test_la_liste_des_statuts_est_figee():
    assert set(statuses.ALL_STATUSES) == STATUTS_DU_CAHIER
    assert len(statuses.ALL_STATUSES) == 8


def test_une_attente_n_est_jamais_un_succes():
    """Un statut d'attente n'est jamais présenté comme un succès."""
    assert statuses.is_final(statuses.PROCESSING) is False
    assert statuses.is_final(statuses.AWAITING_CUSTOMER_ACTION) is False


def test_les_etats_terminaux_n_ont_aucune_sortie():
    attendus = {
        statuses.SUCCEEDED,
        statuses.DECLINED_BY_CUSTOMER,
        statuses.REJECTED_BY_OPERATOR,
        statuses.EXPIRED,
        statuses.FAILED,
    }

    assert statuses.TERMINAL_STATUSES == frozenset(attendus)
    for statut in attendus:
        assert statuses.ALLOWED_TRANSITIONS[statut] == frozenset()
        assert statuses.is_final(statut) is True


def test_is_final_est_coherent_avec_la_table():
    """Un statut est final s'il n'a aucun successeur — jamais l'inverse."""
    for statut in statuses.ALL_STATUSES:
        assert statuses.is_final(statut) is (not statuses.ALLOWED_TRANSITIONS[statut])


def test_chaque_transition_legale_est_acceptee():
    for courant, cibles in statuses.ALLOWED_TRANSITIONS.items():
        for cible in cibles:
            assert statuses.can_transition(courant, cible) is True


def test_toute_transition_interdite_est_rejetee():
    """Toute transition absente de la table est fausse — y compris la boucle sur soi."""
    for courant in statuses.ALL_STATUSES:
        for cible in statuses.ALL_STATUSES:
            autorisee = cible in statuses.ALLOWED_TRANSITIONS[courant]
            assert statuses.can_transition(courant, cible) is autorisee


def test_succeeded_ne_retourne_jamais_en_created():
    """Le test de validation de la phase 5."""
    assert statuses.can_transition(statuses.SUCCEEDED, statuses.CREATED) is False
    assert statuses.can_transition(statuses.SUCCEEDED, statuses.AWAITING_CUSTOMER_ACTION) is False
    assert statuses.can_transition(statuses.SUCCEEDED, statuses.SUCCEEDED) is False


def test_une_attente_ne_reviens_jamais_en_arriere():
    """`PROCESSING` ne redescend jamais vers l'attente de décision du client."""
    assert statuses.CREATED not in statuses.ALLOWED_TRANSITIONS[statuses.PROCESSING]
    assert (
        statuses.AWAITING_CUSTOMER_ACTION
        not in statuses.ALLOWED_TRANSITIONS[statuses.PROCESSING]
    )


def test_refus_client_et_rejet_operateur_sont_deux_voies_distinctes():
    """Les deux sont atteignables depuis l'attente du client, mais jamais l'une depuis l'autre."""
    attente = statuses.ALLOWED_TRANSITIONS[statuses.AWAITING_CUSTOMER_ACTION]

    assert statuses.DECLINED_BY_CUSTOMER in attente
    assert statuses.REJECTED_BY_OPERATOR in attente

    assert statuses.can_transition(statuses.DECLINED_BY_CUSTOMER, statuses.REJECTED_BY_OPERATOR) is False
    assert statuses.can_transition(statuses.REJECTED_BY_OPERATOR, statuses.DECLINED_BY_CUSTOMER) is False


def test_un_statut_inconnu_provoque_une_erreur():
    """Une faute de frappe ne doit jamais passer pour une transition interdite."""
    with pytest.raises(ValueError):
        statuses.can_transition("PENDING", statuses.SUCCEEDED)

    with pytest.raises(ValueError):
        statuses.can_transition(statuses.SUCCEEDED, "PAYE")


# --- Le service applique la machine -----------------------------------------


def test_le_service_refuse_une_transition_interdite():
    transaction, token = _create()
    payments.decide(transaction["reference"], token, "CONFIRM")
    assert transaction["status"] == statuses.SUCCEEDED

    with pytest.raises(payments.PaymentError) as erreur:
        payments.apply_transition(transaction, statuses.CREATED, None, "retour arrière")

    assert erreur.value.status_code == 409
    assert "Transition interdite" in erreur.value.detail
    assert transaction["status"] == statuses.SUCCEEDED  # l'état n'a pas bougé


def test_le_service_accepte_une_transition_legale():
    transaction, _ = _create()

    payments.apply_transition(transaction, statuses.PROCESSING, None, "en cours")
    assert transaction["status"] == statuses.PROCESSING

    payments.apply_transition(transaction, statuses.SUCCEEDED, None, "payé")
    assert transaction["status"] == statuses.SUCCEEDED
    assert statuses.is_final(transaction["status"]) is True


def test_un_echec_technique_apres_attente_est_legale():
    """`PROCESSING -> FAILED` est autorisé : l'opérateur peut échouer après coup."""
    transaction, _ = _create()

    payments.apply_transition(transaction, statuses.PROCESSING, None, "en cours")
    panne = payments.get_for_merchant(
        {"id": 1}, transaction["reference"]
    )

    payments.apply_transition(
        panne, statuses.FAILED, "OPERATOR_ERROR", "Échec technique."
    )

    assert panne["status"] == statuses.FAILED
    assert panne["reason"] == "OPERATOR_ERROR"
