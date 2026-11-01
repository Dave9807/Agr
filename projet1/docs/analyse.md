/# ANALYSE DU PROJET 3DPAY — STACK, INFRASTRUCTURES ET PLAN DÉTAILLÉ

> Document destiné à l'équipe. Il complète `CONTEXTE_PROJET.md` (référence fonctionnelle)
> en y ajoutant les décisions techniques : choix de la stack, comparatif des infrastructures
> et plan de réalisation détaillé.
>
> Date de l'analyse : octobre 2026
> Statut : proposition soumise à validation de l'équipe

---

## 1. Résultat de l'analyse

### 1.1 Ce que demande le cahier des charges (`CONTEXTE_PROJET.md`)

- Simuler un agrégateur de paiement Mobile Money (MTN, Moov, Celtiis) au Bénin.
- **Simulation uniquement** : aucun transfert d'argent réel, aucune dépendance aux API privées des opérateurs.
- **Libre-service** : un développeur s'inscrit, reçoit ses 2 clés (publique + secrète), branche son
  système et suit tout dans un **tableau de bord** — c'est la vision 3Dpay.
- **Un seul numéro de test** : les 3 opérateurs restent au choix, mais un numéro fictif unique
  pilote le scénario de résultat (succès, échec, solde insuffisant, attente).
- Stack annoncée dans le document : **Python + FastAPI + Uvicorn**, API REST en JSON.
- Fonctions essentielles du MVP : consultation des opérateurs, création d'une demande de paiement,
  décision du client (confirmé/refusé), traitement simulé par l'opérateur, machine à statuts,
  consultation par référence, webhooks signés, **idempotence**, authentification, journalisation.
- Sécurité imposée : isolation par compte, clés/mots de passe **hachés**, **rate limiting**,
  **protection SSRF** des webhooks, marquage « SIMULATION ».
- Points pédagogiques centraux : distinguer **code HTTP** (201, 404, 422) et **statut métier**
  (`CREATED`, `SUCCEEDED`…), et comprendre qu'une persistance en mémoire est perdue au redémarrage.

### 1.2 État réel du dépôt (constat important)

| Élément | État réel dans le dépôt |
|---|---|
| `app/main.py` (FastAPI) | **Présent** — app créée, **aucune route** |
| `app/{routes,models,services,operators,notifications}` | Présents, **vides** |
| `tests/` | Présent, vide |
| `requirements.txt` (`fastapi`, `uvicorn`) | Présent ; `.env.example`, `.gitignore` présents ; `.venv` **absent** |
| Squelette Laravel | **Abandonné** — la stack retenue est Python + FastAPI |
| Réponse `422` signalée dans le doc d'origine | **Non vérifiable** : le code concerné n'existe pas ici |

**Conclusion :** l'étape d'audit est faite. Le squelette FastAPI est en place, mais **aucune route,
aucun métier** : on part d'une base propre, rien à sauvegarder côté logique.
⚠️ Les fichiers ont été déplacés sous `Agr-gateur-de-payement/projet1/` alors que Git suit encore
`projet1/` : à réorganiser avant de continuer (voir roadmap phase 1).

### 1.3 Décision technique retenue

**Une seule stack : Python + FastAPI.** Le squelette Laravel n'est pas utilisé pour l'API.

Justification :

1. **Cohérence** : le cahier des charges, la terminologie et la stratégie de développement
   (étapes 1 à 8) sont écrits pour Python/FastAPI.
2. **Pédagogie** : l'objectif d'apprentissage est Python et les API REST. Deux stacks
   dilueraient l'effort d'apprentissage.
3. **Dette technique** : deux stacks signifient deux langages, deux bases de code, deux
   déploiements, deux suites de tests, et la logique de transaction maintenue deux fois.
4. **La raison initiale du choix Laravel (gestion dev/production et travail en équipe) n'exige
   pas Laravel** — elle exige des *pratiques* (environnements séparés, CI, revue de code),
   reproduites avec des outils gratuits côté Python (voir sections 3 et 4).

---

## 2. Comparatif des stacks possibles

### 2.1 Les trois options

| Critère | **A. FastAPI (Python)** | **B. Laravel (PHP)** | **C. Les deux** |
|---|---|---|---|
| Cohérence avec `CONTEXTE_PROJET.md` | ✅ Parfaitement cohérent | ❌ Réécriture du document | ⚠️ Documentation scindée |
| Apprentissage Python / API REST | ✅ C'est l'objectif | ❌ Apprend Laravel + REST en même temps | ⚠️ Dispersé |
| Documentation interactive `/docs` | ✅ Automatique (Swagger) | ⚠️ Package tiers requis | ✅ (via FastAPI) |
| Complexité pour une petite équipe | ✅ Faible | ⚠️ Moyenne | ❌ Élevée |
| Écosystème dev/prod (déploiement, env.) | ✅ Bon, outils gratuits | ✅ Très bon, mature | ❌ Double maintenance |
| Travail en équipe (CI, revues, tests) | ✅ Avec GitHub Actions + pytest | ✅ Avec GitHub Actions + Pest/PHPUnit | ⚠️ Deux pipelines |
| Temps de démarrage | ✅ Immédiat | ⚠️ Squelette déjà prêt mais hors sujet | ❌ Le plus long |
| **Recommandation** | ✅ **Retenue** | Non retenue | Déconseillée |

### 2.2 Pourquoi pas les deux ?

Assembler Laravel **et** FastAPI revient à faire dialoguer deux applications distinctes
(par un pont HTTP ou des files d'attente). Pour un MVP de simulation, cela ajoute :

- deux déploiements à maintenir au lieu d'un ;
- deux modèles de transaction à faire concorder ;
- un point de panne supplémentaire (le pont entre les deux) ;
- une courbe d'apprentissage doublée.

Le cahier des charges exclut d'ailleurs toute complexité superflue
(« Privilégie la simplicité maîtrisée »).

---

## 3. Comment on gère dev / production (le point que l'équipe veut comprendre)

Le choix de Laravel n'est **pas** la bonne réponse à « comment gérer dev et prod ».
La bonne réponse est un **mécanisme d'environnements**. Le voici, tel qu'il sera appliqué ici.

### 3.1 Le principe : un code, plusieurs environnements

```
              ┌─────────────────────────────────────────────┐
              │  Le même code source (commité sur Git)      │
              └─────────────────────────────────────────────┘
                        │                  │                │
              ┌─────────▼───────┐ ┌────────▼───────┐ ┌──────▼─────────┐
              │  DEV            │ │  STAGING       │ │  PRODUCTION    │
              │  .env.develop…  │ │  .env.staging… │ │  .env.prod…    │
              │  SQLite local   │ │  PostgreSQL    │ │  PostgreSQL    │
              │  erreurs visibles│ │  données de test│ │  erreurs masquées│
              └─────────────────┘ └────────────────┘ └────────────────┘
```

- **Le code est identique** dans les trois environnements.
- **Seules les variables d'environnement (`.env`) changent** : URL de la base, clés secrètes,
  niveau de journalisation, URL publique.
- Le code lit la configuration via ces variables, jamais en dur.

### 3.2 Les règles concrètes

| Règle | DEV (ton PC) | STAGING (pré-production) | PROD (public) |
|---|---|---|---|
| Fichier `.env` | `.env.development` | `.env.staging` | `.env.production` |
| Base de données | SQLite (fichier local) | PostgreSQL isolé | PostgreSQL de production |
| Affichage des erreurs | Détaillé | Détaillé | **Masqué** (sécurité) |
| Secrets (clés API) | Fictifs / test | Fictifs | **Vrais, jamais dans Git** |
| Données | De test | Copie représentative | Réelles |
| Qui y accède | Développeurs | Équipe + QA | Utilisateurs finaux |

**Sécurité absolue :** le fichier `.env` **ne se commit jamais**. Seul `.env.example`
(sans les vraies valeurs) est versionné, il sert de gabarit à chaque nouveau développeur.

### 3.3 Le travail en équipe (flux Git + CI)

```
1. Développeur crée une branche      git checkout -b feature/f2-creation-paiement
2. Il code + écrit les tests         pytest  ✅
3. Il push et ouvre une Pull Request sur GitHub
4. La CI (GitHub Actions) exécute automatiquement :
      - lint/formatage (Ruff)
      - tests (pytest)      → si échec, la PR est bloquée
5. Un collègue fait la revue de code
6. Merge sur `main` → déploiement automatique sur STAGING
7. Validation → promotion manuelle en PRODUCTION
```

**La CI (Intégration Continue)** est un script qui tourne sur GitHub à chaque push.
Elle garantit que `main` reste toujours vert : personne ne peut casser la branche principale
sans que tout le le voie immédiatement.

### 3.4 Versionning des bases de données (équivalent des "migrations")

Chaque modification de schéma est un **fichier de migration** commité avec le code :

```bash
alembic upgrade head   # applique les migrations manquantes
```

Tous les développeurs et tous les environnements rejouent la **même séquence** →
structures de base identiques partout. C'est exactement le rôle de `php artisan migrate`
dans Laravel : le concept est universel, seul l'outil change.

---

## 4. Comparatif des infrastructures (gratuit pour le MVP)

### 4.1 Critères de choix

Pour ce projet : **coût zéro**, MVP de démonstration, petite équipe, zone Bénin (bande passante
et latence à considérer), et hébergement simple.

### 4.2 Tableau comparatif détaillé

| Besoin | Option retenue (gratuite) | Alternative gratuite | Option payante (si croissance) | Pourquoi ce choix |
|---|---|---|---|---|
| **Code + collaboration** | **GitHub** | GitLab, Codeberg | — | PR, branches protégées, revues, Actions intégrés |
| **CI/CD** | **GitHub Actions** (100 h/mois gratuites) | GitLab CI, CircleCI | — | Natif avec le dépôt, zéro config externe |
| **Base de données DEV** | **SQLite** | — | — | Zéro installation, fichier local |
| **Base de données PROD** | **Neon** (PostgreSQL, free tier) | Supabase, Aiven, CockroachDB Cloud | Render Postgres | PostgreSQL complet, branching possible |
| **Hébergement API** | **Render** (free tier) | Fly.io, Railway (crédits), PythonAnywhere | Scaleway / Hetzner VPS | Déploiement Git direct, HTTPS inclus |
| **Environnements** | **Fichiers `.env`** par environnement | — | — | Standard de l'industrie, aucun coût |
| **Tests / lint** | **pytest + Ruff** | — | — | Standards Python, rapides |
| **Rate limiting** | **slowapi** (middleware FastAPI) | `starlette-limitter` | WAF / reverse-proxy | Réponses `429` sans infrastructure |
| **Protection SSRF (webhooks)** | Validation maison : déni des URL privées/locales | `ipaddress` + résolution DNS | Proxy egress dédié | Zéro dépendance pour un MVP |
| **Mots de passe / clés** | **bcrypt** (`passlib`) + SHA-256 pour les clés | argon2 | — | Hachage irréversible, jamais en clair |
| **Documentation API** | **Swagger `/docs` de FastAPI** | — | — | Générée automatiquement, sans effort |
| **Journalisation** | **Fichiers + stdout** (Render les capture) | — | Sentry (free tier) si besoin | Suffisant pour un MVP |
| **Stockage de secrets** | **Variables d'environnement GitHub / Render** | — | — | Jamais dans le code |

### 4.3 ⚠️ Points de vigilance des free tiers

- **Render (free web service)** : le service **dort après ~15 min sans requête** ;
  le premier appel au réveil prend 30 à 60 s. Acceptable pour une démo, pas pour la prod réelle.
  *Contournement : un cron externe ping l'API toutes les 10 min (Render + cron-job.org gratuits).*
- **Neon / Supabase** : base suspendue après inactivité (réactivation automatique).
- **Quota GitHub Actions** : 2 000 min/mois sur les dépôts publics → largement suffisant.
- **Migration future** : si le projet sort du statut MVP, prévoir un VPS (Hetzner ≈ 4 €/mois)
  avec Docker, ou une offre managée. **Aucune réécriture du code** sera nécessaire : seules
  les variables d'environnement changent — c'est tout l'intérêt du schéma de la section 3.

### 4.4 Architecture cible

```
Site marchand (simulé)                    Développeur (navigateur)
        │  HTTPS / JSON                        │  session
        ▼                                      ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI (Render)                                       │
│  ├── routes/        (API REST publique + protégée)      │
│  ├── auth/          (inscription, connexion, clés)      │
│  ├── dashboard/     (transactions, webhooks, réglages)  │
│  ├── services/      (logique métier, machine à statuts) │
│  ├── operators/     (MTN, Moov, Celtiis + nº de test)   │
│  ├── webhooks/      (signé HMAC, retry, anti-SSRF)      │
│  └── logging/       (journalisation)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ SQLAlchemy + Alembic
                       ▼
                PostgreSQL (Neon)   ← dev : SQLite

GitHub ──push──▶ GitHub Actions (pytest + Ruff) ──▶ Render (staging/prod)
```

---

## 5. Plan détaillé de réalisation

> Adapté des étapes 1 à 8 du cahier des charges, mais réécrit pour la stack retenue.
> **Une étape = un objectif vérifiable.** On ne passe à la suivante que si la précédente est testée.

### Étape 0 — Décisions d'architecture (à valider par l'équipe)

- [x] Stack **FastAPI seule**.
- [x] **Libre-service** : inscription/connexion + 2 clés par compte (`3dp_pub_…`, `3dp_sec_…`).
- [x] En-tête `Authorization: Bearer <clé_secrète>` (variante `X-API-Key` à confirmer).
- [x] **Un seul numéro de test** commun aux 3 opérateurs (valeurs à figer).
- [x] **Tableau de bord minimal** inclus dans le MVP.
- [x] **Rate limiting** + **protection SSRF** des webhooks dans le MVP (seuils/bibliothèque à choisir).
- [ ] Statuts métier retenus et transitions autorisées (figer la liste du §F6).
- [ ] Base de données : SQLite (dev) / PostgreSQL (prod).
- [ ] Schéma de nommage des routes : `/api/v1/...` (versionnage dès le départ).

**Livrable :** ce document validé par l'équipe.

### Étape 1 — Audit et squelette du projet

- Créer l'arborescence :
  ```
  projet1/
  ├── app/
  │   ├── main.py            # point d'entrée FastAPI
  │   ├── config.py          # lecture des variables .env
  │   ├── routes/            # endpoints HTTP uniquement
  │   ├── models/            # schémas Pydantic (validation) + entités
  │   ├── services/          # logique métier (transactions, statuts)
  │   ├── operators/         # MTN, Moov, Celtiis (simulation)
  │   └── notifications/     # notifications simulées
  ├── tests/                 # pytest
  ├── alembic/               # migrations
  ├── .env.example           # gabarit commité
  ├── requirements.txt / pyproject.toml
  └── README.md
  ```
- Initialiser Git + `.gitignore` (`.env`, `.venv`, `__pycache__`).
- Créer le `.env.example` et l'environnement virtuel.
- **Test de validation :** `uvicorn app.main:app --reload` puis ouvrir `/docs` → page affichée.

### Étape 2 — Premières routes et contrats HTTP

- `GET /api/v1/operators` → liste des 3 opérateurs.
- `GET /api/v1/health` → vérification que l'API répond.
- Codes HTTP corrects : `200`, `404`, `422` (validation Pydantic).
- **Test :** `curl` ou Swagger ; `pytest` sur chaque route.
- **Notions :** route, handler, code HTTP, schéma de réponse JSON.

### Étape 3 — Modélisation de la transaction

- Modèle : référence unique, montant, devise, référence commande, opérateur, **numéro de test**,
  statut, horodatages.
- Machine à statuts + **transitions interdites rejetées** (ex. `SUCCEEDED` → `CREATED` = erreur).
- **Test :** unitaire sur chaque transition légale et illégale.
- **Notions :** modèle de données, machine à statuts, validation.

### Étape 3b — Comptes utilisateurs, clés et auth (libre-service)

- `register` / `login` / `logout` : mot de passe **bcrypt**, session (cookie ou jeton opaque).
- 2 clés par compte : `3dp_pub_…` (affichable), `3dp_sec_…` (affichée une seule fois, **SHA-256**).
- Middleware `Authorization: Bearer` → `401` (clé absente/invalide), `403` (compte suspendu).
- Isolation : `merchant_id` sur chaque transaction, clé et webhook.
- **Test :** inscription → clé affichée une fois ; `POST /payments` sans clé → `401` ;
  un compte ne voit jamais les données d'un autre.
- **Notions :** hachage, sessions, middleware, isolation par locataire.

### Étape 4 — Cycle de vie complet (MVP cœur)

- `POST /api/v1/payments` → `201 Created` + référence.
- `GET /api/v1/payments/{reference}` → `200` ou `404`.
- `POST /api/v1/payments/{reference}/decision` → confirmation / refus du client.
- Résultat opérateur simulé : mode contrôlé + mode par règles, piloté par le **numéro de test**
  (**un seul** numéro fictif, commun aux 3 opérateurs — tableau à figer et à documenter).
- **Test :** scénarios succès / refus / attente / erreur technique ; mêmes résultats avec MTN et Moov.
- **Notions :** code HTTP ≠ statut métier (le point clé du cahier des charges).

### Étape 5 — Persistance (SQLite)

- SQLAlchemy + **Alembic** ; suppression du stockage en mémoire.
- **Test décisif :** créer une transaction → redémarrer le serveur → la transaction existe toujours.

### Étape 6 — Fiabilité, webhooks et sécurité

- **Idempotence** via en-tête `Idempotency-Key` (une requête rejouée = 1 transaction).
- **Journalisation** des événements importants (sans données sensibles).
- **Webhook signé** : `POST` vers l'URL déclarée, en-tête `X-3DPay-Signature` (HMAC),
  exigence de réponse **2xx**, sinon **retry ×5** journalisé ; journal des webhooks persisté.
- **Protection SSRF** : refus des URL de webhook vers des adresses internes/privées.
- **Rate limiting** (`slowapi`) sur `/auth/*` et `/payments` → réponse `429`.
- **Test :** rejouer une requête identique → 1 seule transaction ; appel sans clé → `401` ;
  webhook vers `http://127.0.0.1/...` → rejeté ; rafale de requêtes → `429`.

### Étape 6b — Tableau de bord (MVP)

- Accès après `login` ; transactions, journal des webhooks, clés (régénération), réglages.
- Isolation stricte : aucune donnée d'un autre compte visible ; mention « SIMULATION ».
- **Test :** deux comptes créés → chacun ne voit que son propre contenu.

**Notions :** signature HMAC, limitation de débit, isolation multi-tenant.

### Étape 7 — Tests et documentation

- Suite pytest complète : succès, refus, attente, erreurs, idempotence, auth (`401`/`403`),
  rate limiting (`429`), SSRF (URL privée rejetée), webhook (signature + retry), isolation des comptes.
- Exemples JSON documentés pour chaque route + **page des numéros de test**.
- Démonstration complète via `/docs` et le tableau de bord.

### Étape 8 — Infrastructure et CI/CD

- Workflow GitHub Actions : `ruff check` + `pytest` à chaque push/PR.
- Déploiement staging automatique sur `main`, promotion manuelle en production.
- Configuration des `.env` par environnement (Render + Neon).
- **Test :** un push avec un test qui échoue doit **bloquer** la PR.

### Étape 9 — Démonstration du MVP

- Vérifier chaque critère du §10 du cahier des charges.
- Démo scénario complet : création → décision → traitement → consultation → notification.

---

## 6. Récapitulatif des décisions

| Sujet | Décision | Statut |
|---|---|---|
| Stack API | **Python + FastAPI** | ✅ Retenue |
| Laravel | Écarté : le dépôt ne contient plus ce squelette | ✅ Retenu |
| Base DEV / PROD | SQLite / PostgreSQL (Neon) | ✅ Retenue |
| CI/CD | GitHub Actions (gratuit) | ✅ Retenue |
| Hébergement | Render free tier (limitations connues) | ✅ Retenu |
| Modèle économique | **Libre-service** : inscription/connexion + 2 clés (publique, secrète) | ✅ Retenu |
| Auth API | `Authorization: Bearer <clé_secrète>` (hachée SHA-256) | ✅ Retenue (variante `X-API-Key` ⏳) |
| Session tableau de bord | cookie sécurisé **ou** jeton opaque | ⏳ À choisir |
| Numéros de test | **un seul** numéro fictif pour les 3 opérateurs (valeurs ⏳) | ✅ Principe retenu |
| Tableau de bord | minimal, **inclus** dans le MVP | ✅ Retenu |
| Webhook | signé **HMAC** + exigence 2xx + retry ×5 + journal | ✅ Retenu (à coder) |
| Rate limiting | `slowapi` sur `/auth/*` et `/payments` → `429` (seuils ⏳) | ✅ Retenu |
| Protection SSRF | déni des URL privées/locales pour les webhooks | ✅ Retenue |
| Statuts finaux | Liste à figer (§F6 du cahier des charges) | ⏳ À confirmer |
| Versionnement routes | `/api/v1/` | ✅ Retenu |

---

*Document à mettre à jour à chaque changement de décision d'architecture.*
