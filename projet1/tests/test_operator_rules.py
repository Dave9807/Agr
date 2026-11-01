"""Tests des règles de l'opérateur simulé et de son mode contrôlé.

Ces tests n'appellent pas HTTP : le mode contrôlé (`forced_outcome`) est un
outil interne de test, jamais exposé par une route publique.
"""

import pytest

from app.operators import celtiis, get_operator, moov, mtn
from app.operators.base import FORCED_OUTCOMES, INVALID_TEST_NUMBER, TEST_SCENARIOS
from app.services import payments

MODULES = (mtn, moov, celtiis)


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("test_number", sorted(TEST_SCENARIOS))
def test_les_trois_operateurs_appliquent_les_memes_regles(module, test_number):
    attendu = mtn.process(test_number)

    resultat = module.process(test_number)

    assert resultat.outcome == attendu.outcome
    assert resultat.reason == attendu.reason


@pytest.mark.parametrize("module", MODULES)
def test_un_numero_inconnu_ne_produit_jamais_un_succes(module):
    resultat = module.process("01979999")

    assert resultat.outcome == INVALID_TEST_NUMBER
    assert resultat.reason == "INVALID_TEST_NUMBER"


@pytest.mark.parametrize("outcome", sorted(FORCED_OUTCOMES))
def test_le_mode_controle_force_le_resultat(outcome):
    resultat = mtn.process("01979999", forced_outcome=outcome)

    assert resultat.outcome == outcome
    assert "mode contrôlé" in resultat.message


def test_un_resultat_force_inconnu_leve_une_erreur():
    with pytest.raises(ValueError):
        mtn.process("01970000", forced_outcome="PEUT_ETRE")


def test_un_operateur_inconnu_leve_une_erreur():
    with pytest.raises(ValueError):
        get_operator("orange")


def test_le_service_traduit_un_echec_technique_en_failed():
    payments.reset()
    transaction, token = payments.create(
        account={"id": 1},
        amount=1000,
        currency="XOF",
        operator="mtn",
        merchant_reference=None,
        test_number="01970000",
    )

    resultat = payments.decide(
        transaction["reference"],
        token,
        "CONFIRM",
        forced_outcome="FAILED",
    )

    assert resultat["status"] == "FAILED"
    assert resultat["reason"] == "OPERATOR_ERROR"
    payments.reset()
