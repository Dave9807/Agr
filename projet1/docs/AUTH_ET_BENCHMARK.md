# 3DPAY — DÉCISIONS, AUTHENTIFICATION ET BENCHMARK AGRÉGATEURS

> Complément de `CONTEXTE_PROJET.md` (référence fonctionnelle) et `analyse.md` (décisions techniques).
> Document de travail destiné à toute l'équipe : il résume l'état de notre réflexion, les décisions
> prises et celles restant à valider par le chef d'équipe.
>
> Date : octobre 2026
> Statut : proposition soumise à validation

---

## 1. Contexte et thème

- **Thème du projet :** paiement mobile money · simulation d'API · transaction sécurisée.
- **3DPAY** est un agrégateur de paiement Mobile Money **simulé** (MTN Mobile Money, Moov Money, Celtiis Cash) destiné aux sites marchands au Bénin.
- **Vision de la plateforme (3Dpay) :** un service **en libre-service**. Un développeur crée un compte, reçoit ses clés API, branche son système, suit ses transactions dans un tableau de bord — **sans aucun vrai argent**, sans compte chez un vrai agrégateur.
- **Numéro de test unique :** les trois opérateurs restent au choix, mais **un seul numéro de téléphone fictif** est utilisé pour toutes les simulations ; c'est lui qui détermine le scénario de résultat (succès, échec, solde insuffisant, attente).
- **Référence métier :** les agrégateurs réels du marché, notamment **Kkiapay** et **FedaPay**, utilisés par les systèmes e-commerce. Notre objectif n'est pas d'inventer, mais de **reproduire leur logique en version simulée**, sans transfert d'argent réel ni accès aux API privées des opérateurs.
- Objectif pédagogique : construire une API REST testable, documentée et suffisamment proche du réel pour tenir une démonstration devant le chef d'équipe et les membres du corps professoral.

---

## 2. État des lieux du dépôt

| Élément | État réel dans le dépôt |
|---|---|
| `app/main.py` (FastAPI) | **Présent** — app créée, titre/version renseignés, **aucune route** |
| Sous-modules `routes/`, `models/`, `services/`, `operators/`, `notifications/` | **Présents**, tous vides (`__init__.py` seulement) |
| `tests/` | Présent, vide |
| `requirements.txt` | `fastapi`, `uvicorn[standard]` |
| `.env.example` | `APP_ENV`, `APP_DEBUG`, `APP_NAME=3DPAY`, `DATABASE_URL` (SQLite) |
| Squelette Laravel | Non retenu : la stack est **Python + FastAPI** (`analyse.md` §1.3) |

**Conclusion :** le squelette FastAPI est en place (phase 1 en cours), mais **aucune route ni aucun métier n'existe encore**. On part d'une base propre : rien à sauvegarder côté logique.

---

## 3. Les acteurs du système

| Acteur | Parle-t-il à l'API 3DPAY ? | Authentification |
|---|---|---|
| **Site marchand** (serveur → serveur) | **Oui — c'est son seul client réel** | **Oui : clé API par compte** (`Bearer` + clé secrète) |
| **Développeur / marchand (humain)** | Sur le **tableau de bord**, pas sur l'API de paiement | **Oui : inscription / connexion** → session |
| **Client payeur** (internaute) | **Non** — il est sur la boutique, jamais sur 3DPAY | Aucune : sa décision transite par le marchand |
| **Opérateur simulé** (MTN/Moov/Celtiis) | Non — composant **interne** de l'application | Aucune (c'est du code, pas un tiers) |
| **Équipe / admin** | Administration complète | Hors MVP |

**Phrase clé (§F10 du cahier des charges) :** *ne pas confondre l'authentification technique du site marchand auprès de l'API avec une éventuelle authentification du client payeur.*

Il y a **deux authentifications distinctes** côté 3Dpay :
1. **l'humain** (développeur) → inscription/connexion → tableau de bord (session) ;
2. **la machine** (serveur du marchand) → clé API secrète → API de paiement.

Le client payeur n'a **aucun** compte 3Dpay : c'est le point de confusion principal à écarter.

---

## 4. Décision : comptes utilisateurs + clés API (libre-service)

La plateforme est en libre-service : **n'importe quel développeur peut s'inscrire et recevoir ses clés.** Deux niveaux d'authentification, jamais confondus.

### 4.1 Niveau humain — le tableau de bord

| Élément | Choix |
|---|---|
| Opérations | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` |
| Identifiants | e-mail + mot de passe |
| Mot de passe | haché (**bcrypt** / `passlib`), jamais en clair, jamais journalisé |
| Session | jeton de session (cookie sécurisé ou jeton opaque) — **pas d'OAuth2** |
| Portée | accès **uniquement à ses propres** clés, transactions, webhooks, réglages |

### 4.2 Niveau machine — l'API de paiement

| Élément | Choix |
|---|---|
| En-tête | `Authorization: Bearer <clé_secrète>` ⏳ *(variante `X-API-Key` à confirmer)* |
| **Clé publique** | identifiant du compte (`3dp_pub_…`), affichable côté client / widget ; **n'authentifie pas** les routes serveur |
| **Clé secrète** | `3dp_sec_…`, aléatoire 32+ caractères ; sert seule à authentifier les appels serveur → serveur |
| Routes publiques | `GET /api/v1/health`, `GET /api/v1/operators`, `POST /api/v1/auth/*` |
| Routes protégées | `POST /api/v1/payments`, `GET /api/v1/payments/{reference}`, `POST /api/v1/payments/{reference}/decision` |
| Erreurs | clé absente ou invalide → `401` ; compte suspendu → `403` ; corps JSON structuré |
| Stockage | table `merchants` : `id, name, email, password_hash, public_key, api_key_hash (sha256), status, created_at` |
| Règle de sécurité | la clé secrète n'est affichée **qu'une fois** à la création ; **stockée hachée**, jamais journalisée |
| Rotation | `POST /api/v1/keys/rotate` régénère la clé secrète et **révoque l'ancienne** |
| Effet utile | `payments.merchant_id` rattache chaque transaction à son compte |
| Idempotence | en-tête `Idempotency-Key` **scopée par marchand** (deux marchands peuvent réutiliser la même clé sans conflit) |

### 4.3 Pourquoi pas autre chose

- *Clé seule, sans compte* (seed/scripts) : rejeté — la vision est le **libre-service** ; chaque développeur crée lui-même son compte.
- *Clé unique sans clé publique* : la clé publique sert d'identifiant affichable côté client, comme chez Kkiapay ; elle ne remplace jamais la secrète.
- *OAuth2 / JWT complet* : surdimensionné pour un MVP de simulation ; une session simple + une clé statique suffisent.
- *Authentifier le client payeur* : impossible et inutile — il n'appelle jamais 3DPAY.

---

## 5. Exclusions assumées et règles de sécurité

### 5.1 Exclusions

- Pas d'OAuth2 ni de protocole d'authentification complexe (session + clé statique suffisent).
- Pas d'authentification du client payeur au niveau de l'API.
- Pas de secret dans le code source, les réponses ni les journaux (clés **hachées**).
- Pas de véritable code secret Mobile Money demandé ou stocké.
- Pas de paiement réel, pas d'intégration aux API privées des opérateurs.

### 5.2 Règles de sécurité imposées (MVP)

- **Isolation** : chaque compte ne voit que **ses propres** données (clé, transactions, webhooks).
- **Clés secrètes hachées** (SHA-256), affichées une seule fois, jamais journalisées.
- **Mots de passe hachés** (bcrypt).
- **Limitation du débit** (rate limiting) sur les routes sensibles (auth, création de paiement) contre les abus.
- **Protection SSRF** des webhooks : une URL déclarée vers une adresse interne/privée (localhost, `10.*`, `192.168.*`, `169.254.*`…) est **refusée**.
- **Signature HMAC** des webhooks (`X-3DPay-Signature`) + exigence de réponse 2xx, sinon retry journalisé.
- **Marquage « SIMULATION »** sur l'interface, la documentation et les réponses ; aucune donnée bancaire réelle.

---

## 6. Benchmark : comment fonctionnent Kkiapay et FedaPay

### 6.1 Deux canaux d'intégration, jamais un seul

1. **Côté client (navigateur) :** un widget ou SDK **hébergé par l'agrégateur** (`<kkiapay-widget>` chez Kkiapay, `generateToken()` → URL de paiement chez FedaPay). **C'est là que le client choisit son opérateur, reçoit l'OTP et confirme.** Aucune donnée de paiement ne transite par le serveur du marchand.
2. **Côté serveur (machine → machine) :** API REST pour créer, vérifier et rembourser des transactions. **C'est la seule partie authentifiée par clé.**

### 6.2 Le flux type (FedaPay)

```
POST /v1/transactions      (Authorization: Bearer SECRET_KEY)
  → 201 { id, reference, amount, status: "pending" }
→ generateToken() → URL de paiement
→ le CLIENT paie sur l'écran de l'agrégateur (choix opérateur + OTP)
→ webhook "transaction.approved" envoyé au marchand (signé, avec retry)
→ en secours, le marchand consulte : GET /v1/transactions/{id}   (polling / verify)
→ remboursement éventuel : POST refund
```

### 6.3 Authentification réelle

- **Kkiapay :** 3 clés — *publique* (widget côté client), *privée* (vérification serveur), *secrète* (mutations).
- **FedaPay :** 1 clé secrète en `Authorization: Bearer`, avec environnements `sandbox` / `live`.
- **Aucun des deux n'authentifie le client payeur au niveau de l'API.**

### 6.4 Webhooks, pas des « notifications » vagues

- Payload JSON nommé `transaction.created / approved / declined / canceled / transferred`.
- En-tête de **signature HMAC** (`x-kkiapay-secret` chez Kkiapay, `X-FedaPay-Signature` chez FedaPay).
- Le marchand doit répondre **HTTP 2xx**, sinon retry : **5 tentatives** (Kkiapay), **9 tentatives exponentielles** puis désactivation (FedaPay).
- Protection anti-replay par timestamp inclus dans la signature.

### 6.5 Cycle de vie des statuts (FedaPay)

`pending` → `approved` | `declined` | `canceled` | `expired`, puis `refunded` | `transferred` après coup.

- `declined` = refus ou interruption **par le client** ;
- `canceled` = échec côté opérateur (fonds insuffisants, etc.).

**Deux notions bien séparées — exactement ce que demande notre §F6.**

---

## 7. Table de correspondance 3DPAY ↔ agrégateurs réels

| Pilier agrégateur | 3DPAY actuel | Verdict |
|---|---|---|
| **Libre-service** : compte + clés auto-générées | inscription / connexion + 2 clés (publique, secrète) | ✅ Comme Kkiapay |
| Seul le marchand authentifié, pas le client payeur | clé API secrète par compte | ✅ Conforme au réel |
| `POST` création → `201` + référence + statut d'attente | `POST /payments` → `201` + `CREATED` | ✅ Identique à FedaPay |
| Refus client ≠ rejet opérateur | `DECLINED_BY_CUSTOMER` ≠ `REJECTED_BY_OPERATOR` | ✅ Plus fin que FedaPay |
| Consultation par référence en secours | `GET /payments/{reference}` | ✅ = *verify* |
| Mode test / sandbox | environnements dev/prod + mode contrôlé + **numéro de test unique** | ✅ Équivalent |
| Tableau de bord marchand | tableau de bord minimal (transactions, webhooks, clés, réglages) | ✅ Conforme au réel |
| **Webhook signé avec retry et exigence 2xx** | prévu (roadmap phase 7), **pas encore codé** | ⏳ **Écart n°1 — à livrer** |
| **Limitation du débit** | prévue, **pas encore codée** | ⏳ à livrer |
| **Protection SSRF des webhooks** | prévue, **pas encore codée** | ⏳ à livrer |
| **En-tête `Authorization: Bearer`** | retenu (variante `X-API-Key` à confirmer) | ⚠️ Écart cosmétique |
| **Nommage des événements `transaction.*`** | retenu, à appliquer | ⚠️ Gratuit à aligner |
| `refunded` / `transferred` (remboursement, décaissement) | exclus | ⚠️ **Hors périmètre MVP assumé** (CONTEXTE §3.2) — à argumenter à l'oral |

**Conclusion : notre logique est déjà celle des agrégateurs.** Les fossés restants sont d'ordre **d'implémentation** (webhook signé, rate limiting, SSRF), pas de conception.

---

## 8. Ajustements à réaliser

1. **Webhook simulé** (remplace le F8 vague) :
   - `POST` vers l'URL déclarée par le marchand ;
   - payload : `{event: "transaction.succeeded" | "transaction.declined" | "transaction.failed", reference, status, amount, occurred_at}` ;
   - en-tête `X-3DPay-Signature` (HMAC) ;
   - exigence de réponse **HTTP 2xx**, sinon **retry simulé ×5** visible dans les logs ;
   - le `GET /payments/{reference}` reste le mécanisme de repli.
2. **Bascule de l'en-tête d'authentification** vers `Authorization: Bearer <api_key>`.
3. **Nommage des événements** en `transaction.*`.
4. **Table d'équivalence des statuts** à documenter :

| 3DPAY | FedaPay |
|---|---|
| `CREATED` | `pending` |
| `AWAITING_CUSTOMER_ACTION` | `pending` (décision du client) |
| `PROCESSING` | `pending` (opérateur en cours) |
| `SUCCEEDED` | `approved` |
| `DECLINED_BY_CUSTOMER` | `declined` |
| `REJECTED_BY_OPERATOR` | `canceled` |
| `EXPIRED` | `expired` |
| `FAILED` | échec technique (`failureCode`) |
| *(non prévu)* | `refunded`, `transferred` — hors MVP |

5. **Comptes en libre-service** : `register` / `login` (mot de passe bcrypt), puis 2 clés par compte
   (`3dp_pub_…` affichable, `3dp_sec_…` affichée une seule fois et hachée), rotation possible.
6. **Tableau de bord minimal** : transactions, journal des webhooks, clés, réglages — isolation par compte.
7. **Documentation des numéros de test** : un **seul numéro fictif** commun aux 3 opérateurs, avec le
   scénario associé (succès, échec, solde insuffisant, attente) — tableau à figer.
8. **Rate limiting** sur `auth` et `payments` (réponse `429` explicite).
9. **Protection SSRF** : rejet des URL de webhook pointant vers une adresse interne/privée.
10. **Marquage « SIMULATION »** dans les réponses API, la documentation et le widget.

---

## 9. Plan en phases

### Phase 0 — Acter les décisions (étape 0 de `analyse.md`)
Stack, en-tête d'auth, libre-service (comptes + 2 clés), inclusion du webhook, numéro de test unique, tableau de bord, page widget de démo.

### Phase 1 — Documentation
Ce document + `AUTH` (contrat d'authentification détaillé) ; mise à jour de `analyse.md` si les décisions changent.

### Phase 2 — Implémentation (étapes 1→10 de `analyse.md`, avec les alignements §8)

| Étape | Contenu | Alignement agrégateur |
|---|---|---|
| 1 | Squelette FastAPI + `/docs` | — |
| 2 | `GET /operators`, `GET /health` | ≈ choix `mtn_open` / `moov_open` |
| 3 | Modèle transaction + machine à statuts | table d'équivalence (§8.4) |
| 4 | Cycle complet : création → décision → opérateur simulé + **numéro de test unique** | `201 + référence + attente` = FedaPay |
| 5 | Persistance SQLite (Alembic) | — |
| 6 | **Comptes (inscription/login) + 2 clés** + idempotence + table `merchants` | libre-service façon Kkiapay |
| 6b | **Webhook simulé signé + retry** | `transaction.*`, `X-3DPay-Signature`, 2xx |
| 6c | **Rate limiting + protection SSRF** | sécurité attendue de tout agrégateur |
| 7 | **Tableau de bord minimal** (transactions, webhooks, clés, réglages) | espace marchand |
| 8 | Tests pytest + documentation `/docs` | sandbox / mode contrôlé |
| 9 | CI GitHub Actions (Ruff + pytest) | — |
| 10 | **Scénario de démo e-commerce** | boutique fictive → widget simulé → webhook → consultation → succès |

### Phase 3 — Démonstration
Rejouer le parcours d'un marchand e-commerce réel, en montrant à chaque brique : *« chez Kkiapay/FedaPay c'est ceci, ici c'est sa version simulée. »*

---

## 10. Points à confirmer par le chef d'équipe ⏳

| # | Point | Recommandation de l'équipe |
|---|---|---|
| 1 | Stack **FastAPI seule** | ✅ Oui (actée dans `analyse.md`) |
| 2 | En-tête `Authorization: Bearer` (plutôt que `X-API-Key`) | ✅ Oui |
| 3 | **Webhook simulé** inclus dans le MVP | ✅ Oui |
| 4 | Page « widget » HTML minimale pour la démo | ✅ Oui |
| 5 | Jeton de session pour le **client payeur** | ❌ Non — remplacé par un **`decision_token`** à usage unique (phase 4, voir `NUMEROS_DE_TEST.md` §4) |
| 6 | Liste finale des statuts et transitions | à figer en étape 0 |
| 7 | Routes versionnées en `/api/v1/` | ✅ Oui |
| 8 | **Libre-service** : inscription/connexion + 2 clés (remplace la création par seed) | ✅ Oui (vision 3Dpay) |
| 9 | **Tableau de bord minimal** dans le MVP | ✅ Oui |
| 10 | **Un seul numéro de test** pour les 3 opérateurs | ✅ Oui |
| 11 | Valeurs exactes des numéros de test et scénarios associés | ✅ Figées : `01970000` succès · `01970001` refus · `01970002` solde insuffisant · `01970003` attente · inconnu = refus (`docs/NUMEROS_DE_TEST.md`) |
| 12 | **Rate limiting** + **protection SSRF** dans le MVP | ✅ Oui (seuils/bibliothèque à choisir) |
| 13 | Session : cookie sécurisé ou jeton opaque | ⏳ à choisir |

---

*Document à mettre à jour à chaque changement de décision.*
