# ROADMAP 3DPAY — PLAN DE CONSTRUCTION ET D'IMPLEMENTATION DÉTAILLÉ

> Complément de `CONTEXTE_PROJET.md` (référence fonctionnelle), `analyse.md` (décisions techniques)
> et `AUTH_ET_BENCHMARK.md` (authentification + benchmark agrégateurs).
>
> **Vision :** 3Dpay est une plateforme de paiement mobile money **simulée en libre-service** —
> inscription, clés API par compte, opérateur fictif piloté par un **numéro de test unique**,
> webhook signé, tableau de bord. Aucun argent réel, tout est marqué « SIMULATION ».
>
> **Principe directeur :** une phase = un objectif = un test de validation. On ne passe à la
> suivante que si la précédente est testée et validée.
>
> Stack retenue : **Python + FastAPI** (squelette Laravel écarté).
> Date : octobre 2026 · Statut : validé par l'équipe

---

## Vue d'ensemble

```
Phase 1 ──► 2 ──► 3 ──► 4 ──► 5 ──► 6 ──► 7 ──► 8 ──► 9 ──► 10
Fondations Routes Comptes Cœur   Statuts Fiabilité Webhook Dash/Widget CI/CD Finalisation
+ clés
```

| Phase | Livrable clé | Dépend de |
|---|---|---|
| 1 · Fondations | `/docs` qui s'ouvre | — |
| 2 · Routes publiques | `/operators` qui répond | 1 |
| 3 · **Comptes + clés API** | `register`/`login` + `401`/`403` qui fonctionnent | 2 |
| 4 · Cycle de vie d'une transaction | `201` + consultation + numéros de test | 3 |
| 5 · Machine à statuts | transitions verrouillées | 4 |
| 6 · Persistance + idempotence + logs + rate limiting | données durables | 5 |
| 7 · **Webhook signé** (+ SSRF) | notification + retry | 6 |
| 8 · **Tableau de bord** + widget de démo | scénario e-commerce complet | 7 |
| 9 · Tests, CI/CD, déploiement | PR bloquées si échec | 6 (parallélisable) |
| 10 · Finalisation | démo sans aide | tout |

---

## Phase 1 — Fondations (poser le terrain)

**Objectif :** un squelette propre où tout le monde peut travailler sans se marcher dessus.

**Tâches :**
- [x] Créer l'arborescence : `app/` (routes, models, services, operators, notifications), `tests/`
- [x] Initialiser **Git** (commits présents)
- [x] `requirements.txt`, `.env.example`, `.gitignore` Python
- [x] Remettre les chemins du dépôt d'équerre : les fichiers sont sous `Agr-gateur-de-payement/projet1/`
      alors que Git suit encore `projet1/` (statut : suppressions + dossier non suivi)
- [x] Créer l'environnement virtuel `.venv` et installer les dépendances
- [ ] Configurer la **branche `main` protégée** sur GitHub (PR obligatoire)
- [ ] Base de données **SQLite** (fichier local, zéro installation)

**Test de validation :** `uvicorn app.main:app --reload` → la page `/docs` s'ouvre.

---

## Phase 2 — Les premières routes (publiques)

**Objectif :** comprendre le cycle requête/réponse avec des routes simples, sans risque.

**Tâches :**
- [x] `GET /api/v1/health` → vérifier que l'API répond
- [x] `GET /api/v1/operators` → liste des 3 opérateurs (MTN Mobile Money, Moov Money, Celtiis Cash)
- [x] Codes HTTP corrects : `200`, `404`, `422` (validation Pydantic)
- [x] Premier fichier de tests `pytest`
- [x] *Sur demande de l'équipe :* routes du module d'authentification intégrées à cette étape
      (`register`, `login`, `logout`, `me`, `keys/rotate` — bcrypt, `3dp_pub_`/`3dp_sec_`,
      rotation, 21 tests ✔ à titre indicatif)

**Test de validation :** appeler les 2 routes via `/docs` → JSON conforme ; requête invalide → `422`.
**Validé le 2026-10-28 :** serveur réel testé — `200 /health`, 3 opérateurs, `200 /docs`,
`422` sans `password`, `401` sans clé. Voir `docs/JOURNAL.md` pour le détail.

---

## Phase 3 — Comptes utilisateurs, clés API et authentification 🔐

**Objectif :** le **libre-service** : un développeur s'inscrit, reçoit ses clés, et seul son compte
peut appeler l'API protégée.
*(Rappel §F10 : ne pas confondre l'auth du marchand et celle du client payeur — le client
payeur n'appelle jamais 3DPAY et n'a aucun compte.)*

**Tâches :**
1. [ ] Table `marchants` : `id, name, email (unique), password_hash (bcrypt), public_key,
       api_key_hash (sha256), status, created_at`
2. [ ] `POST /api/v1/auth/register` → inscription (mot de passe **haché**, jamais en clair)
3. [ ] `POST /api/v1/auth/login` → session (cookie sécurisé ou jeton opaque) / `logout`
4. [ ] **Génération de 2 clés** à l'inscription :
   - `3dp_pub_…` : identifiant public du compte (affichable) ;
   - `3dp_sec_…` : aléatoire 32+ caractères, affichée **une seule fois**,
     stockée en **hash SHA-256**, jamais en clair, jamais journalisée ;
   - `POST /api/v1/keys/rotate` → régénère la clé secrète et révoque l'ancienne.
5. [ ] Middleware d'authentification vérifiant `Authorization: Bearer <clé_secrète>`
   - clé absente ou invalide → **`401`**
   - compte suspendu → **`403`**
6. [ ] Séparation des routes : publiques (`/health`, `/operators`, `/auth/*`) vs protégées (`/payments…`)
7. [ ] Rattacher `marchant_id` à chaque transaction, clé et webhook

**Test de validation :** s'inscrire → la clé secrète s'affiche **une fois** ; `POST /payments`
**sans** clé → `401` ; **avec** la clé du compte → la requête passe (la route peut encore renvoyer
`404`, ce qui prouve que l'auth a bien été vérifiée avant le reste) ; un compte ne voit **jamais**
les données d'un autre.

---

## Phase 4 — Le cœur : cycle de vie d'une transaction

**Objectif :** le parcours complet d'un paiement simulé.

**Tâches :**
1. [x] Modèle de transaction : référence unique, montant, devise, référence commande, opérateur, **numéro de test**, statut, horodatages
2. [x] `POST /api/v1/payments` → crée la transaction → **`201 Created`** + référence + statut initial
3. [x] `GET /api/v1/payments/{reference}` → consultation → `200` ou `404` clair
4. [x] `POST /api/v1/payments/{reference}/decision` → le client **confirme ou refuse**
5. [x] Composants opérateurs **séparés** : `mtn.py`, `moov.py`, `celtiis.py`
   - mode **contrôlé** : on force un résultat (succès / refus / attente / erreur) — `forced_outcome`,
     **jamais exposé par HTTP** (outil de test)
   - mode **règles** : résultat déterminé par le **numéro de test**, avec des règles documentées
6. [x] **Numéro de test unique** : un seul numéro fictif, commun aux 3 opérateurs, pilote le scénario
   - tableau des correspondances figé le 2026-10-29
   - numéro inconnu → **refus explicite** (`INVALID_TEST_NUMBER`), jamais un succès inventé
   - le tableau est publié dans `docs/NUMEROS_DE_TEST.md`
   - le choix de l'opérateur (MTN/Moov/Celtiis) reste fait **par le client sur la boutique**

**Décision complémentaire (2026-10-29) :** le **client payeur** n'ayant aucun compte, la route
`/decision` n'exige pas de clé API mais un **`decision_token` à usage unique**, remis à la création
et stocké haché — voir `CONTEXTE_PROJET.md` §F13 bis.

**Test de validation :** créer → consulter → confirmer → consulter → le statut a bien évolué ;
même scénario avec MTN puis Moov → **mêmes résultats** (même numéro de test) ;
référence inconnue → `404`.
**Validé le 2026-10-29 :** 74 tests pytest ✔ · serveur réel : `201` + `CREATED`, décision →
`200 PROCESSING` (numéro d'attente), rejeu → `409`, sans clé → `401`, référence inconnue → `404`.
Voir `docs/JOURNAL.md`.

---

## Phase 5 — La machine à statuts (intégrité)

**Objectif :** empêcher toute transition incohérente.

**Tâches :**
- [x] Figer la liste finale des statuts : `CREATED`, `AWAITING_CUSTOMER_ACTION`, `PROCESSING`,
  `SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED`
- [x] Table des **transitions autorisées** → toute transition interdite = rejetée
- [x] Règles d'or :
  - refus du client **≠** rejet de l'opérateur
  - un statut d'attente n'est **jamais** présenté comme un succès
- [x] Séparation stricte **code HTTP** (201, 404) / **statut métier** (`PENDING`, `SUCCEEDED`…)
- [x] Table d'équivalence avec FedaPay (voir `AUTH_ET_BENCHMARK.md` §8.4)

**Test de validation :** tenter `SUCCEEDED → CREATED` → rejeté ; chaque transition légale → acceptée.
**Validé le 2026-10-29 :** 89 tests pytest ✔ (13 nouveaux `tests/test_statemachine.py` + 2 tests de renfort dans `tests/test_payments.py`) —
`SUCCEEDED → CREATED` rejeté, les 8 statuts de la liste sont exactement ceux du cahier des charges,
et chaque transition de `ALLOWED_TRANSITIONS` est acceptée. Voir `docs/JOURNAL.md`.

---

## Phase 6 — Persistance + fiabilité + sécurité

**Objectif :** que les données survivent au redémarrage, et que l'API résiste aux erreurs réelles.

**Tâches :**
1. [ ] **Persistance** : SQLAlchemy + Alembic (remplace la liste en mémoire)
2. [ ] **Idempotence** : en-tête `Idempotency-Key` **scopé par marchand**
   → une requête rejouée = **une seule transaction**
3. [ ] **Journalisation** : événements importants avec la référence (aucun secret dans les logs)
4. [ ] **Validation** stricte de toutes les entrées (Pydantic)
5. [ ] **Limitation du débit** (rate limiting) sur `/auth/*` et `/payments` → réponse **`429`**
       explicite ; seuils réglables via `.env`

**Test de validation :** créer une transaction → **redémarrer le serveur** → elle existe toujours ;
rejouer la même requête avec la même `Idempotency-Key` → toujours 1 seule transaction ;
bourrage de requêtes sur `/auth/login` → `429` après le seuil.

---

## Phase 7 — Webhook signé (l'écart n°1 vs Kkiapay/FedaPay)

**Objectif :** notifier le marchand comme le font les vrais agrégateurs.

**Tâches :**
- [ ] `POST` vers l'URL déclarée par le marchand
- [ ] Payload : `{event, reference, status, amount, occurred_at}` avec
  `event ∈ {transaction.succeeded, transaction.declined, transaction.failed}`
- [ ] En-tête **`X-3DPay-Signature` (HMAC)** pour prouver l'origine
- [ ] Réponse attendue : **HTTP 2xx** → sinon **retry simulé ×5** visible dans les logs
- [ ] **Journal des webhooks** persisté (URL, statut HTTP, tentatives, réponse) → affiché au tableau de bord
- [ ] **Protection SSRF** : refuser toute URL de webhook pointant vers une adresse interne/privée
      (`localhost`, `127.*`, `10.*`, `172.16-31.*`, `192.168.*`, `169.254.*`, `::1`) → `422`
- [ ] **Repli toujours disponible** : `GET /payments/{reference}`

**Test de validation :** marchand répondant `200` → 1 seul envoi ; marchand muet → 5 tentatives
journalisées ; URL `http://127.0.0.1:9999/hook` → **rejetée** ; le `GET` de consultation reste
fonctionnel.

---

## Phase 8 — Tableau de bord + widget de démo + scénario e-commerce

**Objectif :** rendre l'usage et la démo visuels et proches du réel.

**Tâches — tableau de bord (MVP) :**
- [ ] Accès après `login` (session), isolation stricte par compte
- [ ] Liste et détail des **transactions de l'utilisateur**
- [ ] **Journal des webhooks** (tentatives, codes HTTP, payload)
- [ ] **Clés** : affichage de la clé publique, régénération de la secrète (avertissement : affichée une seule fois)
- [ ] **Réglages** : URL de webhook, informations du compte
- [ ] Mention **« SIMULATION »** visible partout

**Tâches — widget et scénario :**
- [ ] Page HTML minimale simulant le widget de paiement (choix opérateur → confirmation/refus)
- [ ] Parcours complet : *boutique fictive → choix opérateur → widget → webhook → consultation → succès*
- [ ] Page documentant les **numéros de test** et leurs scénarios
- [ ] Vocabulaire aligné : événements `transaction.*`, table d'équivalence des statuts

**Test de validation :** se connecter au tableau de bord → voir ses transactions, son journal de
webhooks et ses clés, **rien d'autre** ; rejouer le scénario de bout en bout devant quelqu'un, sans casser.

---

## Phase 9 — Tests, CI et déploiement

**Objectif :** que rien ne casse et que tout se déploie automatiquement.

**Tâches :**
- [ ] Suite **pytest** complète : succès, refus, attente, erreurs, auth (`401`/`403`), idempotence, webhook
- [ ] **GitHub Actions** : `ruff check` + `pytest` à chaque push/PR → PR bloquée si échec
- [ ] Déploiement **staging** automatique sur `main`, promotion manuelle en **production** (Render + Neon, gratuits)
- [ ] Fichiers `.env` distincts par environnement (secrets jamais dans Git)

**Test de validation :** pousser un commit avec un test volontairement en échec → la PR est **bloquée**
par la CI.

---

## Phase 10 — Finalisation & démonstration 🎯

**Objectif :** prouver que le MVP est complet.

**Tâches :**
- [ ] Vérifier **chaque critère du §10** de `CONTEXTE_PROJET.md` (liste de contrôle)
- [ ] Documentation finale : routes, exemples JSON, contrats d'auth et de webhook à jour
- [ ] **Démonstration** : parcours complet via `/docs` + widget, en reliant chaque brique au réel
  (*« chez FedaPay c'est ceci, ici c'est sa version simulée »*)
- [ ] Mise à jour de `analyse.md` et `AUTH_ET_BENCHMARK.md` avec les décisions réellement prises
- [ ] Traiter les 7 points ⏳ restants (`AUTH_ET_BENCHMARK.md` §10)

**Test final :** un nouveau membre clone le dépôt, suit le README, lance l'API et reproduit la
démonstration **sans aide**.

---

## Notes de travail

- **L'authentification (phase 3) vient tôt** : il faut protéger `POST /payments` dès sa création,
  mais après les routes publiques pour ne pas mélanger les apprentissages. Elle inclut désormais
  l'**inscription/connexion** et la génération des **2 clés** (vision libre-service).
- **Le tableau de bord dépend du webhook (phase 7)** : son journal affiche les envois produits
  par cette phase — d'où son positionnement en phase 8.
- Les phases **7, 8 et 9** peuvent partiellement chevaucher si l'on travaille à deux
  (un sur le webhook, l'autre sur la CI).
- Les points ⏳ non tranchés (statuts finaux, valeurs des **numéros de test**, en-tête `Bearer`,
  seuils de rate limiting, choix de la session) sont listés dans `AUTH_ET_BENCHMARK.md` §10
  et `CONTEXTE_PROJET.md` §12.
- **Règle permanente :** tout est marqué « SIMULATION », aucune donnée bancaire réelle,
  aucun secret en clair dans le code, les réponses ou les logs.

*Document à mettre à jour à chaque changement de plan.*
