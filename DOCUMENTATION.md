# Documentation technique — ALBARKA App

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Problème résolu](#2-problème-résolu)
3. [Architecture générale](#3-architecture-générale)
4. [Stack technique](#4-stack-technique)
5. [Structure des fichiers](#5-structure-des-fichiers)
6. [Couche base de données](#6-couche-base-de-données)
7. [Couche API — FastAPI](#7-couche-api--fastapi)
8. [Couche métier — core/](#8-couche-métier--core)
9. [Frontend React](#9-frontend-react)
10. [Gestion des rôles et authentification](#10-gestion-des-rôles-et-authentification)
11. [Flux de données — exemples concrets](#11-flux-de-données--exemples-concrets)
12. [Lancer le projet](#12-lancer-le-projet)

---

## 1. Présentation du projet

ALBARKA App est un système de pilotage décisionnel conçu pour le réseau
**ALBARKA**, opérateur de services Mobile Money (MTN MoMo) au Cameroun.

L'application centralise et analyse les données d'activité de plusieurs
**commerciaux terrain** (DSM — District Sales Managers) qui gèrent chacun
un portefeuille d'agents POS (Points of Sale). Elle permet aux superviseurs
de suivre en temps réel les performances Cash In / Cash Out, la couverture
QR Code des agents, l'approvisionnement des commerciaux et leur réactivité
opérationnelle.

---

## 2. Problème résolu

Avant ce projet, le suivi des commerciaux ALBARKA se faisait manuellement :
fichiers Excel partagés par email, calculs dispersés, pas de vue consolidée,
pas d'historique centralisé.

Les problèmes concrets :
- Un superviseur ne pouvait pas savoir en temps réel quel commercial
  avait une faible activité ou était à risque d'inactivité QR.
- Les comparaisons mois par mois (MoM) nécessitaient des heures de
  manipulation Excel.
- L'identification des agents POS sans QR Code ou inactifs demandait
  un traitement manuel des exports MTN.
- Aucune traçabilité des fichiers importés ni de l'historique des
  indicateurs.

ALBARKA App résout ces problèmes en :
1. Centralisant l'import et le traitement des fichiers sources (CSV MTN,
   fichiers SAE, rapports QR Code).
2. Calculant automatiquement les indicateurs clés (taux de couverture,
   temps morts, classements, alertes seuils).
3. Offrant des dashboards interactifs accessibles selon le rôle de
   l'utilisateur (super admin, admin, commercial).
4. Conservant un historique complet des imports et des données calculées.

---

## 3. Architecture générale

```
┌─────────────────────────────────────────────────────────────┐
│                        NAVIGATEUR                           │
│  React 18 + TypeScript + Tailwind CSS + Recharts            │
│  http://localhost:5173                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / JSON (JWT dans Authorization)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   API REST — FastAPI                        │
│  Python 3.14 + Pydantic + JWT                               │
│  http://localhost:8000                                       │
│                                                             │
│  /auth/*     /cash/*    /qr/*                               │
│  /terrain/*  /gestion/* /import/*                           │
└───────────────────────┬─────────────────────────────────────┘
                        │ psycopg2
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 18                             │
│  Base : albarka                                             │
│  14 tables (utilisateurs, commerciaux, cashflow_pos, ...)   │
└─────────────────────────────────────────────────────────────┘

        ┌───────────────────────────────────────┐
        │  core/  — Couche métier Python         │
        │  Traitement des fichiers, calculs,     │
        │  accès base de données (db.py)         │
        └───────────────────────────────────────┘
                        ▲
                        │ utilisé par
              ┌─────────┴──────────┐
              │   api/             │
              │   (FastAPI)        │
              └────────────────────┘
```

---

## 4. Stack technique

### Backend

| Technologie | Version | Rôle |
|---|---|---|
| Python | 3.14 | Langage principal |
| FastAPI | 0.115+ | Framework API REST |
| Pydantic | 2.x | Validation des données / schémas |
| psycopg2-binary | 2.9.12 | Driver PostgreSQL |
| python-jose | 3.x | Génération et validation JWT |
| passlib / hashlib | — | Hashage SHA-256 des mots de passe |
| pandas | 2.x | Traitement des fichiers CSV / Excel |
| openpyxl | 3.x | Génération des classeurs Excel |
| python-multipart | 0.0.32 | Upload de fichiers multipart |
| python-dotenv | 1.x | Chargement des variables d'environnement |
| uvicorn | 0.x | Serveur ASGI |

### Base de données

| Technologie | Version | Rôle |
|---|---|---|
| PostgreSQL | 18 | Base de données principale |

### Frontend

| Technologie | Version | Rôle |
|---|---|---|
| React | 18 | Framework UI |
| TypeScript | 5.x | Typage statique |
| Vite | 5.x | Bundler |
| Tailwind CSS | 3.x | Styles utilitaires |
| Recharts | 2.x | Graphiques (barres, courbes) |
| React Router | 6.x | Routage SPA |
| Sonner | — | Notifications toast |
| Lucide React | — | Icônes |
| html-to-image | 1.11 | Export PNG des graphiques |

---

## 5. Structure des fichiers

```
albarka-app/
│
├── api/                    # Couche API FastAPI
│   ├── main.py             # Point d'entrée, CORS, routers
│   ├── auth.py             # POST /auth/login, GET /auth/me
│   ├── cash.py             # Endpoints Cash Flow
│   ├── qr.py               # Endpoints QR Code
│   ├── terrain.py          # Endpoints Terrain / Portefeuilles
│   ├── gestion.py          # Endpoints Administration / Imports
│   ├── import_tx.py        # POST /import/transactions
│   ├── import_qr.py        # POST /import/qr
│   ├── import_sae.py       # POST /import/sae
│   ├── import_pf.py        # POST /import/portefeuille
│   ├── deps.py             # Dépendances JWT (RequireAdmin, etc.)
│   └── schemas.py          # Modèles Pydantic de réponse
│
├── core/                   # Couche métier Python
│   ├── db.py               # Toutes les fonctions d'accès PostgreSQL
│   ├── cashflow.py         # Traitement fichiers SAE MTN
│   ├── transactions.py     # Nettoyage CSV, classeurs Excel, TCD
│   ├── qr_code.py          # Classification agents QR Code
│   ├── appro.py            # Appro / Déstockage
│   ├── comparaison.py      # Classeur comparatif QR Code
│   ├── metrics.py          # Calculs d'indicateurs
│   └── export.py           # Export Excel générique
│
├── frontend/               # Application React
│   └── 415c9753.../
│       └── src/
│           ├── pages/      # 17 pages React
│           ├── services/   # Clients API (terrain.ts, cash.ts, etc.)
│           ├── components/ # Composants réutilisables
│           ├── contexts/   # AuthContext, FiltresContext
│           ├── hooks/      # useAsync
│           └── types/      # Types TypeScript partagés
│
├── data/                   # Données persistantes
│   ├── qr_code/            # Rapports Excel + cache CSV QR
│   ├── transactions/       # Classeurs Excel générés
│   ├── comparatifs/        # Rapports comparatifs
│   └── albarka.db          # Ancienne base SQLite (backup)
│
├── scripts/
│   └── migrate_sqlite_to_pg.py  # Script de migration
│
├── .env                    # Variables d'environnement (JWT, DATABASE_URL)
└── requirements.txt        # Dépendances Python
```

---

## 6. Couche base de données

Toutes les interactions avec PostgreSQL passent par `core/db.py`. Ce fichier
expose 47 fonctions publiques qui couvrent l'ensemble des besoins de
persistance. Aucun autre fichier ne parle directement à la base.

### Tables principales

| Table | Rôle |
|---|---|
| `utilisateurs` | Comptes de connexion (super_admin, admin, commercial) |
| `commerciaux` | Agents terrain DSM (District Sales Managers) |
| `aliases_commerciaux` | Nom du compte propre du commercial dans les CSV MTN |
| `pos` | Points de vente (agents terrain, source fichier SAE) |
| `cashflow_pos` | Cash In / Cash Out par POS × mois (source SAE) |
| `transactions_momo` | Agrégats historiques (compatibilité v1) |
| `appro` | Approvisionnements et déstockages par commercial × date |
| `clients_servis` | Contreparties des transactions par commercial × date |
| `portefeuilles` | Portefeuilles clients par commercial |
| `clients` | Clients d'un portefeuille (MSISDN + profil POS) |
| `seuils` | Seuils d'alerte Cash In / Cash Out configurables |
| `parrainages` | Saisie manuelle des parrainages MoMo App |
| `suivi_personnes` | Suivi manuel de personnes spécialement suivies |
| `imports` | Historique de tous les fichiers traités |

### Règles de cohérence

- Toutes les écritures utilisent `INSERT ... ON CONFLICT DO UPDATE`
  (upsert) — un re-traitement du même fichier écrase silencieusement
  l'ancien enregistrement sans créer de doublons.
- Les clés étrangères sont activées (FK constraints PostgreSQL natif).
- Les séquences SERIAL sont remises à jour après toute migration.

---

## 7. Couche API — FastAPI

L'API est documentée interactivement à `http://localhost:8000/docs`
(Swagger UI) et `http://localhost:8000/redoc` (ReDoc).

### Authentification

Toutes les routes protégées attendent le header :
```
Authorization: Bearer <JWT>
```

Le JWT est obtenu via `POST /auth/login` et est valide 480 minutes
(configurable via `JWT_EXPIRE_MINUTES` dans `.env`).

### Niveaux d'accès

| Niveau | Rôle requis | Decorator FastAPI |
|---|---|---|
| Tous les utilisateurs connectés | commercial, admin, super_admin | `RequireAll` |
| Administration | admin, super_admin | `RequireAdmin` |
| Super administration | super_admin uniquement | `RequireSuperAdmin` |

---

### Module Auth — `/auth`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Connexion. Body : `{username, mot_de_passe}`. Retourne `{utilisateur, token}` |
| `GET` | `/auth/me` | Tous | Profil de l'utilisateur connecté depuis son JWT |

---

### Module Cash Flow — `/cash`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `GET` | `/cash/commercial` | Admin | Cash In/Out par commercial pour un mois (`?mois=AAAA-MM`) |
| `GET` | `/cash/commercial/evolution` | Admin | Évolution mensuelle réseau (courbe multi-mois) |
| `GET` | `/cash/alertes-commercial` | Admin | Commerciaux dépassant les seuils configurés |
| `GET` | `/cash/pos` | Admin | Cashflow détaillé de tous les POS pour un mois |
| `GET` | `/cash/pos/classement` | Admin | Top N et Flop N des POS (`?mois&flux=cash_in&n=15`) |
| `GET` | `/cash/pos/alertes` | Admin | POS dépassant les seuils |
| `POST` | `/cash/pos/mom` | Admin | Comparaison multi-mois POS. Body : liste de mois |
| `GET` | `/cash/appro` | Tous | Appro/déstockage par commercial (`?mois&commercial_id`) |
| `GET` | `/cash/appro/evolution` | Tous | Évolution mensuelle appro réseau |
| `GET` | `/cash/appro/detail` | Tous | Détail journalier appro avec nom du commercial |
| `GET` | `/cash/mom` | Tous | Comparaison mois M vs M-1 (cash commercial) |
| `GET` | `/cash/appro/mom` | Tous | Comparaison M vs M-1 (appro/déstockage) |

---

### Module QR Code — `/qr`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `GET` | `/qr/dates` | Tous | Dates disponibles dans le cache QR |
| `GET` | `/qr/repartition` | Tous | Agents + métriques pour une date (`?date_ref&dsm_name&segment_group`) |
| `GET` | `/qr/segments` | Tous | Répartition par segment (HVC / MVC / LVC) |
| `GET` | `/qr/dsm` | Admin | Classement DSM par agents actifs |
| `GET` | `/qr/agents` | Tous | Liste complète filtrée (`?segment_group&statut&dsm_name`) |
| `GET` | `/qr/prioritaires` | Tous | Agents non actifs à traiter |
| `GET` | `/qr/comparaison` | Admin | Mouvements de statuts entre deux dates |
| `GET` | `/qr/mom` | Tous | Évolution des KPIs QR entre deux dates |

---

### Module Terrain — `/terrain`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `GET` | `/terrain/points-touches` | Tous | Synthèse + détail des points touchés par commercial |
| `GET` | `/terrain/clients-servis` | Tous | Contreparties servies (`?commercial_id&du&au`) |
| `GET` | `/terrain/reactivite` | Admin | Indicateurs agrégés depuis la base |
| `POST` | `/terrain/reactivite/calcul` | Admin | Calcul complet depuis CSV bruts uploadés |
| `GET` | `/terrain/portefeuilles` | Tous | Liste des portefeuilles (`?commercial_id`) |
| `GET` | `/terrain/portefeuilles/{id}/clients` | Tous | Clients d'un portefeuille |
| `POST` | `/terrain/portefeuilles/{id}/couverture` | Tous | Calcul couverture depuis CSV bruts |

---

### Module Gestion / Administration — `/gestion`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `GET` | `/gestion/imports` | Admin | Historique des imports (`?type_fichier&limite&offset`) |
| `GET` | `/gestion/imports/total` | Admin | Nombre total d'imports |
| `DELETE` | `/gestion/imports/{id}` | Admin | Supprime l'enregistrement (pas le fichier disque) |
| `GET` | `/gestion/imports/{id}/download` | Admin | Télécharge le fichier Excel généré |
| `GET` | `/gestion/parrainages` | Tous | Liste + synthèse des parrainages (`?du&au`) |
| `POST` | `/gestion/parrainages` | Tous | Saisir ou cumuler des parrainages |
| `DELETE` | `/gestion/parrainages/{personne}/{date}` | Admin | Supprimer un enregistrement |
| `GET` | `/gestion/suivi-personnes` | Tous | Suivi des personnes spécialement suivies |
| `POST` | `/gestion/suivi-personnes` | Tous | Nouvelle entrée de suivi |
| `DELETE` | `/gestion/suivi-personnes/{id}` | Admin | Supprimer une entrée |
| `GET` | `/gestion/utilisateurs` | Admin | Liste des comptes utilisateurs |
| `POST` | `/gestion/utilisateurs` | SuperAdmin | Créer un compte |
| `PATCH` | `/gestion/utilisateurs/{id}` | Admin | Modifier nom / état actif |
| `GET` | `/gestion/commerciaux` | Admin | Liste des commerciaux avec alias |
| `PATCH` | `/gestion/commerciaux/{id}` | Admin | Modifier téléphone, zone, alias, état |
| `GET` | `/gestion/seuils` | Admin | Liste des seuils cash configurés |
| `POST` | `/gestion/seuils` | Admin | Créer ou modifier un seuil |

---

### Module Import — `/import`

| Méthode | Route | Accès | Description |
|---|---|---|---|
| `POST` | `/import/transactions` | SuperAdmin | Upload CSV MTN → nettoyage + classeur Excel + clients servis + appro |
| `POST` | `/import/qr` | SuperAdmin | Upload XLSX/GZ QR Code → classification + cache CSV + rapport Excel |
| `POST` | `/import/sae` | SuperAdmin | Upload SAE MTN (.xlsx ou .csv) → upsert POS + cashflow_pos |
| `POST` | `/import/portefeuille` | SuperAdmin | Upload XLSX ALBARKA → création portefeuille + clients |

Tous ces endpoints acceptent les fichiers en `multipart/form-data`.

---

## 8. Couche métier — core/

La couche `core/` contient toute la logique de traitement indépendante
du framework API.

### `core/db.py`
Unique point d'accès à PostgreSQL. 47 fonctions couvrant l'ensemble
des opérations CRUD sur les 14 tables. Utilise psycopg2 avec
`RealDictCursor` pour retourner des `dict` Python natifs.

### `core/cashflow.py`
Traitement des fichiers SAE MTN (Cash Flow POS). Fonctions clés :
- `read_sae_file()` — lecture robuste XLSX ou CSV avec détection
  automatique des colonnes.
- `import_sae_file()` — upsert POS + cashflow_pos en base.
- `_detect_mois_from_filename()` — détection du mois depuis le nom
  du fichier (patterns : `JUILLET_2026`, `2026_07`, `2026-07`).

### `core/transactions.py`
Pipeline de traitement des CSV bruts MTN :
- `clean_transactions()` — filtre `Type=Transfer`, exclut les comptes
  ALBARKA GN SARL, réduit la date à la journée.
- `build_transactions_workbook()` — classeur Excel 3 onglets :
  Données nettoyées, TCD-From Name, TCD-To Name.
- `extract_clients_servis()` — identifie les contreparties du
  commercial depuis les colonnes From/To.
- `extract_appro_from_workbook()` — lit les onglets TCD du classeur
  pour extraire les montants d'appro et de déstockage.

### `core/qr_code.py`
Classification des agents QR Code :
- `read_qr_file()` — lit `.xlsx` ou `.gz` compressé.
- `classify()` — attribue un statut à chaque agent :
  - **Sans QR Code** : `active_deployed` vide
  - **QR non utilisé (+30j)** : `active_30 == 0`
  - **Risque inactivité** : dernière utilisation entre 20 et 29 jours
  - **Actif** : sinon
- `build_report_workbook()` — classeur Excel 10 onglets
  (Résumé + 9 onglets détaillés par segment × statut).

### `core/appro.py`
Lecture et écriture des données d'approvisionnement/déstockage.
`import_appro_from_workbook()` délègue à `core/transactions.py`
pour extraire les lignes depuis les TCD du classeur transactions.

### `core/comparaison.py`
Génère le rapport comparatif Excel entre deux dates QR Code :
rapprochement par `pos_msisdn`, calcul des mouvements de statuts,
tableau de synthèse et détail des agents ayant changé de catégorie.

---

## 9. Frontend React

### Organisation

```
src/
├── pages/          # 17 pages (une par route)
├── services/       # 7 fichiers de service (appels API)
│   ├── api.ts      # Client HTTP centralisé (fetch + JWT)
│   ├── auth.ts     # POST /auth/login, session
│   ├── cash.ts     # Endpoints /cash/*
│   ├── qr.ts       # Endpoints /qr/*
│   ├── terrain.ts  # Endpoints /terrain/*
│   ├── gestion.ts  # Endpoints /gestion/*
│   └── import.ts   # Endpoints /import/*
├── components/     # Composants réutilisables
│   ├── charts/     # ChartWrapper, Charts (Recharts)
│   ├── dashboard/  # SectionCash, SectionQr, SectionAppro, SectionReactivite
│   ├── layout/     # AppLayout, Sidebar, PageHeader
│   └── ui/         # Button, DataTable, Tabs, States, Field, etc.
├── contexts/
│   ├── AuthContext.tsx    # Session JWT, rôle, commercial courant
│   └── FiltresContext.tsx # Filtres partagés (mois, date QR)
├── hooks/
│   └── useAsync.ts   # Hook de chargement asynchrone avec état
└── types/
    └── index.ts      # Types TypeScript partagés
```

### Client HTTP centralisé (`src/services/api.ts`)

Toutes les requêtes passent par un objet `api` qui :
1. Lit `VITE_API_URL` depuis les variables d'environnement Vite
   (défaut : `http://localhost:8000`)
2. Injecte automatiquement le JWT depuis `sessionStorage`
3. Lève une `ApiError` typée si la réponse HTTP n'est pas 2xx
4. Expose `api.get<T>()`, `api.post<T>()`, `api.patch<T>()`,
   `api.del()` et `api.upload<T>()` (multipart)

### Hook `useAsync`

```typescript
const donnees = useAsync(() => getReactivite(), [dependances]);
// donnees.donnees  → résultat (ou null)
// donnees.chargement → boolean
// donnees.erreur   → string | null
// donnees.recharger() → reexécute la promesse
```

### Pages et leur rôle

| Page | Route | Accès | Description |
|---|---|---|---|
| `Login.tsx` | `/login` | Public | Formulaire de connexion. POST /auth/login → JWT stocké en sessionStorage |
| `Accueil.tsx` | `/` | Tous | Page d'accueil avec résumé du réseau et accès rapide aux modules |
| `DashboardGlobal.tsx` | `/dashboard` | Admin | Vue consolidée : métriques Cash, QR Code, Appro et Réactivité réseau |
| `DashboardQr.tsx` | `/dashboard-qr` | Admin | Dashboard QR Code détaillé : répartition par statut, segment, DSM |
| `MonDashboard.tsx` | `/mon-dashboard` | Commercial | Dashboard personnel du commercial connecté : ses indicateurs uniquement |
| `CashFlow.tsx` | `/cash-flow` | Admin | Import fichiers SAE, classements Top/Flop POS, alertes seuils, MoM |
| `Transactions.tsx` | `/transactions` | Tous | Import CSV MTN, classeurs Excel, points touchés, clients servis |
| `SuiviQrCode.tsx` | `/suivi-qr` | SuperAdmin | Import fichier QR Code, classification, téléchargement du rapport |
| `DashboardQr.tsx` | `/dashboard-qr` | Admin | Répartition agents par statut / segment / DSM, onglets HVC/MVC/LVC |
| `EtudeComparative.tsx` | `/etude-comparative` | Admin | Comparaison deux dates QR Code : mouvements de statuts |
| `ComparaisonsMoM.tsx` | `/comparaisons-mom` | Admin | Cash MoM, Appro MoM, QR MoM sur périodes sélectionnées |
| `ApproDestockage.tsx` | `/appro-destockage` | Tous | Consultation historique appro/déstockage par commercial et par mois |
| `Portefeuilles.tsx` | `/portefeuilles` | Tous | Import portefeuilles clients, consultation, calcul de couverture terrain |
| `Historique.tsx` | `/historique` | Admin | Historique de tous les fichiers importés avec téléchargement |
| `Reactivite.tsx` | `/reactivite` | Admin | Calcul des temps morts et de recharge depuis CSV bruts MTN |
| `MomoApp.tsx` | `/momo-app` | Tous | Saisie manuelle des parrainages MoMo App |
| `SuiviPersonnes.tsx` | `/suivi-personnes` | Tous | Suivi manuel de personnes spécialement suivies |
| `Administration.tsx` | `/administration` | Admin | Gestion utilisateurs, commerciaux, aliases CSV, seuils |

### Graphiques

Tous les graphiques (`BarresHorizontales`, `BarresGroupees`,
`BarresEmpilees`, `CourbeEvolution`) sont enveloppés dans un
`ChartWrapper` qui ajoute :
- Boutons zoom + / − / reset (CSS `transform: scale`)
- Bouton téléchargement PNG (extraction SVG → canvas → fichier)

---

## 10. Gestion des rôles et authentification

### Trois rôles

| Rôle | Description | Peut importer | Voit tout le réseau | Administration |
|---|---|---|---|---|
| `super_admin` | Superviseur général | ✅ | ✅ | ✅ |
| `admin` | Responsable | ✅ consultation seule | ✅ | Partielle |
| `commercial` | Agent terrain DSM | ❌ | ❌ (son périmètre uniquement) | ❌ |

### Flux d'authentification

```
1. POST /auth/login { username, mot_de_passe }
        ↓
2. db.authenticate_user() vérifie SHA-256(mot_de_passe) == password_hash
        ↓
3. Création JWT signé avec JWT_SECRET_KEY (payload: user_id, username, role)
        ↓
4. Frontend stocke { utilisateur, token } dans sessionStorage
        ↓
5. Chaque requête injecte : Authorization: Bearer <token>
        ↓
6. deps.py valide le JWT et injecte l'utilisateur dans la dépendance FastAPI
```

### Persistance de session

La session survit à la navigation (sessionStorage) mais expire quand
l'onglet est fermé ou au bout de 480 minutes (configurable). Un
redémarrage d'uvicorn ne casse plus la session grâce à la clé JWT
fixe dans `.env`.

---

## 11. Flux de données — exemples concrets

### Import d'un fichier CSV Transactions

```
Utilisateur dépose PARFAIT(7).csv
        ↓
POST /import/transactions (multipart)
        ↓
api/import_tx.py :
  1. clean_transactions() → 4200 lignes après filtrage
  2. build_transactions_workbook() → classeur Excel 3 onglets sauvé sur disque
  3. Identification "PARFAIT" dans le nom → commercial_id = 1
  4. alias_csv = "ALBARKA 135"
  5. extract_clients_servis(df, "ALBARKA 135") → 312 contreparties
  6. db.save_clients_servis(1, contreparties)
  7. extract_appro_from_workbook(chemin, "ALBARKA 135") → 28 entrées
  8. INSERT INTO appro ... ON CONFLICT DO UPDATE
  9. db.save_import("transactions", "PARFAIT(7)", ...)
        ↓
Réponse JSON : { id_import, fichier, nb_lignes, commercial, alias, nb_clients_servis, appro_ok }
        ↓
Frontend affiche le résumé + bouton "Télécharger le classeur Excel"
```

### Consultation du Dashboard QR Code

```
Frontend : useAsync(() => getRepartitionQr("2026-08-26", undefined, "1-HVC"))
        ↓
GET /qr/repartition?date_ref=2026-08-26&segment_group=1-HVC
        ↓
api/qr.py :
  1. _load_cache("2026-08-26") → lit data/qr_code/_cache/2026-08-26.csv
  2. Filtre df[df["segment_group"] == "1-HVC"]
  3. [_agent_to_out(row) for row in df] → liste QrAgentOut
  4. _calc_repartition(agents) → taux déploiement, utilisation, etc.
        ↓
Réponse JSON : { agents: [...], repartition: { total, parStatut, taux... } }
        ↓
Frontend affiche métriques + graphiques + tableau filtrable
```

### Calcul de réactivité depuis CSV bruts

```
Utilisateur dépose STEPHANE(7).csv + PARFAIT(7).csv
        ↓
POST /terrain/reactivite/calcul (multipart, 2 fichiers)
        ↓
api/terrain.py :
  Pour chaque fichier :
  1. pd.read_csv() → DataFrame
  2. Filtrage Status=Successful, Type=Transfer
  3. get_alias_map() → {"ALBARKA 85": {commercial_id, dsm_name}}
  4. Recherche de l'alias dans From name / To name
  5. _compute_reactivity_raw(df, "ALBARKA 85") :
     - Temps mort : écarts en minutes entre tx consécutives le même jour
     - Temps recharge : durée pour repasser au-dessus de 100 000 FCFA de balance
        ↓
Réponse JSON : liste ReactiviteOut avec tempsMortMedian, tempsRechargeMedian...
        ↓
Frontend persiste dans sessionStorage → survit à la navigation
```

---

## 12. Lancer le projet

### Prérequis

- Python 3.14+ avec le venv activé (`.venv/`)
- Node.js 20+ (installé via nvm)
- PostgreSQL 18 en cours d'exécution
- Variables dans `.env` :
  ```
  DATABASE_URL=postgresql:///albarka?host=/var/run/postgresql
  JWT_SECRET_KEY=<clé-secrète>
  JWT_EXPIRE_MINUTES=480
  CORS_ORIGINS=http://localhost:5173,http://localhost:3000
  ```

### Terminal 1 — Backend

```bash
cd /home/giovanni/Documents/stage/albarka-app
source .venv/bin/activate
python3 -m uvicorn api.main:app --reload --port 8000
```

### Terminal 2 — Frontend

```bash
cd /home/giovanni/Documents/stage/albarka-app/frontend/415c9753-5c44-4cf2-a60c-6f9a9c24385d
npm run dev
```

### Accès

| URL | Description |
|---|---|
| `http://localhost:5173` | Application React (interface principale) |
| `http://localhost:8000/docs` | Documentation Swagger interactive de l'API |
| `http://localhost:8000/redoc` | Documentation ReDoc de l'API |
| `http://localhost:8000/health` | Healthcheck de l'API |

### Comptes par défaut

| Username | Mot de passe | Rôle |
|---|---|---|
| `giovanni` | `sadmin123` | super_admin |
| `theo` | `admin123` | admin |
| `parfait` | `parfait123` | commercial |
| `stephane` | `stephane123` | commercial |
| `antoine` | `antoine123` | commercial |
| `erve` | `erve123` | commercial |
| `ewane` | `ewane123` | commercial |

### Première migration SQLite → PostgreSQL

Si une base SQLite existante doit être migrée :

```bash
source .venv/bin/activate
python3 scripts/migrate_sqlite_to_pg.py
```

---

*Documentation générée le 2 septembre 2026.*
