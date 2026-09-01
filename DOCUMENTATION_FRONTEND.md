# ALBARKA — Documentation technique pour refonte frontend

## 1. Contexte du projet

ALBARKA est une application de **pilotage décisionnel** pour un Super Agent Mobile Money (partenaire MTN Cameroun). Elle centralise et visualise les données du réseau d'agents terrain répartis sur le territoire camerounais.

L'application actuelle est construite en **Python/Streamlit**. Cette documentation décrit l'ensemble du système pour permettre la création d'un nouveau frontend (React, Vue.js, Next.js, etc.) connecté à une API backend Python (FastAPI recommandé).

---

## 2. Charte graphique

| Couleur | Code HEX | Usage |
|---|---|---|
| Jaune ALBARKA | `#F5A623` | Boutons principaux, accents, bordures actives, highlights |
| Jaune foncé (hover) | `#E0950F` | Hover des boutons |
| Noir | `#1A1A1A` | Textes, titres, sidebar |
| Blanc | `#FFFFFF` | Fonds, cartes |
| Gris clair | `#F8F9FA` | Fonds secondaires, séparations |
| Gris moyen | `#E9ECEF` | Bordures, dividers |

**Logo** : losange stylisé jaune/noir + texte "ALBARKA" bold + tagline "SUPER AGENT MOBILE MONEY". Disponible en SVG dans `assets/logo_albarka.svg`.

**Sidebar** : fond noir (`#1A1A1A`), bordure droite jaune (`#F5A623`), textes blancs, lien actif sur fond jaune avec texte noir.

---

## 3. Authentification et rôles

### Système d'authentification
- Hash SHA-256 des mots de passe (pas de dépendance externe)
- Session stockée côté client (JWT recommandé pour le nouveau frontend)
- **Règle absolue** : avant connexion, aucune page ni navigation n'est visible — seulement le formulaire de login

### Trois rôles utilisateurs

#### `super_admin`
- Accès total à toutes les fonctionnalités
- Seul à pouvoir **déposer des fichiers** (CSV, SAE, portefeuilles)
- Seul à pouvoir **saisir des données manuellement** (parrainages, suivi personnes)
- Gestion des utilisateurs, aliases, seuils
- Peut voir toutes les données de tous les commerciaux

#### `admin`
- **Consultation et export uniquement** — jamais de saisie ni de dépôt
- Accès aux dashboards, classements, historique, portefeuilles, appro/destockage, MoM, réactivité
- Ne voit pas les pages : Transactions (import), Suivi QR Code, Administration, MoMo App, Suivi Personnes

#### `commercial`
- Vue filtrée sur **ses données uniquement** (identifié par son `dsm_name`)
- Accès à : Mon Dashboard, Comparaisons MoM (ses données filtrées)
- Ne voit aucune donnée d'un autre commercial

### Comptes par défaut (seed)
| Username | Rôle | Mot de passe |
|---|---|---|
| giovanni | super_admin | sadmin123 |
| theo | admin | admin123 |
| parfait | commercial | parfait123 |
| stephane | commercial | stephane123 |
| antoine | commercial | antoine123 |
| erve | commercial | erve123 |
| ewane | commercial | ewane123 |
| franck | commercial | franck123 |
| prosper | commercial | prosper123 |
| cesaire | commercial | cesaire123 |

---

## 4. Modèle de données (PostgreSQL cible)

### Tables

#### `utilisateurs`
```sql
id            SERIAL PRIMARY KEY
username      TEXT UNIQUE NOT NULL
nom           TEXT NOT NULL
role          TEXT NOT NULL  -- 'super_admin' | 'admin' | 'commercial'
password_hash TEXT NOT NULL  -- SHA-256
actif         INTEGER DEFAULT 1
created_at    TIMESTAMP DEFAULT NOW()
```

#### `commerciaux`
```sql
id             SERIAL PRIMARY KEY
utilisateur_id INTEGER REFERENCES utilisateurs(id)
dsm_name       TEXT UNIQUE NOT NULL  -- ex: 'PARFAIT', 'ANTOINE'
telephone      TEXT
zone           TEXT
actif          INTEGER DEFAULT 1
```

#### `aliases_commerciaux`
```sql
id            SERIAL PRIMARY KEY
commercial_id INTEGER REFERENCES commerciaux(id)
alias         TEXT NOT NULL   -- ex: 'ALBARKA 135' pour PARFAIT
actif         INTEGER DEFAULT 1
created_at    TIMESTAMP DEFAULT NOW()
UNIQUE(commercial_id)
```

**Mapping aliases actuel :**
| Commercial | Alias CSV |
|---|---|
| PARFAIT | ALBARKA 135 |
| STEPHANE | ALBARKA 85 |
| ANTOINE | ALBARKA 72 |
| ERVE | ALBARKA 89 |
| EWANE | ALBARKA 71 |
| FRANCK | — (aucun) |
| PROSPER | — (aucun) |
| CESAIRE | — (aucun) |

#### `imports`
```sql
id             SERIAL PRIMARY KEY
type_fichier   TEXT NOT NULL  -- 'qr_code' | 'transactions' | 'comparatif'
cle            TEXT NOT NULL  -- identifiant unique du traitement
date_donnees   TEXT
chemin_fichier TEXT NOT NULL  -- chemin vers le fichier Excel généré
nb_lignes      INTEGER
date_execution TIMESTAMP
UNIQUE(type_fichier, cle)
```

#### `seuils`
```sql
id         SERIAL PRIMARY KEY
type_flux  TEXT NOT NULL  -- 'cash_in' | 'cash_out'
valeur     REAL NOT NULL
mois       TEXT           -- NULL = seuil global, sinon 'AAAA-MM'
created_by INTEGER REFERENCES utilisateurs(id)
created_at TIMESTAMP DEFAULT NOW()
UNIQUE(type_flux, mois)
```

#### `portefeuilles`
```sql
id            SERIAL PRIMARY KEY
commercial_id INTEGER REFERENCES commerciaux(id)
nom           TEXT NOT NULL
date_import   TEXT NOT NULL
nb_clients    INTEGER DEFAULT 0
```

#### `clients`
```sql
id              SERIAL PRIMARY KEY
portefeuille_id INTEGER REFERENCES portefeuilles(id) ON DELETE CASCADE
nom             TEXT
telephone       TEXT   -- MSISDN du client (clé de rapprochement)
localite        TEXT   -- profil POS (ex: 'MTNC Merchant Account Profile')
```

#### `clients_servis`
```sql
id                  SERIAL PRIMARY KEY
commercial_id       INTEGER REFERENCES commerciaux(id)
date_op             TEXT NOT NULL       -- AAAA-MM-JJ
nom_contrepartie    TEXT
msisdn_contrepartie TEXT NOT NULL
nb_transactions     INTEGER DEFAULT 1
source_fichier      TEXT
created_at          TIMESTAMP DEFAULT NOW()
UNIQUE(commercial_id, date_op, msisdn_contrepartie)
```

#### `appro`
```sql
id            SERIAL PRIMARY KEY
commercial_id INTEGER REFERENCES commerciaux(id)
date_op       TEXT NOT NULL   -- AAAA-MM-JJ
type_op       TEXT NOT NULL   -- 'appro' | 'destockage'
nb_ops        INTEGER DEFAULT 0
montant       REAL NOT NULL
source_fichier TEXT
created_at    TIMESTAMP DEFAULT NOW()
UNIQUE(commercial_id, date_op, type_op)
```

#### `pos` (agents terrain, source fichier SAE MTN)
```sql
id           SERIAL PRIMARY KEY
acceptorid   TEXT UNIQUE NOT NULL
agent_msisdn TEXT
agent_name   TEXT
created_at   TIMESTAMP DEFAULT NOW()
```

#### `cashflow_pos` (cash in/out source SAE MTN)
```sql
id             SERIAL PRIMARY KEY
pos_id         INTEGER REFERENCES pos(id)
mois           TEXT NOT NULL   -- 'AAAA-MM'
cash_in        REAL DEFAULT 0   -- commission cash in (cash_in_com dans le SAE)
cash_out       REAL DEFAULT 0   -- commission cash out (cash_out_com dans le SAE)
source_fichier TEXT
created_at     TIMESTAMP DEFAULT NOW()
UNIQUE(pos_id, mois)
```

#### `parrainages`
```sql
id         SERIAL PRIMARY KEY
personne   TEXT NOT NULL   -- nom de la personne suivie
date_op    TEXT NOT NULL   -- AAAA-MM-JJ
nb         INTEGER DEFAULT 0
created_at TIMESTAMP DEFAULT NOW()
UNIQUE(personne, date_op)
```

#### `suivi_personnes`
```sql
id            SERIAL PRIMARY KEY
commercial_id INTEGER REFERENCES commerciaux(id)
nom_personne  TEXT NOT NULL
montant       REAL DEFAULT 0
date_heure    TEXT NOT NULL   -- 'AAAA-MM-JJ HH:MM:SS'
created_at    TIMESTAMP DEFAULT NOW()
```

#### `transactions_momo` (legacy — données historiques cash in/out par commercial)
```sql
id              SERIAL PRIMARY KEY
commercial_id   INTEGER REFERENCES commerciaux(id)
mois            TEXT NOT NULL
cash_in         REAL DEFAULT 0
cash_out        REAL DEFAULT 0
nb_transactions INTEGER DEFAULT 0
source_fichier  TEXT
created_at      TIMESTAMP DEFAULT NOW()
UNIQUE(commercial_id, mois)
```

---

## 5. Pages et fonctionnalités

### Navigation par rôle

| Page | super_admin | admin | commercial |
|---|:---:|:---:|:---:|
| Accueil | ✅ | ✅ | ✅ |
| Dashboard Global | ✅ | ✅ | ❌ |
| Transactions | ✅ | ❌ | ❌ |
| Suivi QR Code | ✅ | ❌ | ❌ |
| Étude Comparative | ✅ | ✅ | ❌ |
| Historique | ✅ | ✅ | ❌ |
| Cash Flow | ✅ | ✅ | ❌ |
| Dashboard QR Code | ✅ | ✅ | ❌ |
| Portefeuilles | ✅ | ✅ (consult.) | ❌ |
| Appro / Destockage | ✅ | ✅ | ✅ (ses données) |
| Comparaisons MoM | ✅ | ✅ | ✅ (ses données) |
| Réactivité Commerciale | ✅ | ✅ | ❌ |
| MoMo App (Parrainages) | ✅ | ❌ | ❌ |
| Suivi Personnes | ✅ | ❌ | ❌ |
| Administration | ✅ | ❌ | ❌ |
| Mon Dashboard | ❌ | ❌ | ✅ |

---

### Page : Accueil
**Rôles** : tous  
**Description** : Page d'accueil après connexion. Affiche la liste des modules disponibles pour le rôle connecté avec leur description. Pas de données dynamiques — uniquement informatif.

---

### Page : Dashboard Global
**Rôles** : super_admin, admin  
**Description** : Vue consolidée de toutes les performances du réseau.

**Sections** :
1. **Cartes de synthèse** (6 métriques) — filtrées par mois (sidebar)
   - Total transactions MoMo du mois sélectionné
   - Cash In réseau (FCFA) avec delta vs mois précédent
   - Cash Out réseau (FCFA) avec delta vs mois précédent
   - Agents QR actifs / total (date QR sélectionnée)
   - Total appros réseau (FCFA)
   - Total destockages réseau (FCFA)

2. **Section Cash In / Cash Out**
   - Graphique barres horizontales par commercial (Cash In seul / Cash Out seul / comparaison)
   - Top N / Flop N cash in et cash out (séparés, N configurable 5-20)
   - Alertes seuil (commerciaux sous le seuil configuré)
   - Courbe d'évolution mensuelle réseau (si plusieurs mois disponibles)

3. **Section Réactivité commerciale**
   - Métriques réseau : total tx, tx/jour moyen, meilleur, plus faible
   - Graphique barres transactions/jour par commercial

4. **Section QR Code**
   - 5 métriques : total agents, sans QR, QR non utilisé, risque, actifs
   - 5 KPIs taux : déploiement, utilisation, non utilisés, risque, sans QR
   - Graphique barres empilées par segment (couleurs : rouge/orange/jaune/vert)
   - Classement DSM par agents actifs
   - Expander "agents prioritaires"

5. **Section Appros / Destockages**
   - 4 métriques : nb appros, montant appros, nb destockages, montant destockages
   - Graphique barres groupées appros vs destockages par commercial
   - Graphique nb d'opérations
   - Courbe d'évolution mensuelle

**Filtres sidebar** : mois (cash/appro), date de référence QR Code

---

### Page : Transactions
**Rôles** : super_admin (dépôt), admin et commercial (consultation)

**Onglet Import** (super_admin uniquement)
- Upload multi-fichiers CSV bruts MTN (un par commercial)
- Le commercial est identifié automatiquement depuis le nom du fichier (ANTOINE → ANTOINE)
- Pour chaque fichier :
  - Nettoyage : garde `Date, Type, From name, To name, Amount` (Type=Transfer, hors ALBARKA GN SARL)
  - Génère un classeur Excel 3 onglets : **Données**, **TCD - To Name**, **TCD - From Name**
  - Calcule et stocke les points touchés (nb de lignes par jour)
  - Si alias configuré : stocke les clients servis (contreparties) en base
  - Si alias configuré : extrait et stocke l'appro/destockage depuis les TCD
- Bouton téléchargement individuel + ZIP global (si ≥ 2 fichiers)
- Note sur les commerciaux sans alias

**Onglet Points touchés** (tous)
- Tableau synthèse par commercial : total points, jours actifs, moyenne/jour
- Tableau détail journalier
- Export Excel
- Commercial = vue filtrée sur ses données

**Onglet Clients servis** (tous)
- Filtres : commercial + période (du/au)
- Tableau : MSISDN, Nom, Nb transactions, Première date, Dernière date
- Métriques : clients distincts, total transactions
- Export Excel
- Commercial = vue filtrée sur ses données

---

### Page : Suivi QR Code
**Rôles** : super_admin uniquement

**Fonctionnement** :
- Upload fichier QR Code (.xlsx ou .gz)
- Détection automatique du format par signature binaire (gzip si `0x1f 0x8b`)
- Saisie ou détection automatique de la date de référence (depuis le nom du fichier)
- **Classification des agents** selon 4 statuts dans l'ordre de priorité :
  - `active_deployed` vide → **Sans QR Code**
  - `active_30 == 0` → **QR non utilisé (+30j)**
  - `(date_ref - last_qr_co_date) >= 20 jours` → **Risque inactivité**
  - Sinon → **Actif**
- Génère un rapport Excel multi-onglets :
  - Onglet **Résumé** : comptes, pourcentages, KPIs, formules Excel vivantes
  - Un onglet par combinaison `segment_group × statut` pour les 3 statuts non-actifs
- Sauvegarde un cache CSV dans `data/qr_code/_cache/{date}.csv`
- Historise l'import en base

---

### Page : Étude Comparative
**Rôles** : super_admin, admin

**Fonctionnement** :
- Choisir 2 dates parmi les dates déjà traitées (cache CSV) OU déposer 2 nouveaux fichiers
- Génère un classeur Excel 3 onglets :
  - **Résumé comparatif** : comptages + KPIs
  - **Répartition par catégorie** (segment_group)
  - **Mouvements détaillés** : agents qui ont changé de statut (rapprochement par `pos_msisdn`)

---

### Page : Historique
**Rôles** : super_admin, admin

**Fonctionnement** :
- Affiche par défaut les **5 derniers traitements**
- Bouton "Voir plus" : charge **10 traitements supplémentaires** à chaque clic
- Bouton "Replier" : revient à 5
- Filtres : type de fichier (`qr_code` / `transactions` / `comparatif`) + recherche textuelle
- Pour chaque traitement : type, clé, date des données, nb lignes, date d'exécution
- Bouton **Télécharger** si le fichier Excel existe encore sur le disque
- Bouton **Supprimer** (super_admin uniquement) : supprime uniquement l'enregistrement en base, **jamais le fichier Excel**

---

### Page : Cash Flow
**Rôles** : super_admin (import), admin (consultation)

**Source de données** : fichier SAE MTN mensuel (`.xlsx` ou `.csv`)
**Structure SAE** : 2 feuilles — résumé global (ignoré) + `Sheet1` avec 731 lignes (une par POS agent)
**Colonnes clés** : `acceptorid`, `agent_msisdn`, `agent_name`, `cash_in_com`, `cash_out_com`

**Onglet Import SAE** (super_admin)
- Upload fichier SAE, détection automatique du mois depuis le nom
- Importe 731 POS en base, upsert sur (pos_id, mois)

**Onglet Classements**
- Filtre par mois + slider nombre de POS (5-50)
- Sous-onglets Cash In / Cash Out
- Graphique barres horizontales Top N (Plotly)
- Tableaux Top N et Flop N
- Export Excel

**Onglet Alertes seuil**
- POS dont cash_in ou cash_out < seuil configuré
- Affiche le seuil courant + liste des POS en alerte avec écart
- Export Excel

**Onglet Comparaison MoM multi-fichiers**
- Dépôt de 2 ou 3 fichiers SAE de mois différents
- Détection automatique du mois (modifiable)
- Sorties :
  - **Top 20** de chaque mois (par cash in)
  - **Flop 10** de chaque mois
  - **Top 10 cumulé** : somme cash_in sur tous les mois, classement des 10 premiers
  - **POS constants dans le Top** : présents dans le Top20 de tous les mois
  - **POS constants dans le Flop** : présents dans le Flop10 de tous les mois
- Export Excel complet

---

### Page : Dashboard QR Code
**Rôles** : super_admin, admin

**Fonctionnement** :
- Sélection de la date de référence (parmi les dates avec cache CSV)
- Métriques globales (5 cartes) : total, sans QR, QR non utilisé, risque, actifs
- KPIs taux (5 cartes) : déploiement, utilisation, non utilisés %, risque %, sans QR %
- Tableau répartition par segment + graphique barres empilées
- Tableau répartition par DSM (classé par nb agents actifs)
- Expander agents prioritaires (les 3 statuts non-actifs)
- Export Excel (4 onglets : résumé, par segment, par DSM, agents prioritaires)

---

### Page : Portefeuilles
**Rôles** : super_admin (import + suppression + couverture), admin (consultation + couverture)

**Format des fichiers portefeuille ALBARKA** :
- Fichier Excel avec lignes vides en haut
- Ligne d'en-tête contenant `numéro_ccial`, `pos_profile`, `Nom du client`
- Données à partir de la ligne suivante
- Colonne `numéro_ccial` = MSISDN du client (format `237XXXXXXXXX`)

**Onglet Import** (super_admin)
- Upload fichier Excel, sélection du commercial, nom du portefeuille
- Détection automatique de l'en-tête (N lignes vides tolérées)
- Détection des colonnes MSISDN et profil POS dans les données
- Aperçu des 10 premiers clients avant confirmation
- Stocke dans `portefeuilles` + `clients` (telephone=MSISDN, localite=profil POS)

**Onglet Consultation**
- Filtre par commercial
- Pour chaque portefeuille : nom, commercial, date import, nb clients
- Bouton Supprimer (super_admin, avec confirmation)
- Expander pour voir les clients

**Onglet Couverture**
- Sélection d'un portefeuille + période (du/au) optionnelle
- Upload du/des CSV bruts MTN du commercial
- Rapprochement par **MSISDN** : extraction `FRI:237XXXXXXXXX/MSISDN` depuis colonnes `From`/`To` du CSV brut
- Résultat : tableau `MSISDN | Nom associé | Profil POS | Nombre de contacts | Première transaction | Dernière transaction`
- Clients avec 0 contact inclus (absents du CSV)
- Métriques : clients touchés, non touchés, taux de couverture, total contacts
- Filtre affichage (tous / touchés / non touchés)
- Export Excel (format identique au fichier `Suivi-contacts-portefeuille-EWANE.xlsx`)

---

### Page : Appro / Destockage
**Rôles** : super_admin, admin, commercial (vue filtrée)

**Source** : calculé automatiquement depuis les TCD du classeur Transactions au moment du dépôt CSV.

**Logique de calcul** :
- **Appro** = onglet `TCD - From Name` du classeur Transactions → ligne de l'alias du commercial → montant + nb transactions par date
- **Destockage** = onglet `TCD - To Name` → même logique
- Valeurs en valeur absolue
- Ne s'applique qu'aux commerciaux avec alias (ANTOINE, EWANE, ERVE, STÉPHANE, PARFAIT)

**Onglet Dashboard mensuel**
- Filtre par mois
- Métriques réseau : nb appros, montant appros, nb destockages, montant destockages
- Tableau récapitulatif par commercial
- Graphique barres groupées appros vs destockages
- Graphique nb d'opérations (appro + destoc séparés)
- Classements Top par montant
- Vue filtrée pour le rôle commercial

**Onglet Évolution mensuelle**
- Courbes d'évolution réseau (appros / destockages)
- Pivots par commercial × mois
- Vue filtrée pour commercial

**Onglet Détail journalier**
- Filtres : commercial + mois + type (appro/destockage)
- Tableau : commercial, date, type, nb ops, montant, fichier source

---

### Page : Comparaisons MoM
**Rôles** : tous (commercial = ses données uniquement)

**3 onglets** :

**Cash In / Cash Out MoM**
- Sélection du mois de référence M → calcule automatiquement M-1
- Tableau comparatif par commercial : CI M-1, CI M, évol FCFA, évol %, CO M-1, CO M, évol CO
- Synthèse réseau (4 métriques avec delta)
- Export Excel

**Appro / Destockage MoM**
- Même logique : M vs M-1
- Tableau évolution appros et destockages par commercial
- Synthèse réseau
- Vue filtrée pour commercial

**QR Code MoM**
- Sélection de 2 dates (M-1 et M) parmi les dates disponibles en cache
- Tableau répartition par statut : M-1, %, M, %, évolution
- Tableau évolution par DSM (super_admin / admin)
- KPIs MoM : taux déploiement, taux actif, risque, non utilisé
- Vue filtrée pour commercial

---

### Page : Réactivité Commerciale
**Rôles** : super_admin, admin

**Source** : fichiers CSV bruts MTN (même format que STEPHANE(7).csv, PARF-1-14.csv)

**Fonctionnement** :
- Upload multi-fichiers CSV bruts MTN
- Détection automatique de l'alias dans chaque fichier (via les aliases configurés en base)
- Association fichier → commercial vérifiable manuellement
- Calcul des indicateurs depuis le CSV brut (horodatage complet + Balance)

**Indicateurs calculés par commercial** :
- Nb transactions total
- Jours actifs (nb de jours distincts avec transactions)
- Transactions / jour moyen
- Clients distincts touchés / jour moyen (contreparties sans l'alias et sans ALBARKA)
- Temps mort médian (en minutes) — écart entre transactions consécutives le même jour
- Temps mort maximum observé
- Temps de recharge médian (via colonne Balance — passage sous 100 000 FCFA puis remontée)
- Temps de recharge le plus rapide

**Sections affichées** :
1. Tableau récapitulatif complet (N/A si données insuffisantes)
2. Synthèse réseau (métriques globales)
3. 4 onglets graphiques Plotly barres horizontales : Tx/jour, Clients/jour, Temps mort, Temps recharge
4. Fiche individuelle par commercial
5. Export Excel (synthèse réseau + indicateurs par commercial)

**Persistance** : les résultats sont conservés en session au changement de page. Bouton "Effacer" pour réinitialiser.

---

### Page : MoMo App (Parrainages)
**Rôles** : super_admin uniquement

**Personnes suivies** : Antoine, Parfait, Erve, Ewane, Stéphane, Theo, Nathan, + 2 slots libres

**Onglet Saisie**
- Sélection personne + date + nb parrainages → cumul automatique (si on saisit 3 puis 2 pour la même personne/date → total 5)
- Aperçu des 7 derniers jours

**Onglet Dashboard**
- Filtres période (du/au)
- Synthèse par personne (total sur la période)
- Graphique barres (Plotly, couleur jaune ALBARKA)
- Tableau pivot jour × personne
- Métrique "Total réseau sur la période"
- Export Excel (synthèse + détail + pivot)

**Onglet Gestion des personnes**
- Ajouter une personne temporairement (session courante)
- Supprimer un enregistrement spécifique (personne × date)

---

### Page : Suivi Personnes Spécialement Suivies
**Rôles** : super_admin uniquement

**Commerciaux concernés** : CESAIRE, ANTOINE, PARFAIT, ERVE, STEPHANE

**Onglet Saisie**
- Sélection commercial + nom personne suivie + montant + date + heure
- Aperçu des 20 dernières entrées

**Onglet Dashboard**
- Filtres : commercial + période
- Synthèse par commercial × personne suivie : montant cumulé, nb entrées
- Métriques globales : montant total, personnes distinctes, nb entrées
- Historique chronologique
- Export Excel (synthèse + historique)

**Onglet Gestion**
- Suppression d'entrées individuelles par filtre commercial × date

---

### Page : Administration
**Rôles** : super_admin uniquement

**Onglet Utilisateurs**
- Liste des comptes avec rôle et statut
- Formulaire création : username, nom complet, rôle, mot de passe, dsm_name (si commercial)

**Onglet Modifier / Désactiver**
- Sélection d'un compte (pas le sien)
- Modifier nom et/ou mot de passe
- Activer / Désactiver (avec double confirmation)

**Onglet Commerciaux**
- Sélection d'un commercial
- Modifier : téléphone, zone, dsm_name
- Activer / Désactiver (synchronise aussi le compte utilisateur lié)
- Tableau récapitulatif de tous les commerciaux avec leur alias

**Onglet Aliases CSV**
- Tableau des aliases actuels par commercial
- Formulaire de modification : saisie du nouvel alias (ou vide pour supprimer)
- Tableau de référence des aliases par défaut
- C'est ici que se configurent les liens `PARFAIT → ALBARKA 135` etc.

**Onglet Seuils cash in / cash out**
- Affiche les seuils actuels (global ou par mois)
- Formulaire : nouveau seuil CI, nouveau seuil CO, mois optionnel (AAAA-MM)
- Historique des seuils configurés

---

### Page : Mon Dashboard (Commercial)
**Rôles** : commercial uniquement

**Section 1 — QR Code**
- Sélection de la date de référence (parmi les dates disponibles)
- Vue filtrée sur le dsm_name du commercial connecté
- Métriques : total agents, actifs, à risque, sans QR, taux
- Tableau des agents par statut

**Section 2 — QR Code évolution**
- Sélection de 2 dates
- Évolution des statuts sur son périmètre

**Section 3 — Cash In / Cash Out**
- Ses chiffres cash in/out par mois
- **Rang anonymisé** dans le classement : il voit son rang mais les autres commerciaux apparaissent comme "Commercial #N", seuls les voisins ±2 sont visibles

---

## 6. Fichiers sources et leurs formats

### CSV brut MTN (transactions)
- Colonnes clés : `Id`, `Date` (AAAA-MM-JJ HH:MM:SS), `Status`, `Type`, `From`, `From name`, `To`, `To name`, `Amount`, `Balance`
- `From`/`To` au format `FRI:237XXXXXXXXX/MSISDN`
- `Amount` signé : négatif si le commercial est From (envoie), positif si To (reçoit)
- Filtrer : `Status=Successful` + `Type=Transfer`
- Exclure les lignes où `From name` ou `To name` est `ALBARKA GN SARL` ou `ALBARKA GN SARL 5`

### Fichier SAE MTN (cash flow)
- Excel 2 feuilles : feuille 1 = résumé global (ignorer), feuille 2 `Sheet1` = 731 lignes POS
- Colonnes clés : `acceptorid`, `agent_msisdn`, `agent_name`, `cash_in_com`, `cash_out_com`
- Les valeurs sont des entiers en string (ex. `"25060"`)

### Fichier QR Code
- Excel (.xlsx) ou compressé (.gz)
- Colonnes clés : `active_deployed`, `active_30`, `last_qr_co_date`, `segment_group`, `dsm_name`, `pos_name`, `pos_msisdn`, `region`, `territory`, `town`, `quartier`, `site_name`

### Fichier portefeuille ALBARKA
- Excel avec lignes vides en haut (format variable selon le fichier)
- Ligne d'en-tête : `Nom du client`, `numéro_ccial`, `nom_puce cciale`, `pos_profile`, `Localisation précise`, `numéro personnel`
- Colonne clé : `numéro_ccial` = MSISDN `237XXXXXXXXX`
- Profil POS : commence par `MTNC`

### Classeur Excel généré par Transactions
- 3 onglets : `Données`, `TCD - To Name`, `TCD - From Name`
- TCD structure : ligne 4 = dates (dd/mm/YYYY fusionnées sur 2 colonnes), ligne 5 = `Somme Montant` / `Nb Transactions`, ligne 6+ = données
- L'appro/destockage est extrait depuis les TCD en cherchant la ligne de l'alias

---

## 7. Logique métier critique à préserver

### Classification QR Code (ordre de priorité strict)
```
Si active_deployed est vide/nul → "Sans QR Code"
Sinon si active_30 == 0         → "QR non utilisé (+30j)"
Sinon si (date_ref - last_qr_co_date) >= 20 jours → "Risque inactivité"
Sinon                           → "Actif"
```

### Calcul appro / destockage depuis TCD
```
Appro     = onglet "TCD - From Name", ligne de l'alias, montant par date (valeur absolue)
Destockage = onglet "TCD - To Name",  ligne de l'alias, montant par date (valeur absolue)
```

### Couverture portefeuille
```
Rapprochement par MSISDN :
  - Extraire MSISDN depuis "From"/"To" du CSV brut : regex FRI:(\d{9,12})/MSISDN
  - Identifier la contrepartie (l'autre côté du commercial via son alias)
  - Vérifier si ce MSISDN est dans la liste du portefeuille
  - Compter le nb de transactions et garder min/max des dates
```

### Rang anonymisé (Mon Dashboard commercial)
```
Le commercial voit son rang (ex. #4 sur 6)
Les autres commerciaux : "Commercial #1", "Commercial #2"...
Seuls les voisins ±2 positions sont affichés
```

### Temps mort (réactivité)
```
Pour chaque jour actif :
  Trier les transactions par horodatage
  Calculer les écarts entre transactions consécutives (en minutes)
Médiane et maximum sur tous les écarts de tous les jours
```

### Temps de recharge (réactivité)
```
Seuil flotte basse = 100 000 FCFA
Détecter les passages sous ce seuil (colonne Balance)
Mesurer le temps (en minutes) entre le passage sous le seuil et le premier dépassement
Médiane et minimum de ces durées
```

---

## 8. Exports Excel générés

Tous les exports suivent le même style :
- Couleur header : `#1F4E78` (bleu foncé, pas le jaune ALBARKA — pour la lisibilité Excel)
- Lignes alternées : `#F2F6FA`
- Total bg : `#EAF1F8`
- Police : Arial 10pt
- Freeze panes sur la première ligne de données

Les classeurs de transactions ont des formules Excel vivantes dans les TCD (pas des valeurs figées).

---

## 9. Structure du projet backend (Python)

```
albarka-app/
├── app.py                    ← Point d'entrée (à remplacer par FastAPI dans la refonte)
├── core/
│   ├── db.py                 ← Toutes les fonctions CRUD SQLite (→ PostgreSQL)
│   ├── auth.py               ← Authentification SHA-256
│   ├── transactions.py       ← Nettoyage CSV, génération classeur Excel, extraction appro
│   ├── cashflow.py           ← Parsing SAE, import POS, classements, MoM
│   ├── appro.py              ← Lecture/écriture table appro, agrégations
│   ├── qr_code.py            ← Classification agents, rapport Excel multi-onglets
│   ├── comparaison.py        ← Étude comparative QR Code 2 dates
│   ├── metrics.py            ← Indicateurs réactivité (legacy — partiellement remplacé)
│   ├── export.py             ← Export Excel générique multi-onglets stylisé
│   └── ui.py                 ← CSS/logo (spécifique Streamlit — à supprimer)
├── pages/                    ← Pages Streamlit (→ composants React dans la refonte)
├── data/
│   ├── albarka.db            ← Base SQLite (→ PostgreSQL en prod)
│   ├── qr_code/              ← Rapports QR générés + cache CSV
│   ├── transactions/         ← Classeurs Excel transactions générés
│   └── comparatifs/          ← Classeurs Excel comparatifs générés
└── assets/
    └── logo_albarka.svg
```

---

## 10. Points d'attention pour le nouveau frontend

1. **Authentification** : implémenter JWT avec refresh token. Les rôles doivent être vérifiés côté serveur à chaque requête API, pas seulement côté frontend.

2. **Upload de fichiers** : plusieurs pages nécessitent l'upload de fichiers volumineux (CSV 10 000+ lignes). Utiliser `multipart/form-data` avec indication de progression.

3. **Exports Excel** : les fichiers Excel générés (rapports QR, classeurs TCD) sont produits par `openpyxl` côté Python. Le frontend déclenche la génération via API et télécharge le fichier binaire retourné.

4. **Persistance des résultats de calcul** : la page Réactivité Commerciale fait des calculs longs sur plusieurs fichiers. Stocker les résultats en base (nouvelle table `resultats_reactivite`) ou utiliser Redis pour le cache, plutôt que la session navigateur.

5. **Données temps réel** : aucune donnée temps réel dans l'application. Tout est basé sur des imports manuels de fichiers. Pas de WebSocket nécessaire.

6. **Graphiques** : tous les graphiques actuels sont en Plotly. Recharts ou Chart.js sont de bonnes alternatives React. Les types utilisés : barres horizontales, barres groupées, barres empilées, courbes d'évolution.

7. **Filtres sidebar** : le Dashboard Global a des filtres persistants (mois cash, mois appro, date QR) qui s'appliquent à plusieurs sections simultanément. Gérer cela avec un state global (Redux, Zustand, Context API).

8. **Navigation** : chaque rôle a une liste de pages différente. La navigation doit être construite dynamiquement après connexion selon le rôle retourné par l'API.

9. **Suppressions** : toujours confirmer les suppressions avec un dialog de confirmation. Les suppressions ne touchent **jamais les fichiers sur disque** — uniquement la base de données.

10. **Rang anonymisé** (Mon Dashboard commercial) : logique à implémenter côté API — retourner le classement complet mais anonymisé, avec position du commercial connecté mise en évidence.
