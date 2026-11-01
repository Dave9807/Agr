# NUMÉROS DE TEST — 3DPAY (SIMULATION)

> **Aucun paiement réel.** Aucun numéro de téléphone réel n'est demandé, stocké
> ou appelé. Les numéros ci-dessous sont des **numéros fictifs** qui pilotent le
> scénario de l'opérateur simulé.

---

## 1. Un seul numéro fictif pour les trois opérateurs

Le **numéro de test** est transmis par le marchand dans le corps de
`POST /api/v1/payments` (champ `test_number`, exactement **8 chiffres**).

Le scénario dépend **uniquement de ce numéro** : MTN, Moov et Celtiis renvoient
donc le **même résultat** pour un même numéro. C'est ce qui rend les
démonstrations reproductibles.

| Numéro de test | Scénario simulé | Statut métier enregistré | `reason` |
|---|---|---|---|
| `01970000` | succès | `SUCCEEDED` | — |
| `01970001` | refus de l'opérateur | `REJECTED_BY_OPERATOR` | `OPERATOR_DECLINED` |
| `01970002` | solde insuffisant | `REJECTED_BY_OPERATOR` | `INSUFFICIENT_FUNDS` |
| `01970003` | attente (résultat non définitif) | `PROCESSING` | — |
| tout autre numéro à 8 chiffres | numéro inconnu | `REJECTED_BY_OPERATOR` | `INVALID_TEST_NUMBER` |

### Numéro inconnu : refus explicite, jamais un succès

Un numéro absent du tableau ne produit **pas** un succès par défaut : inventer un
succès masquerait une erreur d'intégration. La transaction est rejetée avec
`reason = INVALID_TEST_NUMBER` et un message qui renvoie vers cette page.

---

## 2. Ce que le numéro de test ne décide pas

Le numéro de test n'intervient qu'**après** la décision du client :

1. `POST /api/v1/payments` → `201` + référence, statut `CREATED` ;
2. le client **confirme** ou **refuse** via le `decision_token` ;
3. **refus du client** → `DECLINED_BY_CUSTOMER`, quel que soit le numéro de test,
   et **aucun** appel à l'opérateur ;
4. **confirmation** → l'opérateur simulé applique les règles du tableau.

Un refus du client n'est donc jamais confondu avec un rejet de l'opérateur.

---

## 3. Statuts et codes HTTP

Le code HTTP décrit la requête ; le statut métier décrit le paiement.

| Statut | Définitif (`is_final`) | Signification |
|---|---|---|
| `CREATED` | non | transaction créée, le client n'a pas encore décidé |
| `AWAITING_CUSTOMER_ACTION` | non | réservé au widget (phase 8) : le client a ouvert la page de paiement |
| `PROCESSING` | non | résultat non définitif — **ce n'est pas un succès** |
| `SUCCEEDED` | oui | paiement simulé réussi |
| `DECLINED_BY_CUSTOMER` | oui | le client a refusé |
| `REJECTED_BY_OPERATOR` | oui | l'opérateur simulé a rejeté |
| `EXPIRED` | oui | demande expirée (pas encore déclenchée automatiquement) |
| `FAILED` | oui | échec technique |

> `PROCESSING` est le nom API de ce que les documents de conception appellent
> `PENDING` : un seul statut d'attente, pour éviter deux noms pour la même chose.

---

## 4. Exemple complet (curl)

```bash
# 1. Créer — clé secrète du marchand (3dp_sec_…)
curl -X POST http://127.0.0.1:8000/api/v1/payments \
  -H "Authorization: Bearer 3dp_sec_…" \
  -H "Content-Type: application/json" \
  -d '{"amount":5000,"operator":"mtn","merchant_reference":"CMD-001","test_number":"01970000"}'
# -> 201 {"reference":"3dp_tx_…","status":"CREATED","is_final":false,…,
#         "decision_token":"3dp_dec_…"}

# 2. Le client confirme (le jeton remplace un compte client, qu'il n'a pas)
curl -X POST http://127.0.0.1:8000/api/v1/payments/3dp_tx_…/decision \
  -H "Content-Type: application/json" \
  -d '{"decision":"CONFIRM","decision_token":"3dp_dec_…"}'
# -> 200 {"status":"SUCCEEDED","is_final":true,…}

# 3. Le marchand consulte (repli toujours disponible)
curl http://127.0.0.1:8000/api/v1/payments/3dp_tx_… \
  -H "Authorization: Bearer 3dp_sec_…"
```

Le `decision_token` est **à usage unique** et n'est affiché qu'à la création :
il n'est jamais renvoyé par la consultation, et une seconde décision sur la même
transaction renvoie `409`.

---

## 5. Mode contrôlé (outil de test, jamais public)

Les tests internes peuvent forcer un résultat, y compris un **échec technique**
(`FAILED`) qu'aucun numéro de test ne déclenche :

```python
from app.operators import mtn
mtn.process("01979999", forced_outcome="INSUFFICIENT_FUNDS")  # mode contrôlé
```

`forced_outcome` accepte `SUCCESS`, `DECLINED`, `INSUFFICIENT_FUNDS`, `PENDING`,
`FAILED`. Aucune route HTTP ne l'expose : un mécanisme de forçage ne doit jamais
être utilisable dans une intégration réelle.

---

*Page à maintenir : toute modification du tableau (`app/operators/base.py`) doit
être répercutée ici.*
