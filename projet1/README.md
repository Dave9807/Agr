# 3DPay — agrégateur de paiement Mobile Money **simulé**

> Plateforme en libre-service : un développeur s'inscrit, reçoit ses clés,
> encaisse des paiements Mobile Money **fictifs** (MTN Mobile Money, Moov Money,
> Celtiis Cash), reçoit des **webhooks signés** et suit tout dans un tableau de
> bord. **Aucun argent réel ne circule. Tout est marqué `SIMULATION`.**

---

## 1. Démarrage rapide

```bash
# 1. environnement virtuel
python -m venv .venv
.\.venv\Scripts\activate          # Windows (PowerShell/CMD)
# source .venv/bin/activate       # Linux / macOS

# 2. dépendances
pip install -r requirements.txt

# 3. configuration
copy .env.example .env            # Windows
# cp .env.example .env            # Linux / macOS

# 4. lancement
uvicorn app.main:app --reload
```

- API interactive : <http://127.0.0.1:8000/docs>
- Démonstration : <http://127.0.0.1:8000/demo/boutique>
- Numéros de test : <http://127.0.0.1:8000/demo/numeros-de-test>

La base SQLite `3dpay.db` est créée automatiquement au démarrage.

---

## 2. Parcours de démonstration (5 minutes)

1. `POST /api/v1/auth/register` → copier `secret_key` (`3dp_sec_…`) **affichée une seule fois**.
2. Ouvrir `/demo/boutique`, coller la clé, choisir un montant, un opérateur et un
   numéro de test → la boutique crée le paiement (`201 CREATED`).
3. Le widget s'ouvre : le client **confirme** ou **refuse** (via le `decision_token`).
4. Le marchand consulte `GET /api/v1/payments/{reference}` (repli toujours disponible).
5. Le webhook signé part vers l'URL configurée dans le tableau de bord, avec
   retry ×5 si le marchand ne répond pas `2xx`.

---

## 3. Contrat de l'API

| Route | Accès | Rôle |
|---|---|---|
| `GET /api/v1/health` | publique | état de l'API |
| `GET /api/v1/operators` | publique | les 3 opérateurs simulés |
| `POST /api/v1/auth/register` | publique | inscription + 2 clés |
| `POST /api/v1/auth/login` | publique | session `sess_…` (24 h) |
| `GET /api/v1/auth/me` · `POST /api/v1/auth/logout` | session | compte courant |
| `POST /api/v1/keys/rotate` | clé secrète | rotation de la clé secrète |
| `POST /api/v1/payments` | clé secrète | créer une demande (`201`, statut `CREATED`) |
| `GET /api/v1/payments/{reference}` | clé secrète | consulter (`200` / `404`) |
| `POST /api/v1/payments/{reference}/decision` | `decision_token` | confirmation / refus du client |
| `GET /api/v1/dashboard/transactions` | session | mes transactions |
| `GET /api/v1/dashboard/transactions/{reference}` | session | détail |
| `GET /api/v1/dashboard/webhooks` | session | journal des webhooks |
| `GET/PATCH /api/v1/dashboard/settings` | session | URL de webhook, compte |
| `GET /api/v1/dashboard/keys` · `POST /api/v1/dashboard/keys/rotate` | session | clés |

**Deux authentifications distinctes** : session humaine (tableau de bord) et clé
secrète machine (serveur marchand). Le **client payeur n'a aucun compte** : sa
décision est prouvée par un `decision_token` à usage unique.

**Code HTTP ≠ statut métier** : un `201` peut contenir `CREATED`, un `200` peut
contenir `PROCESSING` (résultat non définitif, jamais présenté comme un succès).

---

## 4. Numéros de test

Un même jeu de numéros pour les **trois** opérateurs (le numéro décide, pas
l'opérateur) — détail dans [`docs/NUMEROS_DE_TEST.md`](docs/NUMEROS_DE_TEST.md).

| Numéro | Scénario | Statut |
|---|---|---|
| `01970000` | succès | `SUCCEEDED` |
| `01970001` | refus opérateur | `REJECTED_BY_OPERATOR` (`OPERATOR_DECLINED`) |
| `01970002` | solde insuffisant | `REJECTED_BY_OPERATOR` (`INSUFFICIENT_FUNDS`) |
| `01970003` | attente | `PROCESSING` |
| autre | numéro inconnu | `REJECTED_BY_OPERATOR` (`INVALID_TEST_NUMBER`) |

---

## 5. Structure

```
app/
├── main.py            # application FastAPI, routeurs, gestionnaire d'erreurs
├── config.py          # lecture du .env (aucun secret en dur)
├── db.py              # moteur SQLAlchemy + sessions
├── deps.py            # contrôles Authorization (Bearer, HTTPBearer/Swagger)
├── errors.py          # erreurs métier portant leur code HTTP
├── models/
│   ├── entities.py    # tables : merchants, transactions, webhooks, idempotence
│   ├── schemas.py     # validation Pydantic (422)
│   └── statuses.py    # 8 statuts + table des transitions autorisées
├── operators/         # mtn.py, moov.py, celtiis.py + règles des numéros
├── services/
│   ├── auth.py        # comptes, clés (bcrypt / SHA-256), sessions
│   ├── payments.py    # cycle de vie, machine à statuts, expiration, webhooks
│   ├── idempotency.py # Idempotency-Key scopée par marchand
│   ├── ratelimit.py   # fenêtre glissante → 429
│   └── webhooks.py    # HMAC, retry ×5, anti-SSRF, journal
└── routes/            # health, operators, auth, payments, dashboard, pages
alembic/               # migrations de base de données
tests/                 # 133 tests pytest
```

---

## 6. Tests et qualité

```bash
pytest -q                      # suite complète
ruff check app tests           # lint / import order
```

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute `ruff` puis `pytest`
à chaque push et à chaque pull request : une PR avec un test en échec est bloquée.

---

## 7. Migrations (Alembic)

```bash
alembic upgrade head                                  # appliquer le schéma
alembic revision --autogenerate -m "ma modification"  # nouvelle migration
```

Le schéma est aussi créé automatiquement au démarrage (`create_all`, idempotent),
ce qui rend le démarrage local immédiat ; Alembic reste la référence pour les
environnements déployés.

---

## 8. Déploiement (gratuit)

- **API** : Render (free tier) — `render.yaml` fourni ;
- **Base** : Neon (PostgreSQL gratuit) — renseigner `DATABASE_URL` ;
- **Secrets** : variables d'environnement Render/GitHub, jamais dans Git ;
- **CI/CD** : GitHub Actions (ruff + pytest) ; `main` protégée par PR.

> Render (free) met le service en veille après ~15 min d'inactivité : le premier
> appel après réveil prend 30–60 s. Acceptable pour une démonstration.

---

## 9. Limites assumées (MVP)

- Remboursements, décaissements et intégrations réelles avec les opérateurs : **hors périmètre**.
- Les sessions sont en mémoire : un redémarrage déconnecte le tableau de bord
  (les comptes, transactions et webhooks, eux, sont persistés).
- Le retry des webhooks est synchrone (bloquant) : suffisant pour une démonstration.

---

*Documentation détaillée : [`docs/`](docs) — contexte, analyse technique,
roadmap, journal de suivi, numéros de test.*
