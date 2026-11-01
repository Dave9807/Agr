# DOCUMENT DE CONTEXTE DU PROJET — OPENCODE

## 1. Présentation générale

**Nom du projet :** Agrégateur de paiement Mobile Money  
**Nom de travail de l'API :** 3DPay API  
**Nom commercial / plateforme :** **3Dpay**  
**Domaine :** Fintech, paiements numériques et intégration d'API  
**Zone de référence :** Bénin  
**Technologie actuellement utilisée :** Python avec FastAPI et Uvicorn  
**Type de solution :** plateforme de paiement Mobile Money **simulée**, en libre-service.

### L'idée en une phrase

**3Dpay est une plateforme de paiement mobile money simulée**, où n'importe quel développeur peut créer un compte, recevoir ses propres clés API et tester ou démontrer son système de paiement, **sans aucun vrai argent**.

### Mission du projet

Le projet consiste à concevoir, développer et tester une API REST capable de centraliser des demandes d'encaissement Mobile Money pour des sites marchands.

L'objectif est de simuler le fonctionnement d'un agrégateur de paiement qui permettrait à un site marchand de proposer plusieurs moyens de paiement Mobile Money à ses clients à travers une interface technique unique.

**Côté plateforme :** 3Dpay fonctionne comme un service en libre-service. Un développeur s'inscrit, reçoit ses clés, branche son système sur l'API et suit ses transactions dans un tableau de bord — le tout sans compte chez un vrai agrégateur, sans documents, sans validation et sans argent réel.

### Le problème résolu

Pour tester un site e-commerce avec le mobile money, il faut normalement un compte chez un vrai agrégateur (FedaPay, Kkiapay…), des documents, une validation, et parfois du vrai argent. 3Dpay offre un **terrain d'essai libre et immédiat**, pour apprendre, développer et faire des démonstrations.

### Schéma de fonctionnement

```
Site e-commerce du développeur ──► API 3Dpay ──► Opérateur fictif
                     ▲                                   │
                     └────────── Webhook signé ◄─────────┘
```

Les opérateurs concernés sont :

- MTN Mobile Money ;
- Moov Money ;
- Celtiis Cash.

**Important :** il s'agit d'une simulation logicielle. Le projet ne doit effectuer aucun transfert d'argent réel et ne doit pas dépendre d'un accès aux API privées des opérateurs. Tout est marqué **« SIMULATION »** et aucune vraie donnée bancaire n'est demandée.

**Point important sur les numéros :** les trois opérateurs restent proposés au choix sur le site marchand, mais **un seul et même numéro de téléphone fictif** est utilisé pour toutes les simulations. Ce numéro est l'entrée de l'opérateur fictif : c'est lui qui détermine le résultat (succès, échec, solde insuffisant, attente…). Voir §F13.

L'objectif est de construire une base fonctionnelle, testable, compréhensible et suffisamment structurée pour pouvoir être améliorée par la suite.

---

## 2. Problématique et objectifs

### 2.1 Problématique

Un site marchand qui souhaite proposer plusieurs opérateurs Mobile Money doit pouvoir créer une demande de paiement, identifier l'opérateur choisi, suivre l'évolution de la transaction et recevoir le résultat du traitement.

Le projet vise à centraliser ces opérations au moyen d'une API unique, tout en garantissant la cohérence des données, la traçabilité des transactions et la gestion des erreurs.

### 2.2 Objectif général

Développer une API REST de simulation d'encaissements Mobile Money, permettant de gérer le cycle de vie d'une transaction depuis la création de la demande jusqu'à l'enregistrement et à la consultation de son résultat.

### 2.3 Objectifs spécifiques

1. Créer une demande d'encaissement à partir des données transmises par un site marchand.
2. Proposer une liste d'opérateurs Mobile Money simulés.
3. Simuler le choix de l'opérateur par le client sur le site marchand.
4. Représenter la confirmation ou le refus du client.
5. Simuler le traitement de la demande par l'opérateur choisi.
6. Gérer différents résultats : succès, refus, attente et erreur technique.
7. Générer une référence unique pour chaque transaction.
8. Permettre la consultation du statut d'une transaction à partir de sa référence.
9. Simuler les notifications envoyées au site marchand lors des changements de statut pertinents.
10. Prévenir les doubles traitements grâce à un mécanisme d'idempotence.
11. Sécuriser les appels API, valider les données et journaliser les événements importants.
12. Tester les fonctionnalités au moyen de requêtes HTTP et de réponses JSON.

---

## 3. Périmètre fonctionnel

### 3.1 Fonctionnalités prévues pour le MVP

Le MVP est la première version minimale démontrant les fonctions essentielles du projet.

#### F1 — Consultation des opérateurs

L'API doit exposer une opération permettant d'obtenir la liste des opérateurs simulés disponibles.

La liste initiale comprend MTN Mobile Money, Moov Money et Celtiis Cash.

Chaque opérateur doit pouvoir être identifié de manière cohérente dans les requêtes et les réponses.

#### F2 — Création d'une demande d'encaissement

Le site marchand transmet à l'API les informations nécessaires à la création d'une demande, notamment :

- le montant ;
- la devise ;
- la référence de commande du marchand ;
- l'opérateur choisi par le client ;
- les autres informations strictement nécessaires au scénario de simulation.

L'API valide les données, crée la transaction et lui attribue une référence unique.

La réponse doit être structurée en JSON et fournir les informations utiles, notamment la référence de transaction et son statut initial.

**Règle essentielle :** créer une demande de paiement ne signifie pas que le paiement est réussi.

#### F3 — Choix de l'opérateur

Le client choisit son opérateur sur le site marchand avant que celui-ci transmette la demande à l'agrégateur.

L'API reçoit donc l'opérateur sélectionné. Elle ne doit pas déplacer arbitrairement cette responsabilité vers une interface de sélection appartenant à l'agrégateur.

#### F4 — Confirmation ou refus du client

Le système doit représenter les deux possibilités :

- le client confirme la demande de paiement simulée ;
- le client refuse la demande.

Ces deux décisions doivent produire des résultats métier distincts.

Aucun véritable code secret Mobile Money ne doit être demandé ou stocké. Les informations utilisées doivent être fictives.

#### F5 — Simulation du traitement opérateur

Une fois la demande soumise au traitement simulé, le composant représentant l'opérateur retourne un résultat.

Deux modes de simulation sont prévus :

**Mode contrôlé :** un scénario de test permet d'obtenir un résultat déterminé, par exemple un succès, un refus, une attente ou une erreur.

**Mode fondé sur des règles :** le résultat est déterminé par des règles prédéfinies et documentées.

Les résultats doivent être suffisamment reproductibles pour faciliter les démonstrations et les tests.

Les mécanismes permettant de forcer un résultat doivent rester des outils de test, et non des fonctions publiques librement utilisables dans une véritable intégration de paiement.

#### F6 — Gestion des statuts

L'API doit enregistrer l'état de chaque transaction et empêcher les transitions incohérentes.

Les statuts envisagés au cours de la conception comprennent :

- `CREATED` : demande créée ;
- `AWAITING_CUSTOMER_ACTION` : attente de la décision du client ;
- `PROCESSING` : traitement en cours ou résultat non définitif (nom API de ce
  que les premières versions de ce document appelaient `PENDING` — un seul
  statut d'attente, pour ne pas en avoir deux qui veulent dire la même chose) ;
- `SUCCEEDED` : paiement simulé réussi ;
- `DECLINED_BY_CUSTOMER` : refus du client ;
- `REJECTED_BY_OPERATOR` : rejet de l'opérateur simulé ;
- `EXPIRED` : demande expirée ;
- `FAILED` : échec technique.

Cette liste est figée pour l'API (implémentée dans `app/models/statuses.py`). Les transitions autorisées le sont **aussi** : `ALLOWED_TRANSITIONS`, dans ce même module, décrit les seuls passages possibles et sert de contrôle unique dans `app/services/payments.py` (toute transition absente de la table → `409`). Un état terminal (`SUCCEEDED`, `DECLINED_BY_CUSTOMER`, `REJECTED_BY_OPERATOR`, `EXPIRED`, `FAILED`) n'a aucune sortie.

Un refus du client doit être distingué d'un rejet de l'opérateur. Un résultat en attente ne doit jamais être présenté comme un succès.

#### F7 — Consultation d'une transaction

Le site marchand doit pouvoir interroger l'API à partir de la référence d'une transaction.

La réponse fournit le statut courant et les informations utiles à son suivi.

Une référence inconnue doit entraîner une réponse d'erreur claire et structurée.

Cette opération est indispensable si une notification échoue ou si le marchand souhaite vérifier l'état d'une transaction.

#### F8 — Webhooks signés vers le site marchand

L'agrégateur doit envoyer un **webhook** (notification HTTP) au site marchand lors des changements de statut pertinents.

- payload JSON : `{event, reference, status, amount, occurred_at}` avec
  `event ∈ {transaction.succeeded, transaction.declined, transaction.failed}` ;
- en-tête **`X-3DPay-Signature` (HMAC)** pour prouver l'origine ;
- réponse attendue : **HTTP 2xx**, sinon **retry simulé ×5** journalisé ;
- **protection SSRF** : toute URL déclarée vers une adresse interne/privée est refusée ;
- le **journal des webhooks** (tentatives, codes HTTP) est visible dans le tableau de bord.

La livraison est simulée (pas de système externe réel), mais le mécanisme (signature, exigence 2xx, retry) est celui des vrais agrégateurs.

Le site marchand doit toujours pouvoir consulter l'état enregistré dans l'API, car un webhook peut échouer, être retardé ou être reçu plusieurs fois.

#### F9 — Idempotence

L'API doit prévoir un mécanisme permettant de prévenir les doubles traitements.

Par exemple, si le site marchand répète une requête à la suite d'un délai d'attente, cette répétition ne doit pas créer accidentellement plusieurs transactions pour une même opération logique.

La clé d'idempotence, sa durée de validité et les règles de comparaison des requêtes doivent être définies pendant la conception.

#### F10 — Authentification, validation et journalisation

Les appels API protégés doivent être authentifiés.

Les entrées doivent être validées avant tout traitement. Les événements importants et les erreurs doivent être journalisés afin de faciliter le diagnostic et le suivi des transactions.

Le mécanisme exact d'authentification des appels API reste à confirmer. Il ne faut pas confondre l'authentification technique du site marchand auprès de l'API avec une éventuelle authentification du client payeur.

#### F11 — Comptes utilisateurs (libre-service)

La plateforme est ouverte : un développeur peut **créer un compte** (inscription) puis **se connecter** pour accéder à son espace.

- inscription : nom, e-mail, mot de passe (haché, jamais en clair) ;
- connexion : ouvre une session vers l'espace personnel ;
- chaque utilisateur ne voit que **ses propres données** (comptes, clés, transactions, webhooks).

Ce compte est celui du **développeur / marchand**. Le client payeur, lui, n'a jamais de compte 3Dpay : il reste sur la boutique.

#### F12 — Gestion des clés API

À l'inscription (ou à la première génération), l'utilisateur reçoit **ses clés uniques** :

- une **clé publique** : identifiant du compte, affichable dans l'interface et côté client ;
- une **clé secrète** : utilisée pour authentifier les appels serveur → serveur, affichée **une seule fois**, **stockée hachée** (SHA-256), jamais journalisée.

Règles :
- les clés sont **propres à un utilisateur** ; un utilisateur ne peut ni voir ni utiliser les clés d'un autre ;
- régénération possible (l'ancienne clé est révoquée) ;
- aucun endpoint public ne doit permettre de créer un compte de marchand **sans** passer par l'inscription.

#### F13 — Opérateur fictif et numéros de test

Un **opérateur fictif** interne produit le résultat d'une transaction. Le résultat est choisi selon le **numéro de test** transmis dans la demande de paiement (le numéro fictif unique utilisé pour toutes les simulations).

Scénarios figés (publiés dans `docs/NUMEROS_DE_TEST.md`) :

| Numéro de test | Scénario simulé | Statut métier visé | `reason` |
|---|---|---|---|
| `01970000` | succès | `SUCCEEDED` | — |
| `01970001` | échec / refus opérateur | `REJECTED_BY_OPERATOR` | `OPERATOR_DECLINED` |
| `01970002` | solde insuffisant | `REJECTED_BY_OPERATOR` | `INSUFFICIENT_FUNDS` |
| `01970003` | attente (non définitif) | `PROCESSING` | — |
| numéro inconnu | refus par défaut : jamais un succès inventé | `REJECTED_BY_OPERATOR` | `INVALID_TEST_NUMBER` |

Deux modes coexistent :
- **mode contrôlé** : un scénario est forcé pour la démonstration (outil de test, pas une fonction publique d'intégration) ;
- **mode règles** : le résultat découle des règles ci-dessus, reproductibles et documentées.

Le choix de l'opérateur (MTN, Moov, Celtiis) reste fait **par le client sur le site marchand** ; il est transmis par le marchand à l'API.

#### F13 bis — Décision du client payeur

Le client payeur n'a **aucun compte** 3DPAY : sa décision ne peut donc pas
s'authentifier avec une clé de marchand ni avec une session.

À la création de la transaction, l'API remet un **`decision_token`** à usage
unique, affiché une seule fois et stocké haché (SHA-256). Le marchand le place
dans le lien de son widget ; la décision (`CONFIRM` / `DECLINE`) exige ce jeton.

- jeton invalide, déjà utilisé ou lié à une autre transaction → `401` ;
- transaction déjà traitée → `409` ;
- le jeton n'est jamais réaffiché par la consultation.

C'est l'équivalent simulé du lien de paiement d'un agrégateur réel : une preuve
limitée à **une** transaction et à **une** décision.

#### F14 — Tableau de bord

L'utilisateur suit son activité depuis un tableau de bord minimal :

- liste et détail de **ses** transactions ;
- **journal des webhooks** envoyés (statut, tentatives, réponses) ;
- **ses clés** (avec régénération) ;
- **réglages** (URL de webhook, informations du compte).

Le tableau de bord fait partie du MVP. Une interface d'administration complète (multi-tenancy avancée, remboursements, décaissements) reste hors périmètre.

### 3.2 Fonctionnalités secondaires

Un historique simple des transactions est couvert par le tableau de bord (F14).

Les remboursements, les décaissements et les intégrations réelles avec les opérateurs ne font pas partie du périmètre initial.

---

## 4. Parcours métier de référence

Le parcours principal est le suivant :

1. Le client choisit des produits sur le site marchand.
2. Le site marchand calcule le montant total de la commande.
3. Le client choisit son opérateur Mobile Money parmi les opérateurs proposés.
4. Le site marchand transmet la demande à l'API de l'agrégateur.
5. L'API valide la demande et crée une transaction identifiable par une référence.
6. Le client confirme ou refuse la demande dans le scénario de simulation.
7. Si le traitement est confirmé, le composant de l'opérateur simulé renvoie un résultat.
8. L'agrégateur enregistre le statut correspondant.
9. L'agrégateur renvoie une réponse API cohérente et envoie un webhook sign� au site marchand lorsqu'elle est nécessaire.
10. Si le marchand ne reçoit pas la notification ou souhaite vérifier le résultat, il consulte la transaction par sa référence.

Le système doit respecter la distinction entre la décision du client, le résultat de l'opérateur simulé et le statut enregistré par l'agrégateur.

---

## 5. Exigences non fonctionnelles

### Sécurité

- Authentifier les appels protégés.
- Valider les données entrantes.
- Ne jamais demander de véritable code secret Mobile Money.
- Ne pas exposer les secrets dans les réponses ou les journaux.
- Ne pas permettre qu'un mécanisme de simulation soit utilisé comme un véritable moyen de paiement.
- Chaque utilisateur ne voit que **ses propres données** (isolation stricte par compte).
- Clés secrètes **stockées hachées** (jamais en clair, jamais journalisées).
- **Limitation du débit** (rate limiting) contre les abus et les tentatives de force brute.
- Protection des webhooks contre les **adresses internes** (SSRF) : ne pas appeler d'URL privées/locales déclarées par l'utilisateur.
- Signature **HMAC** des webhooks pour prouver leur origine.
- Tout est marqué **« SIMULATION »** ; aucune donnée bancaire réelle n'est demandée ni stockée.

### Intégrité

- Garantir une référence de transaction stable et unique.
- Prévenir les doubles traitements.
- Contrôler les transitions entre statuts.
- Conserver la cohérence entre les réponses, les données enregistrées et les notifications.

### Fiabilité

- Gérer les erreurs de validation et les erreurs techniques.
- Distinguer un statut intermédiaire d'un résultat final.
- Permettre la consultation du statut même lorsque la notification échoue.
- Éviter les annonces de succès injustifiées.

### Traçabilité

- Enregistrer les événements utiles au suivi d'une transaction.
- Associer les événements à une référence lorsque cela est pertinent.
- Faciliter le diagnostic des erreurs sans enregistrer de données sensibles inutiles.

### Maintenabilité et testabilité

- Séparer la logique métier, les routes API, la persistance des données et les composants opérateurs simulés.
- Permettre l'ajout ou la modification d'un scénario sans réécrire toute l'application.
- Rendre les scénarios reproductibles et testables.

---

## 6. Architecture logique envisagée

L'architecture devra progressivement distinguer les composants suivants :

1. **API REST :** reçoit les requêtes HTTP, valide les entrées et renvoie les réponses JSON.
2. **Gestionnaire de transactions :** crée les références, conserve les transactions et contrôle les statuts.
3. **Orchestrateur de simulation :** organise le traitement et choisit le scénario applicable.
4. **Composants opérateurs simulés :** représentent séparément MTN Mobile Money, Moov Money et Celtiis Cash.
5. **Service de notification :** simule les notifications destinées au site marchand.
6. **Journalisation :** enregistre les événements utiles au suivi et au diagnostic.
7. **Couche de persistance :** permet de conserver les transactions au-delà du cycle de vie du serveur.

Cette architecture est une cible progressive. Avant de créer de nouveaux modules, il faut examiner la structure réelle du projet et adapter la conception à ce qui existe déjà.

---

## 7. Contrat général de l'API

Les opérations suivantes sont envisagées. Les routes indiquées sont des propositions de travail à vérifier avant de les figer.

| Fonction | Méthode indicative | Route indicative | Auth |
|---|---|---|---|
| Santé de l'API | GET | `/api/v1/health` | publique |
| Lister les opérateurs | GET | `/api/v1/operators` | publique |
| Inscription | POST | `/api/v1/auth/register` | publique |
| Connexion | POST | `/api/v1/auth/login` | publique |
| Régénérer mes clés | POST | `/api/v1/keys/rotate` | session |
| Créer une demande de paiement | POST | `/api/v1/payments` | clé API |
| Consulter une transaction | GET | `/api/v1/payments/{reference}` | clé API |
| Enregistrer la décision du client | POST | `/api/v1/payments/{reference}/decision` | jeton de décision |
| Mes transactions (tableau de bord) | GET | `/api/v1/dashboard/transactions` | session |
| Journal des webhooks | GET | `/api/v1/dashboard/webhooks` | session |
| Réglages webhook / compte | GET, PATCH | `/api/v1/dashboard/settings` | session |

Routes versionnées sous `/api/v1/`. Deux niveaux d'authentification distincts :
- **clé API** (`Authorization: Bearer <clé secrète>`) pour les appels serveur → serveur du marchand ;
- **session du compte** pour le tableau de bord (interface humaine, navigateur).

L'API doit utiliser des échanges JSON structurés.

Il faut distinguer deux notions :

- **Code HTTP :** indique le résultat de la requête HTTP.
- **Statut métier :** indique l'état de la transaction de paiement.

Par exemple, une demande peut être créée correctement et retourner HTTP `201 Created`, alors que la transaction reste au statut `CREATED` ou `PROCESSING` et attend encore la décision du client ou le résultat de l'opérateur.

Les codes HTTP ne doivent donc pas être utilisés comme substituts aux statuts métier.

La documentation interactive de FastAPI, notamment `/docs`, doit servir à tester et démontrer les opérations de l'API.

---

## 8. État actuel de l'apprentissage et de l'implémentation

Le projet a déjà commencé. Il ne faut pas le considérer comme une application entièrement vierge.

L'environnement de travail est Windows, avec Visual Studio Code.

Python est installé. FastAPI et Uvicorn ont été installés dans un environnement virtuel `.venv`.

Les éléments suivants ont déjà été abordés ou testés :

- création d'une application FastAPI dans `main.py` ;
- démarrage du serveur de développement ;
- utilisation de `/docs` ;
- utilisation de requêtes GET ;
- liste de paiements dans un fichier `paiements.py` ;
- consultation d'un paiement par identifiant ;
- gestion des réponses HTTP `200`, `404` et `422` ;
- création d'une opération POST retournant `201 Created` ;
- compréhension du fait qu'une liste Python conservée uniquement en mémoire est perdue lors du redémarrage du serveur.

**Point de vigilance :** le dernier problème rapporté pendant les exercices concernait une réponse `422`. Il faut examiner le code actuel et la requête qui provoque cette réponse avant de conclure à sa cause. Ne pas supposer que cette erreur est encore présente si le code a changé.

L'état exact des fichiers et des routes doit être vérifié dans le projet local avant toute modification.

---

## 9. Stratégie de développement

Le développement doit être progressif, avec une fonctionnalité testée avant de passer à la suivante.

Ordre de travail recommandé :

### Étape 1 — Audit du projet existant

- Examiner les fichiers et dossiers.
- Lire `main.py`, `paiements.py` et les autres fichiers présents.
- Vérifier l'environnement virtuel et les dépendances.
- Identifier les routes fonctionnelles et les éventuelles erreurs.
- Faire un état des lieux sans modifier immédiatement le code.

### Étape 2 — Stabilisation de l'API existante

- Corriger les erreurs actuelles.
- Vérifier les opérations GET et POST.
- Clarifier la structure des modèles de données.
- Tester les cas normaux et les erreurs de validation.

### Étape 3 — Modélisation du paiement

- Définir le modèle de transaction.
- Fixer les statuts et transitions nécessaires.
- Définir les champs obligatoires et facultatifs.
- Prévoir les références de transaction et de commande.

### Étape 4 — Gestion des opérateurs simulés

- Créer une représentation distincte des trois opérateurs.
- Implémenter les scénarios de résultat.
- Séparer le choix de l'opérateur de la logique de traitement.
- Intégrer la règle du **numéro de test unique** : un seul numéro fictif, quel que soit l'opérateur choisi, déclenche le scénario (succès, échec, solde insuffisant, attente).
- Documenter les numéros de test et leurs résultats.

### Étape 5 — Cycle de vie d'une transaction

- Créer une demande.
- Enregistrer la décision du client.
- Simuler le résultat opérateur.
- Enregistrer le statut final ou intermédiaire.
- Consulter la transaction par référence.

### Étape 6 — Persistance des données

- Remplacer progressivement le stockage uniquement en mémoire par une persistance adaptée.
- Évaluer le choix de la base de données selon les besoins du projet.
- Garantir la conservation des transactions après redémarrage.
- Tester les opérations de lecture et d'écriture.

Ne pas introduire une base de données complexe avant d'avoir expliqué son utilité et défini les besoins réels.

### Étape 7 — Comptes utilisateurs et clés API

- Inscription et connexion (mot de passe haché, session).
- Génération des clés : publique + secrète, affichée une seule fois, stockée hachée.
- Isolation : chaque utilisateur n'accède qu'à ses propres données.
- Régénération / révocation des clés.

### Étape 8 — Fiabilité et sécurité

- Implémenter l'idempotence.
- Ajouter l'authentification des appels protégés (clé API).
- Améliorer la validation.
- Ajouter la journalisation (sans secrets).
- Simuler les webhooks et leurs échecs (signature HMAC + retry).
- Ajouter la **limitation du débit** (rate limiting).
- Protéger les webhooks contre le **SSRF** (blocage des URL internes/privées).

### Étape 9 — Tableau de bord

- Transactions de l'utilisateur, journal des webhooks, gestion des clés, réglages.
- Aucune donnée d'un autre utilisateur n'est visible.

### Étape 10 — Tests et documentation

- Tester les scénarios de succès, de refus, d'attente et d'erreur.
- Vérifier les réponses HTTP et les statuts métier.
- Documenter les routes, les paramètres, les numéros de test et les exemples JSON.
- Préparer une démonstration complète à travers `/docs` et le tableau de bord.

Cet ordre est un plan de travail proposé. Il doit être ajusté après l'audit initial du code.

---

## 10. Critères de validation du MVP

Le MVP pourra être considéré comme démontrable lorsque les critères suivants seront satisfaits :

- Une demande valide peut être créée et possède une référence.
- La liste des trois opérateurs simulés est accessible.
- Les décisions de confirmation et de refus du client sont distinguées.
- Le traitement simulé peut produire plusieurs résultats.
- Le statut enregistré peut être consulté par référence.
- Les réponses HTTP sont cohérentes avec la nature des opérations.
- Les statuts métier restent cohérents au fil du traitement.
- Les requêtes répétées sont gérées par idempotence.
- Les notifications simulées ne sont pas l'unique moyen de connaître le résultat.
- Les appels protégés et les entrées sont contrôlés.
- Les événements importants sont retraçables.
- Les transactions sont conservées conformément à la stratégie de persistance retenue.
- Un développeur peut s'inscrire, se connecter et retrouver **ses** clés (la secrète n'est visible qu'une fois).
- Un utilisateur ne voit **jamais** les données ou les clés d'un autre utilisateur.
- Les numéros de test produisent les scénarios documentés (succès, échec, solde insuffisant, attente), quel que soit l'opérateur choisi.
- Un webhook est envoyé, signé (HMAC), journalisé, avec retry si le site ne répond pas en 2xx.
- Les webhooks vers des URL internes/privées sont rejetés (SSRF).
- La limitation du débit est active sur les routes sensibles.
- Le tableau de bord montre transactions, journal des webhooks, clés et réglages.
- L'ensemble est marqué « SIMULATION » et ne demande aucune donnée bancaire réelle.
- L'ensemble peut être démontré sans transfert d'argent réel ni accès privé aux opérateurs.

---

## 11. Consignes de collaboration destinées à OpenCode

Tu interviens comme assistant de développement sur un projet pédagogique réel. Le développeur apprend Python, les API REST et la conception logicielle en construisant progressivement l'application.

Respecte les consignes suivantes :

1. **Audite avant de modifier.** Lis les fichiers existants et présente un bref diagnostic avant les changements importants.
2. **Ne recommence pas à zéro sans raison.** Préserve le travail existant et évite les réécritures inutiles.
3. **Explique les décisions.** Pour chaque modification importante, indique le problème traité, le fichier concerné et la raison du choix technique.
4. **Procède par petites étapes.** Évite de créer toute l'application en une seule opération.
5. **Ne suppose pas que le code fonctionne.** Exécute ou propose des tests adaptés et présente leurs résultats réels.
6. **Ne masque pas les erreurs.** Explique les erreurs HTTP, les erreurs Python et les problèmes de validation avec des exemples compréhensibles.
7. **Respecte le périmètre.** N'ajoute pas de paiement réel, d'intégration privée d'opérateur ou de fonctionnalité hors MVP sans validation.
8. **Ne fixe pas silencieusement les points ouverts.** Propose une solution, explique les conséquences et demande une décision lorsque le choix influence fortement l'architecture.
9. **Protège les données.** Ne demande pas de codes secrets réels et ne place aucun secret dans le code source, les réponses ou les journaux.
10. **Privilégie la simplicité maîtrisée.** Choisis une solution adaptée au niveau actuel et explique les concepts nouveaux avant de les multiplier.
11. **Conserve une documentation cohérente.** Mets à jour les exemples, les routes et les instructions lorsque le contrat de l'API change.
12. **N'annonce pas une fonctionnalité comme terminée avant sa vérification.**

Pour chaque étape, adopte le format de travail suivant :

- Objectif de l'étape.
- Diagnostic ou fichiers concernés.
- Modification proposée et justification.
- Code complet des fichiers modifiés, lorsque nécessaire.
- Commandes exactes à exécuter dans le terminal Windows.
- Tests à effectuer et résultats attendus.
- Explication des notions nouvelles.
- Bilan de l'étape et prochaine action.

Évite de fournir simultanément un grand nombre de manipulations que le développeur ne peut pas encore vérifier. Termine les étapes pédagogiques par une vérification concrète avant de poursuivre.

---

## 12. Décisions encore à confirmer

**Décisions déjà actées** (ne pas les remettre en cause sans motif) :

- Stack technique : **Python + FastAPI + Uvicorn** (voir `analyse.md`).
- Libre-service : **inscription / connexion** et génération des clés par l'utilisateur (voir F11, F12).
- Trois opérateurs affichés, **un seul numéro de test** utilisé pour toutes les simulations (voir F13).
- **Tableau de bord minimal inclus** dans le MVP (voir F14).
- Webhook **signé (HMAC)** avec exigence de réponse 2xx et retry.
- Versionnage des routes sous `/api/v1/`.

**Points encore ouverts** — ne présente pas les éléments suivants comme définitivement arrêtés :

- La liste finale des statuts et les transitions autorisées.
- Les valeurs exactes des numéros de test et le scénario associé à chaque numéro.
- Le contrat définitif des routes et des réponses JSON.
- La forme technique des webhooks simulés (délai de retry, nombre de tentatives).
- La stratégie de nouvelle tentative des notifications.
- Les seuils de limitation du débit et les routes concernées en priorité.
- Le choix précis de la protection SSRF (liste noire d'URL ou résolution d'adresse).
- La représentation précise de la confirmation du client dans le parcours de démonstration.
- Le choix de la base de données en production.

Pour chaque point, explique les options pertinentes et recommande une solution simple, sécurisée et adaptée à une API de démonstration.

---

## 13. Première instruction à exécuter

Commence par **auditer le projet PaySim API existant**, sans effectuer de refonte ni de modification destructive.

1. Examine l'arborescence du projet et les fichiers Python existants.
2. Identifie les routes déjà implémentées.
3. Vérifie la structure des modèles et le mode de stockage actuel.
4. Repère les incohérences, les risques et les éventuelles erreurs, notamment autour de la dernière réponse HTTP `422` signalée pendant les tests.
5. Compare l'état actuel aux objectifs décrits dans ce document.
6. Présente un bilan clair en séparant :
   - ce qui existe et fonctionne ;
   - ce qui existe mais doit être corrigé ;
   - ce qui reste à développer.
7. Propose ensuite une seule prochaine étape prioritaire, avec une justification et un test de validation.

Attends que l'état du projet soit établi avant de décider d'une refonte ou d'ajouter de nombreux fichiers.

Le résultat recherché n'est pas seulement une API qui fonctionne : c'est un agrégateur de paiement simulé, cohérent, testable, documenté et compréhensible par la personne qui le développe.
