# JOURNAL DE SUIVI — 3DPAY

> Trace chronologique de l'avancement. Une entrée par étape réalisée,
> avec ce qui a été fait, les tests exécutés et leurs résultats réels.

---

## 2026-10-28 — Étape 2 : routes publiques + module d'authentification

### Ce qui a été fait

**Étape 1 — dépendances (terminée) :**
- `.venv` créé (Python 3.13.16), dépendances installées : `fastapi 0.162.0`,
  `uvicorn[standard]`, `pytest`, `httpx`, `bcrypt`
- `.env` créé à partir de `.env.example` (ignoré par Git)
- `requirements.txt` complété avec la liste exacte

**Étape 2 — implementée (fichiers créés) :**

| Fichier | Rôle |
|---|---|
| `app/models/schemas.py` | Modèles Pydantic : validation des entrées (`422` automatique) |
| `app/operators/registry.py` | Catalogue des 3 opérateurs simulés |
| `app/services/auth.py` | Logique métier : inscription, sessions, clés, rotation |
| `app/deps.py` | Contrôle de `Authorization: Bearer <jeton>` |
| `app/routes/health.py` | `GET /api/v1/health` |
| `app/routes/operators.py` | `GET /api/v1/operators` |
| `app/routes/auth.py` | `register` `login` `logout` `me` + `keys/rotate` |
| `app/main.py` | Branchement des routeurs + gestionnaire d'`AuthError` |
| `tests/conftest.py` + 3 fichiers de tests | pytest |

### Contrat des routes livrées

| Route | Accès | Réponses |
|---|---|---|
| `GET /api/v1/health` | publique | `200` |
| `GET /api/v1/operators` | publique | `200` |
| `POST /api/v1/auth/register` | publique | `201` · `409` doublon · `422` |
| `POST /api/v1/auth/login` | publique | `200` jeton `sess_…` · `401` |
| `POST /api/v1/auth/logout` | session | `200` · `401` |
| `GET /api/v1/auth/me` | session | `200` · `401` |
| `POST /api/v1/keys/rotate` | clé secrète | `200` nouvelle `3dp_sec_…` · `401` |

### Règles de sécurité appliquées

- Le mot de passe est **haché bcrypt** — jamais stocké ni retourné en clair.
- La clé secrète `3dp_sec_…` est affichée **une seule fois**, stockée en hash SHA-256.
- Message de connexion identique selon si l'e-mail existe ou non → pas d'énumération de comptes.
- L'ancienne clé est **révoquée immédiatement** après rotation.
- Le jeton de session expire après 24 h.

### Tests réels exécutés

```
.\.venv\Scripts\python.exe -m pytest -q   → 21 passed in 11 s
Serveur réel (uvicorn, port 8000) :
  GET /api/v1/health     → 200 {"status":"ok","mode":"SIMULATION"}
  GET /api/v1/operators  → 200, 3 opérateurs (mtn, moov, celtiis)
  GET /docs              → HTTP 200
  POST /auth/register sans password          → 422 (validation)
  POST /keys/rotate sans cle Authorization   → 401 (authentification)
```

> Où l'a-t-on retrouvé : stockage en mémoire → **toute inscription est perdue au
> redémarrage**. Comportement attendu de l'étape 2 ; résolu à l'étape 6 (gestion de la persistance).

### Tester manuellement sur Swagger UI

1. `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
2. Ouvrir `http://127.0.0.1:8000/docs`
3. `POST /auth/register` → copier la `secret_key` du corps (1 seule fois !)
4. `POST /auth/login` → copier son `access_token` (jeton `sess_…`)
5. Cliquez sur le **cadenas 🔓 Authorize** (haut de page) → collez le jeton **sans** écrire
   `Bearer ` (Swagger l'ajoute seul) → `GET /auth/me` → `200`
6. `POST /keys/rotate` → même fenêtre Authorize mais avec la `3dp_sec_…` → `200`
   (l'ancienne clé devient ensuite `401`)

---

## 2026-10-29 — Correctif : bouton Authorize (HTTPBearer) sur /docs

### Anomalie constatée

Symptôme rapporté par le développeur : `GET /auth/me` renvoyait systématiquement
`401 {"detail": "En-tête Authorization manquant."}` alors que le jeton était bien
saisi dans le champ « try it out » de Swagger.

### Cause racine (démontrée, pas supposée)

- Rejeu identique en dehors de Swagger : **sans** en-tête → `401 manquant` ;
  **avec** l'en-tête → `200`. Le code applicatif était donc correct.
- Inspect OpenAPI : `Authorization` était déclaré comme **paramètre brut**
  (`{"name": "authorization", "in": "header"}`), et non comme schéma de sécurité.
- Swagger UI **ignore** les valeurs saisies dans un champ de paramètre nommé
  `Authorization` (en-tête réservé à son bouton Authorize) → l'en-header n'était
  **jamais transmis** au serveur → d'où le `401 "manquant"`.

### Correctif appliqué (`app/deps.py`)

- Remplacement de `Header(default=None)` par **`fastapi.security.HTTPBearer(auto_error=False)`**
  via `Security()` dans `current_session_token` et `require_api_key`.
- Le document OpenAPI déclare désormais `securitySchemes.HTTPBearer`
  (`type: http`, `scheme: bearer`) → **bouton 🔓 Authorize** sur `/docs`.
- Messages d'erreur conservés et affinés : `401` en-tête absent / format incorrect /
  mauvais type de jeton, `403` compte suspendu.
- L'ancien faux paramètre a disparu de la spec (`parametres restants -> aucun`).

### Validation réelle

```
pytest -q                      -> 21 passed (aucune régression)
Serveur réel (port 8000) :
  sans en-tête                  -> HTTP 401
  Bearer sess_ valide           -> HTTP 200 (demo@b.bj)
  scheme « Basic » (incorrect)  -> HTTP 401
  /docs                         -> HTTP 200
```

### Prochaine anomalie connue (non bloquante)

Le token reste **en mémoire** : tout redémarrage d'`uvicorn` (y compris
`--reload` après modification d'un fichier) invalide les sessions →
`401 "Session invalide ou expirée."` → il suffit de refaire `login`.
Réellement résolu à l'étape 6 (persistance).

---

## 2026-10-29 — Phase 4 : cycle de vie d'une transaction

### Ce qui a été fait

| Fichier | Rôle |
|---|---|
| `app/models/statuses.py` | les 8 statuts métier, `is_final()`, statuts encore actionnables |
| `app/operators/base.py` | règles de l'opérateur simulé : tableau des numéros de test + mode contrôlé |
| `app/operators/mtn.py` · `moov.py` · `celtiis.py` | un module par opérateur, mêmes règles |
| `app/operators/__init__.py` | `get_operator()` : sélection du module selon l'opérateur |
| `app/services/payments.py` | transactions en mémoire, jeton de décision haché, traduction résultat → statut |
| `app/routes/payments.py` | `POST /payments`, `GET /payments/{reference}`, `POST /payments/{reference}/decision` |
| `app/models/schemas.py` | `PaymentIn`, `PaymentOut`, `PaymentCreatedOut`, `DecisionIn` |
| `app/main.py` | routeur des paiements + gestionnaire de `PaymentError` |
| `tests/test_payments.py` | 30 tests HTTP du cycle de vie |
| `tests/test_operator_rules.py` | règles des 3 opérateurs + mode contrôlé |
| `docs/NUMEROS_DE_TEST.md` | page publiée des numéros de test |

### Contrat des routes livrées

| Route | Accès | Réponses |
|---|---|---|
| `POST /api/v1/payments` | clé secrète `3dp_sec_…` | `201` + référence + `CREATED` + `decision_token` · `401` · `422` |
| `GET /api/v1/payments/{reference}` | clé secrète `3dp_sec_…` | `200` · `404` · `401` |
| `POST /api/v1/payments/{reference}/decision` | `decision_token` | `200` · `401` jeton invalide · `404` · `409` déjà traitée · `422` |

### Décisions prises (et pourquoi)

- **Le client payeur n'a aucun compte** (F11) : la décision est authentifiée par un
  `decision_token` à usage unique, affiché à la création et stocké en SHA-256. Sans lui,
  n'importe qui pourrait confirmer ou refuser le paiement d'un autre en devinant une référence.
- **Isolation par compte** : une référence appartenant à un autre marchand renvoie `404`, jamais `403`
  (ne pas révéler l'existence de la transaction).
- **Refus client ≠ rejet opérateur** : `DECLINE` n'appelle **jamais** l'opérateur ; un numéro de test
  de succès ne change rien au refus.
- **Résultat opérateur synchrone** : la décision interroge l'opérateur simulé dans la même requête.
  Pas de tâche de fond : les tests restent déterministes. Le statut d'attente (`PROCESSING`) reste
  donc non définitif, ce qui rend la consultation indispensable.
- **`PROCESSING`** est le nom API du `PENDING` des documents : un seul statut d'attente.
- **Numéro inconnu = refus explicite** (`INVALID_TEST_NUMBER`) : un succès inventé masquerait une
  erreur d'intégration.
- **Mode contrôlé** (`forced_outcome`, avec `FAILED` pour l'erreur technique) : accessible uniquement
  depuis le code et les tests, **aucune route HTTP** ne l'expose (F13).

### Tests réels exécutés

```
.\.venv\Scripts\python.exe -m pytest -q   → 74 passed in 16.9 s   (21 avant la phase 4)

Serveur réel (uvicorn, port 8011) :
  /docs                                    → 200
  POST /payments (moov, 01970003)          → 201 {"status":"CREATED","is_final":false}
  GET  /payments/{ref}                     → 200 {"status":"CREATED"}
  POST /payments/{ref}/decision CONFIRM    → 200 {"status":"PROCESSING","is_final":false}
  même décision rejouée                    → 409
  GET  /payments/{ref} sans clé            → 401
  GET  /payments/3dp_tx_zzz                → 404
```

> Limite assumée : les transactions vivent en mémoire → tout redémarrage (y compris `--reload`)
> efface comptes, sessions et paiements. Résolu en phase 6 (persistance).
> Limite assumée : un `PROCESSING` ne se résout pas encore tout seul (pas de reprise ni
> d'expiration) — règles prévues en phase 5/6.

### Tester manuellement sur Swagger UI

1. `POST /auth/register` → copier la `secret_key`
2. 🔓 **Authorize** → coller la `3dp_sec_…`
3. `POST /payments` avec `test_number: "01970000"` → `201`, copier `reference` + `decision_token`
4. `GET /payments/{reference}` → `200 CREATED`
5. `POST /payments/{reference}/decision` (route publique) avec ce `decision_token` → `200 SUCCEEDED`
6. `GET /payments/{reference}` → `SUCCEEDED`, `is_final: true`

---

### Prochaine étape

**Phase 5** — machine à statuts : table des transitions autorisées, rejet de toute transition
incohérente (ex. `SUCCEEDED → CREATED`).

---

## 2026-10-29 — Phase 5 : la machine à statuts

### Ce qui a été fait

| Fichier | Rôle |
|---|---|
| `app/models/statuses.py` | + `ALLOWED_TRANSITIONS` (table des seuls passages autorisés), `can_transition()`, `TERMINAL_STATUSES` ; `FINAL_STATUSES` en découle (une seule source de vérité) |
| `app/services/payments.py` | `apply_transition()` : **point de contrôle unique** — toute transition absente de la table → `409 Transition interdite` |
| `tests/test_statemachine.py` | 13 tests : chaque transition légale acceptée, chaque transition hors table rejetée |

### La table (8 statuts, 3 non terminaux)

| Depuis | Vers |
|---|---|
| `CREATED` | `AWAITING_CUSTOMER_ACTION`, `PROCESSING`, `SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED` |
| `AWAITING_CUSTOMER_ACTION` | `PROCESSING`, `SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED` |
| `PROCESSING` | `SUCCEEDED`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED` |
| `SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED` | **rien** (états terminaux) |

### Règles d'or encodées (pas seulement documentées)

- **Un état terminal n'a aucune sortie** : `SUCCEEDED → CREATED` est faux dans la table **et**
  rejeté par le service (`409`), quel que soit le chemin qui tenterait de le produire.
- **Refus client ≠ rejet opérateur** : `DECLINED_BY_CUSTOMER` et `REJECTED_BY_OPERATOR` sont deux
  états distincts, tous deux atteignables depuis l'attente du client, mais **jamais l'un depuis
  l'autre**.
- **Un statut d'attente n'est jamais un succès** : `is_final(PROCESSING)` = `False`, et
  `PROCESSING` ne redescend jamais vers `CREATED`/`AWAITING_CUSTOMER_ACTION`.
- **Statut inconnu = `ValueError`**, pas « transition interdite » : une faute de frappe dans un
  statut ne doit jamais passer pour un refus de la machine.

### Test de validation de la roadmap

`succeeded → created` rejeté ✔ · chaque transition légale acceptée ✔ · **89 tests** au total
(74 avant, 13 nouveaux `test_statemachine` + 2 tests de renfort ajoutés à `test_payments.py` :
`201 ≠ succès` et `champ obligatoire manquant → 422`), suite entière verte.

### Ce que la machine ne fait pas encore (volontairement)

- aucune **expiration automatique** (`EXPIRED` n'est jamais produit par le code, seulement
  atteignable) → phase 6 (tâche de fond) ;
- aucune **reprise** d'une transaction restée `PROCESSING` → elle y restera jusqu'à la phase 6/7.

### Table d'équivalence FedaPay

Complétée dans `AUTH_ET_BENCHMARK.md` §8.4 : `AWAITING_CUSTOMER_ACTION` et `PROCESSING` sont tous
les deux `pending` côté FedaPay — notre API distingue ce que FedaPay regroupe.

---

## 2026-11-01 — Phases 6 à 10 : persistance, webhooks, tableau de bord, CI/CD

### 0. Contexte d'intégration (important)

Les phases 4 et 5 ont été livrées en parallèle par un autre membre. Leur contrat
est **conservé tel quel** — je ne l'ai pas réécrit :

- `POST /payments` → `201` + `decision_token` à usage unique ;
- la décision du client est authentifiée par ce jeton (`CONFIRM` / `DECLINE`),
  le client payeur n'a **pas** de compte ;
- champs `merchant_reference`, `test_number` (8 chiffres), `is_final` ;
- numéros `01970000` → succès, `01970001` → refus, `01970002` → solde
  insuffisant, `01970003` → attente, tout autre → `INVALID_TEST_NUMBER` ;
- machine à statuts dans `app/models/statuses.py` (`ALLOWED_TRANSITIONS`).

Tout le travail ci-dessous est donc **ajouté par-dessus**, sans casser les
89 tests existants (comptes, paiements, machine à statuts).

### 1. Phase 6 — persistance et fiabilité

| Fichier | Rôle |
|---|---|
| `app/config.py` | toutes les variables lues depuis `.env` (aucun secret en dur) |
| `app/db.py` | moteur SQLAlchemy 2.x, `get_db`, `init_db`, `reset_db` |
| `app/models/entities.py` | tables `merchants`, `transactions`, `webhook_deliveries`, `idempotency_records` |
| `app/errors.py` | `AppError` + `AuthError`, `PaymentError`, `RateLimitError`, `WebhookError`, `IdempotencyError` |
| `app/services/auth.py` | comptes **persistés** (bcrypt + SHA-256), sessions en mémoire |
| `app/services/payments.py` | transactions **persistées**, expiration paresseuse, déclenchement des webhooks |
| `app/services/idempotency.py` | `Idempotency-Key` scopée par marchand |
| `app/services/ratelimit.py` | fenêtre glissante → `429` + `Retry-After` |
| `alembic/` | migration initiale `344f3f865cf1_schema_initial.py` |

**Logique de persistance retenue (write-through).** La machine à statuts et les
tests manipulent la transaction comme un dictionnaire vivant (`apply_transition`
modifie l'objet en place). Plutôt que de casser ce contrat, le service garde ce
dict en mémoire et **écrit chaque changement en base** (`_save`) ; après un
redémarrage, `_load` recharge la ligne SQLAlchemy et reconstruit le dict. La base
reste la source de vérité, l'objet Python n'est qu'un cache d'écriture.

**Effets concrets :** comptes, transactions, clés et journal des webhooks
survivent à un redémarrage. Seules les **sessions** restent volatiles (jeton
`sess_…` de navigateur) : un redémarrage déconnecte le tableau de bord, ce qui est
le comportement attendu d'une session.

**Idempotence.** `Idempotency-Key` (en-tête), empreinte SHA-256 canonique du
corps, unicité `(merchant_id, key)`. Rejeu identique → **même référence** ; corps
différent → `409`. Un rejeu réémet un `decision_token` (l'ancien est invalidé) :
la transaction n'est jamais dupliquée, et le client garde un jeton utilisable.

**Expiration.** `EXPIRED` n'était jamais produit (limite notée en phase 5).
Il l'est désormais de façon **paresseuse** : à la lecture/décision, une
transaction encore `CREATED`/`AWAITING_CUSTOMER_ACTION` dont le délai
`TRANSACTION_TTL_MINUTES` est dépassé passe en `EXPIRED`.

**Rate limiting.** Appliqué à `POST /auth/register`, `POST /auth/login` et aux
trois routes `/payments`. Implémentation maison (fenêtre glissante, mémoire) au
lieu de `slowapi` : zéro dépendance supplémentaire, seuils pilotés par `.env`,
réponse `429` homogène avec un en-tête `Retry-After`.

**Journalisation.** `logging` standard, une ligne par transition avec la
référence (`transaction 3dp_tx_… : CREATED → PROCESSING`), plus les échecs de
webhook. Aucun secret, aucun jeton, aucun mot de passe journalisé.

**Erreurs unifiées.** Un seul gestionnaire (`AppError`) dans `main.py` :
`401` (jeton), `403` (suspendu), `404` (inconnu), `409` (transition/idempotence),
`422` (validation/SSRF), `429` (débit). Le code HTTP reste distinct du statut métier.

### 2. Phase 7 — webhook signé, retry et anti-SSRF

`app/services/webhooks.py` :

- payload `{event, reference, status, amount, occurred_at}` ;
- en-tête **`X-3DPay-Signature`** = `sha256=<HMAC-SHA256(body)>` avec
  `WEBHOOK_SECRET` (comparaison à temps constant pour la vérification) ;
- attente d'un **2xx**, sinon **retry ×5** (nombre via `WEBHOOK_MAX_ATTEMPTS`) ;
- **journal** persistant : URL, nombre de tentatives, dernier code HTTP, corps de
  réponse, état `delivered` / `failed` ;
- **protection SSRF** : refus des schémas non `http(s)` et de toute URL dont
  l'hôte résout vers `127.*`, `10.*`, `172.16-31.*`, `192.168.*`, `169.254.*`,
  `::1`, `localhost`, etc. → `422` ;
- le `GET /payments/{reference}` reste le **repli** si le webhook échoue.

Déclenchement uniquement sur statut terminal (`SUCCEEDED` → `transaction.succeeded`,
`DECLINED_BY_CUSTOMER` → `transaction.declined`, les autres → `transaction.failed`).
Un échec d'envoi **ne doit jamais** faire échouer la réponse API (try/except + log).

### 3. Phase 8 — tableau de bord et pages de démonstration

- `app/routes/dashboard.py` (session) : `transactions`, `transactions/{ref}`,
  `webhooks`, `settings` (GET/PATCH, URL validée anti-SSRF), `keys`, `keys/rotate`.
  Isolation stricte : une référence d'un autre compte renvoie `404`.
- `app/routes/pages.py` : `/`, `/demo/boutique`, `/demo/widget`,
  `/demo/numeros-de-test` (HTML autonome, aucun framework, mention « SIMULATION »).
- Parcours démontrable : boutique (clé secrète) → création `201 CREATED` →
  widget (`decision_token`) → `SUCCEEDED`/`DECLINED` → webhook → consultation.

### 4. Phase 9 — tests, CI et déploiement

| Fichier | Contenu |
|---|---|
| `tests/test_persistence.py` | survie aux redémarrages (compte, transaction, statut, clé) |
| `tests/test_idempotency.py` | rejeu, `409` sur corps différent, isolation par marchand |
| `tests/test_webhooks.py` | signature, 2xx → 1 envoi, muet → 5 tentatives, SSRF (6 cas) |
| `tests/test_ratelimit.py` | `429` + `Retry-After` sur auth et paiements |
| `tests/test_dashboard.py` | session exigée, isolation, clés, réglages |
| `tests/test_pages.py` | pages `200`, scénarios affichés, liens boutique/widget |
| `.github/workflows/ci.yml` | `ruff check` puis `pytest` à chaque push/PR |
| `render.yaml` | blueprint Render (free) + secrets `sync: false` |
| `alembic/` | migrations ; `alembic upgrade head` vérifié |

### 5. Décisions actées dans cette étape

| Sujet | Décision |
|---|---|
| Contrat API des phases 4/5 | **conservé** (aucune rupture pour l'équipe) |
| Stockage | SQLite (dev/tests) / PostgreSQL (prod) via `DATABASE_URL` |
| Objet transaction en mémoire | conservé comme cache d'écriture, base = source de vérité |
| Idempotence | `Idempotency-Key`, scopée par marchand, rejeu → même référence + nouveau jeton |
| Rejeu d'une décision | `409` (statut non actionnable), jeton à usage unique |
| Expiration | paresseuse, `TRANSACTION_TTL_MINUTES` (30 min par défaut) |
| Rate limiting | fenêtre glissante maison (pas de dépendance), `429` + `Retry-After` |
| Webhooks | synchrones, retry ×5, jamais bloquants pour la réponse |
| SSRF | actif par défaut ; `WEBHOOK_BLOCK_PRIVATE=false` réservé aux démos locales |
| Sessions | en mémoire (éphémères), comptes persistés |

### 6. Vérifications réellement exécutées

```
.venv\Scripts\python.exe -m pytest -q          → 132 passed
.venv\Scripts\ruff.exe check app tests         → All checks passed!
alembic upgrade head (base vide)                → tables créées, colonnes conformes
```

Serveur réel (port 8124, base jetable) :

```
GET  /docs                                  → 200
GET  /api/v1/health                         → 200 {"mode":"SIMULATION"}
POST /api/v1/auth/register                  → 201 (clé secrète affichée 1 fois)
POST /api/v1/payments (moov, 01970000)      → 201 {"status":"CREATED","is_final":false}
POST /api/v1/payments/{ref}/decision CONFIRM → 200 {"status":"SUCCEEDED","is_final":true}
GET  /api/v1/payments/{ref}                 → 200 SUCCEEDED (relu depuis la base)
rejouer la décision                         → 409 "Transaction déjà traitée"
GET  / , /demo/boutique, /demo/widget,
     /demo/numeros-de-test                   → 200 (mention SIMULATION présente)
```

### 7. Limites connues et points de vigilance

- **Base locale `projet1/3dpay.db`** : elle avait été créée avec l'ancien schéma
  (table `transaction_events`, colonnes `phone`/`order_reference`) et elle est
  **verrouillée par un serveur uvicorn encore actif**. À traiter une fois le
  serveur arrêté : supprimer le fichier puis `alembic upgrade head`.
- Le retry des webhooks est **synchrone** : suffisant pour une démonstration,
  à déplacer dans une tâche de fond pour une charge réelle.
- Les sessions restent en mémoire (déconnexion au redémarrage) — assumé.
- `refunded` / `transferred` restent hors périmètre MVP.
- Le déploiement Render/Neon n'a pas été exécuté (identifiants absents) : seul
  le blueprint est fourni.

### Tester manuellement

1. `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
2. `/docs` → `POST /auth/register` → copier la `secret_key`
3. `/demo/boutique` → coller la clé, montant, opérateur, `01970000` → Payer
4. Dans le widget : **Confirmer** → statut `SUCCEEDED`
5. `GET /dashboard/transactions` (session) → la transaction et son état final
6. `/demo/numeros-de-test` → tableau publié des scénarios
