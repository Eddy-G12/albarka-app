"""
core/db.py
==========

Couche de persistance de l'appli ALBARKA — v2.

Tables existantes (inchangées) :
  - imports            : historique des fichiers traités
  - utilisateurs       : comptes de connexion
  - commerciaux        : agents terrain (DSM)
  - seuils             : seuils cash in / cash out configurables
  - portefeuilles      : portefeuilles clients par commercial
  - clients            : clients d'un portefeuille
  - transactions_momo  : agrégats cash in / cash out (conservée pour compatibilité historique)
  - appro              : appro / destockage par commercial × date

Nouvelles tables v2 :
  - aliases_commerciaux : alias de chaque commercial dans les fichiers CSV
                          (ex. PARFAIT → ALBARKA 135), modifiable depuis Administration
  - clients_servis      : contreparties historisées jour par jour (depuis Transactions)
                          → sert au calcul de couverture de portefeuille
  - pos                 : agents terrain (POS) issus du fichier SAE MTN
  - cashflow_pos        : cash in / cash out par POS et par mois (source SAE)
  - parrainages         : saisie manuelle des parrainages MoMo App
  - suivi_personnes     : saisie manuelle du suivi des personnes spécialement suivies

Règle générale : INSERT OR REPLACE / ON CONFLICT DO UPDATE — un retraitement
de la même clé écrase silencieusement l'ancien enregistrement.
"""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH  = DATA_DIR / "albarka.db"

OUTPUT_DIRS = {
    "qr_code":      DATA_DIR / "qr_code",
    "transactions": DATA_DIR / "transactions",
    "comparatif":   DATA_DIR / "comparatifs",
}


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for d in OUTPUT_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

def init_db():
    """Crée toutes les tables si elles n'existent pas. À appeler au démarrage."""
    conn = get_connection()

    # ── Historique des imports ──────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            type_fichier   TEXT NOT NULL,
            cle            TEXT NOT NULL,
            date_donnees   TEXT,
            chemin_fichier TEXT NOT NULL,
            nb_lignes      INTEGER,
            date_execution TEXT NOT NULL,
            UNIQUE(type_fichier, cle)
        )
    """)

    # ── Utilisateurs ────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            nom           TEXT NOT NULL,
            role          TEXT NOT NULL CHECK(role IN ('super_admin','admin','commercial')),
            password_hash TEXT NOT NULL,
            actif         INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── Commerciaux ─────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commerciaux (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id) ON DELETE SET NULL,
            dsm_name       TEXT NOT NULL UNIQUE,
            telephone      TEXT,
            zone           TEXT,
            actif          INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ── Aliases commerciaux ─────────────────────────────────────────────────
    # Un alias est le nom tel qu'il apparaît dans les fichiers CSV Mobile Money
    # pour identifier le compte propre du commercial (ex. "ALBARKA 135" pour PARFAIT).
    # Un seul alias actif à la fois par commercial.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS aliases_commerciaux (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            alias         TEXT NOT NULL,
            actif         INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id)
        )
    """)

    # ── Seuils configurables ────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seuils (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type_flux  TEXT NOT NULL CHECK(type_flux IN ('cash_in','cash_out')),
            valeur     REAL NOT NULL,
            mois       TEXT,
            created_by INTEGER REFERENCES utilisateurs(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(type_flux, mois)
        )
    """)

    # ── Portefeuilles ────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portefeuilles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            nom           TEXT NOT NULL,
            date_import   TEXT NOT NULL,
            nb_clients    INTEGER DEFAULT 0
        )
    """)

    # ── Clients d'un portefeuille ────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            portefeuille_id INTEGER NOT NULL REFERENCES portefeuilles(id) ON DELETE CASCADE,
            nom             TEXT NOT NULL,
            telephone       TEXT,
            localite        TEXT
        )
    """)

    # ── Clients servis (historique contreparties) ────────────────────────────
    # Alimenté automatiquement à chaque import de fichier Transactions.
    # nom_contrepartie = libellé MTN de la contrepartie (From/To name hors alias commercial)
    # msisdn_contrepartie = numéro MSISDN brut de la contrepartie (From/To msisdn)
    # Upsert sur (commercial_id, date_op, msisdn_contrepartie) pour dédoublonner.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients_servis (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id       INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            date_op             TEXT NOT NULL,
            nom_contrepartie    TEXT,
            msisdn_contrepartie TEXT NOT NULL,
            nb_transactions     INTEGER NOT NULL DEFAULT 1,
            source_fichier      TEXT,
            created_at          TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id, date_op, msisdn_contrepartie)
        )
    """)

    # ── POS (agents terrain, source SAE MTN) ────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            acceptorid   TEXT NOT NULL UNIQUE,
            agent_msisdn TEXT,
            agent_name   TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── Cash Flow POS (source SAE MTN) ──────────────────────────────────────
    # Remplace transactions_momo pour le module Cash Flow.
    # transactions_momo est conservée pour l'historique existant mais
    # les nouvelles données SAE vont dans cashflow_pos.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cashflow_pos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            pos_id       INTEGER NOT NULL REFERENCES pos(id) ON DELETE CASCADE,
            mois         TEXT NOT NULL,
            cash_in      REAL NOT NULL DEFAULT 0,
            cash_out     REAL NOT NULL DEFAULT 0,
            source_fichier TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(pos_id, mois)
        )
    """)

    # ── transactions_momo (conservée pour compatibilité historique) ──────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions_momo (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id   INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            mois            TEXT NOT NULL,
            cash_in         REAL NOT NULL DEFAULT 0,
            cash_out        REAL NOT NULL DEFAULT 0,
            nb_transactions INTEGER DEFAULT 0,
            source_fichier  TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id, mois)
        )
    """)

    # ── Appro / Destockage ───────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appro (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            date_op       TEXT NOT NULL,
            type_op       TEXT NOT NULL CHECK(type_op IN ('appro','destockage')),
            nb_ops        INTEGER DEFAULT 0,
            montant       REAL NOT NULL DEFAULT 0,
            source_fichier TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id, date_op, type_op)
        )
    """)

    # ── Parrainages MoMo App ─────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parrainages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            personne   TEXT NOT NULL,
            date_op    TEXT NOT NULL,
            nb         INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(personne, date_op)
        )
    """)

    # ── Suivi personnes spécialement suivies ─────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suivi_personnes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            nom_personne  TEXT NOT NULL,
            montant       REAL NOT NULL DEFAULT 0,
            date_heure    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()

    # Migrations sur tables existantes (idempotentes)
    _run_migrations(conn)

    conn.close()
    _seed_users()


def _run_migrations(conn):
    """Applique les migrations de schéma sur les tables existantes (idempotentes)."""
    # nb_ops sur appro (peut manquer sur les anciennes bases)
    try:
        conn.execute("ALTER TABLE appro ADD COLUMN nb_ops INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # colonne déjà présente

    # Index UNIQUE sur appro (remplace la contrainte UNIQUE manquante sur les anciennes bases)
    try:
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_appro_unique
            ON appro(commercial_id, date_op, type_op)
        """)
        conn.commit()
    except Exception:
        pass  # index déjà présent ou conflit de données


# ---------------------------------------------------------------------------
# Gestion des mots de passe
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


# ---------------------------------------------------------------------------
# Seed : données initiales
# ---------------------------------------------------------------------------

def _seed_users():
    """Insère les comptes par défaut si absents, avec leurs aliases."""
    conn = get_connection()

    # Super Admin + Admin
    comptes_base = [
        ("giovanni", "Giovanni", "super_admin", "sadmin123"),
        ("theo",     "Theo",     "admin",       "admin123"),
    ]
    for username, nom, role, mdp in comptes_base:
        if not conn.execute("SELECT id FROM utilisateurs WHERE username = ?", (username,)).fetchone():
            conn.execute(
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (?,?,?,?)",
                (username, nom, role, hash_password(mdp))
            )

    # Commerciaux (DSM) — (username, dsm_name, mdp, alias_dans_csv)
    # alias = None si le commercial n'a pas d'alias dans les fichiers CSV
    commerciaux_seed = [
        ("parfait",  "PARFAIT",  "parfait123",  "ALBARKA 135"),
        ("stephane", "STEPHANE", "stephane123", "ALBARKA 85"),
        ("antoine",  "ANTOINE",  "antoine123",  "ALBARKA 72"),
        ("erve",     "ERVE",     "erve123",     "ALBARKA 89"),
        ("ewane",    "EWANE",    "ewane123",    "ALBARKA 71"),
        ("franck",   "FRANCK",   "franck123",   None),
        ("prosper",  "PROSPER",  "prosper123",  None),
        ("cesaire",  "CESAIRE",  "cesaire123",  None),
    ]

    for username, dsm_name, mdp, alias in commerciaux_seed:
        if not conn.execute("SELECT id FROM utilisateurs WHERE username = ?", (username,)).fetchone():
            conn.execute(
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (?,?,?,?)",
                (username, dsm_name, "commercial", hash_password(mdp))
            )
        user = conn.execute("SELECT id FROM utilisateurs WHERE username = ?", (username,)).fetchone()
        if user:
            if not conn.execute("SELECT id FROM commerciaux WHERE dsm_name = ?", (dsm_name,)).fetchone():
                conn.execute(
                    "INSERT INTO commerciaux (utilisateur_id, dsm_name) VALUES (?,?)",
                    (user["id"], dsm_name)
                )
            # Seed de l'alias si défini
            if alias:
                com = conn.execute("SELECT id FROM commerciaux WHERE dsm_name = ?", (dsm_name,)).fetchone()
                if com and not conn.execute(
                    "SELECT id FROM aliases_commerciaux WHERE commercial_id = ?", (com["id"],)
                ).fetchone():
                    conn.execute(
                        "INSERT INTO aliases_commerciaux (commercial_id, alias) VALUES (?,?)",
                        (com["id"], alias)
                    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM utilisateurs WHERE username = ? AND actif = 1",
        (username.lower().strip(),)
    ).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def get_user_by_id(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, nom, role, actif, created_at FROM utilisateurs ORDER BY role, nom"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, nom: str, role: str, password: str, dsm_name: str = None):
    """Crée un compte. Si role='commercial' et dsm_name fourni, crée aussi dans commerciaux."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (?,?,?,?)",
        (username.lower().strip(), nom, role, hash_password(password))
    )
    if role == "commercial" and dsm_name:
        user = conn.execute(
            "SELECT id FROM utilisateurs WHERE username = ?", (username.lower().strip(),)
        ).fetchone()
        if user:
            conn.execute(
                "INSERT INTO commerciaux (utilisateur_id, dsm_name) VALUES (?,?)",
                (user["id"], dsm_name.strip().upper())
            )
    conn.commit()
    conn.close()


def update_user(user_id: int, nom: str = None, password: str = None):
    conn = get_connection()
    if nom is not None:
        conn.execute("UPDATE utilisateurs SET nom = ? WHERE id = ?", (nom, user_id))
    if password is not None:
        conn.execute("UPDATE utilisateurs SET password_hash = ? WHERE id = ?",
                     (hash_password(password), user_id))
    conn.commit()
    conn.close()


def toggle_user_actif(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT actif FROM utilisateurs WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Utilisateur {user_id} introuvable.")
    nouveau = 0 if row["actif"] else 1
    conn.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?", (nouveau, user_id))
    conn.commit()
    conn.close()
    return bool(nouveau)


def get_commercial_by_user_id(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM commerciaux WHERE utilisateur_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_commerciaux() -> list:
    """Liste les commerciaux actifs avec leur alias s'il existe."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, u.username, u.nom AS user_nom,
               a.alias AS alias_csv
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        LEFT JOIN aliases_commerciaux a ON a.commercial_id = c.id AND a.actif = 1
        WHERE c.actif = 1
        ORDER BY c.dsm_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_commerciaux_complet() -> list:
    """Tous les commerciaux (actifs + inactifs) avec infos compte et alias."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.id, c.dsm_name, c.telephone, c.zone, c.actif AS com_actif,
               u.id AS user_id, u.username, u.nom AS user_nom, u.actif AS user_actif,
               a.alias AS alias_csv
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        LEFT JOIN aliases_commerciaux a ON a.commercial_id = c.id AND a.actif = 1
        ORDER BY c.dsm_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_commercial_actif(commercial_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT actif, utilisateur_id FROM commerciaux WHERE id = ?", (commercial_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Commercial {commercial_id} introuvable.")
    nouveau = 0 if row["actif"] else 1
    conn.execute("UPDATE commerciaux SET actif = ? WHERE id = ?", (nouveau, commercial_id))
    if row["utilisateur_id"]:
        conn.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?",
                     (nouveau, row["utilisateur_id"]))
    conn.commit()
    conn.close()
    return bool(nouveau)


def update_commercial(commercial_id: int, telephone: str = None, zone: str = None,
                      dsm_name: str = None):
    conn = get_connection()
    if telephone is not None:
        conn.execute("UPDATE commerciaux SET telephone = ? WHERE id = ?",
                     (telephone.strip() or None, commercial_id))
    if zone is not None:
        conn.execute("UPDATE commerciaux SET zone = ? WHERE id = ?",
                     (zone.strip() or None, commercial_id))
    if dsm_name is not None and dsm_name.strip():
        conn.execute("UPDATE commerciaux SET dsm_name = ? WHERE id = ?",
                     (dsm_name.strip().upper(), commercial_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Aliases commerciaux
# ---------------------------------------------------------------------------

def get_alias(commercial_id: int) -> str | None:
    """Retourne l'alias actif d'un commercial, ou None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT alias FROM aliases_commerciaux WHERE commercial_id = ? AND actif = 1",
        (commercial_id,)
    ).fetchone()
    conn.close()
    return row["alias"] if row else None


def set_alias(commercial_id: int, alias: str | None):
    """
    Définit (ou supprime) l'alias d'un commercial.
    alias=None ou alias="" → supprime l'alias (actif=0).
    Sinon, upsert sur (commercial_id).
    """
    conn = get_connection()
    if not alias or not alias.strip():
        conn.execute(
            "UPDATE aliases_commerciaux SET actif = 0 WHERE commercial_id = ?",
            (commercial_id,)
        )
    else:
        conn.execute("""
            INSERT INTO aliases_commerciaux (commercial_id, alias, actif)
            VALUES (?, ?, 1)
            ON CONFLICT(commercial_id) DO UPDATE SET
                alias  = excluded.alias,
                actif  = 1,
                created_at = datetime('now')
        """, (commercial_id, alias.strip()))
    conn.commit()
    conn.close()


def list_aliases() -> list:
    """Retourne tous les aliases actifs {commercial_id, dsm_name, alias}."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.id AS commercial_id, c.dsm_name, a.alias
        FROM aliases_commerciaux a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE a.actif = 1
        ORDER BY c.dsm_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alias_map() -> dict:
    """
    Retourne un dict {alias_upper: commercial_dict} pour
    retrouver rapidement le commercial depuis son alias CSV.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.id, c.dsm_name, a.alias
        FROM aliases_commerciaux a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE a.actif = 1
    """).fetchall()
    conn.close()
    return {dict(r)["alias"].upper().strip(): dict(r) for r in rows}


# ---------------------------------------------------------------------------
# Seuils
# ---------------------------------------------------------------------------

def get_seuil(type_flux: str, mois: str = None):
    conn = get_connection()
    if mois:
        row = conn.execute(
            "SELECT * FROM seuils WHERE type_flux = ? AND mois = ? ORDER BY created_at DESC LIMIT 1",
            (type_flux, mois)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM seuils WHERE type_flux = ? AND mois IS NULL ORDER BY created_at DESC LIMIT 1",
            (type_flux,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_seuil(type_flux: str, valeur: float, mois: str = None, created_by: int = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO seuils (type_flux, valeur, mois, created_by)
        VALUES (?,?,?,?)
        ON CONFLICT(type_flux, mois) DO UPDATE SET
            valeur = excluded.valeur,
            created_at = datetime('now')
    """, (type_flux, valeur, mois, created_by))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Portefeuilles et clients
# ---------------------------------------------------------------------------

def create_portefeuille(commercial_id: int, nom: str, date_import: str, clients: list) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO portefeuilles (commercial_id, nom, date_import, nb_clients) VALUES (?,?,?,?)",
        (commercial_id, nom, date_import, len(clients))
    )
    pf_id = cur.lastrowid
    for client in clients:
        conn.execute(
            "INSERT INTO clients (portefeuille_id, nom, telephone, localite) VALUES (?,?,?,?)",
            (pf_id, client.get("nom", ""), client.get("telephone"), client.get("localite"))
        )
    conn.commit()
    conn.close()
    return pf_id


def list_portefeuilles(commercial_id: int = None) -> list:
    conn = get_connection()
    if commercial_id:
        rows = conn.execute("""
            SELECT p.*, c.dsm_name
            FROM portefeuilles p
            JOIN commerciaux c ON c.id = p.commercial_id
            WHERE p.commercial_id = ?
            ORDER BY p.date_import DESC
        """, (commercial_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.*, c.dsm_name
            FROM portefeuilles p
            JOIN commerciaux c ON c.id = p.commercial_id
            ORDER BY c.dsm_name, p.date_import DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_portefeuille(portefeuille_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT p.*, c.dsm_name
        FROM portefeuilles p
        JOIN commerciaux c ON c.id = p.commercial_id
        WHERE p.id = ?
    """, (portefeuille_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_clients(portefeuille_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clients WHERE portefeuille_id = ? ORDER BY nom",
        (portefeuille_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_portefeuille(portefeuille_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM portefeuilles WHERE id = ?", (portefeuille_id,))
    conn.commit()
    conn.close()


def get_telephones_clients(portefeuille_id: int) -> set:
    """Retourne les numéros normalisés des clients d'un portefeuille."""
    clients = list_clients(portefeuille_id)
    telephones = set()
    for c in clients:
        tel = c.get("telephone")
        if tel:
            tel_norm = str(tel).strip().replace(" ", "").replace("-", "")
            if tel_norm.endswith(".0") and tel_norm[:-2].isdigit():
                tel_norm = tel_norm[:-2]
            for prefixe in ("+237", "00237"):
                if tel_norm.startswith(prefixe):
                    tel_norm = tel_norm[len(prefixe):]
            if tel_norm:
                telephones.add(tel_norm)
    return telephones


# ---------------------------------------------------------------------------
# Clients servis
# ---------------------------------------------------------------------------

def save_clients_servis(commercial_id: int,
                        contreparties: list[dict],
                        source_fichier: str = None,
                        date_op: str = None):
    """
    Insère / met à jour les contreparties pour un commercial.
    Chaque entrée de `contreparties` doit contenir :
      - date_op             : date ISO (AAAA-MM-JJ) — lue depuis l'entrée en priorité,
                              sinon utilise le paramètre date_op global (rétrocompatibilité)
      - nom_contrepartie    : nom MTN de la contrepartie
      - msisdn_contrepartie : MSISDN ou nom (fallback) de la contrepartie
      - nb_transactions     : nombre de transactions ce jour (optionnel, défaut 1)
    Upsert sur (commercial_id, date_op, msisdn_contrepartie).
    """
    conn = get_connection()
    for cp in contreparties:
        msisdn = str(cp.get("msisdn_contrepartie", "")).strip()
        if not msisdn:
            continue
        # Priorité : date_op dans l'entrée, sinon paramètre global
        d_op = cp.get("date_op") or date_op
        if not d_op:
            continue  # on ne peut pas insérer sans date
        conn.execute("""
            INSERT INTO clients_servis
                (commercial_id, date_op, nom_contrepartie, msisdn_contrepartie,
                 nb_transactions, source_fichier)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(commercial_id, date_op, msisdn_contrepartie) DO UPDATE SET
                nom_contrepartie = excluded.nom_contrepartie,
                nb_transactions  = nb_transactions + excluded.nb_transactions,
                source_fichier   = excluded.source_fichier,
                created_at       = datetime('now')
        """, (commercial_id, d_op,
              cp.get("nom_contrepartie"),
              msisdn,
              cp.get("nb_transactions", 1),
              source_fichier))
    conn.commit()
    conn.close()


def get_msisdns_servis(commercial_id: int,
                       date_debut: str = None,
                       date_fin: str = None) -> set:
    """
    Retourne l'ensemble des MSISDN des contreparties servies par un commercial
    sur la période [date_debut, date_fin] (bornes incluses, format ISO AAAA-MM-JJ).
    """
    conn = get_connection()
    q = "SELECT msisdn_contrepartie FROM clients_servis WHERE commercial_id = ?"
    params = [commercial_id]
    if date_debut:
        q += " AND date_op >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= ?"
        params.append(date_fin)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {r["msisdn_contrepartie"] for r in rows}


def list_clients_servis(commercial_id: int,
                        date_debut: str = None,
                        date_fin: str = None) -> list:
    """Liste détaillée des clients servis avec agrégation sur la période."""
    conn = get_connection()
    q = """
        SELECT msisdn_contrepartie, nom_contrepartie,
               SUM(nb_transactions) AS nb_total,
               MIN(date_op) AS premiere_date,
               MAX(date_op) AS derniere_date
        FROM clients_servis
        WHERE commercial_id = ?
    """
    params = [commercial_id]
    if date_debut:
        q += " AND date_op >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= ?"
        params.append(date_fin)
    q += " GROUP BY msisdn_contrepartie, nom_contrepartie ORDER BY nb_total DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# POS et Cash Flow SAE
# ---------------------------------------------------------------------------

def upsert_pos(acceptorid: str, agent_msisdn: str = None,
               agent_name: str = None) -> int:
    """Insère ou met à jour un POS. Retourne son id."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO pos (acceptorid, agent_msisdn, agent_name)
        VALUES (?, ?, ?)
        ON CONFLICT(acceptorid) DO UPDATE SET
            agent_msisdn = COALESCE(excluded.agent_msisdn, agent_msisdn),
            agent_name   = COALESCE(excluded.agent_name,   agent_name)
    """, (acceptorid, agent_msisdn, agent_name))
    row = conn.execute("SELECT id FROM pos WHERE acceptorid = ?", (acceptorid,)).fetchone()
    pos_id = row["id"]
    conn.commit()
    conn.close()
    return pos_id


def save_cashflow_pos(pos_id: int, mois: str, cash_in: float,
                      cash_out: float, source_fichier: str = None):
    """Upsert cash in / cash out pour un POS × mois."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO cashflow_pos (pos_id, mois, cash_in, cash_out, source_fichier)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(pos_id, mois) DO UPDATE SET
            cash_in        = excluded.cash_in,
            cash_out       = excluded.cash_out,
            source_fichier = excluded.source_fichier,
            created_at     = datetime('now')
    """, (pos_id, mois, cash_in, cash_out, source_fichier))
    conn.commit()
    conn.close()


def get_cashflow_pos(mois: str) -> list:
    """Retourne tous les POS avec leur cash in/out pour un mois donné."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.acceptorid, p.agent_msisdn, p.agent_name,
               c.mois, c.cash_in, c.cash_out, c.source_fichier
        FROM cashflow_pos c
        JOIN pos p ON p.id = c.pos_id
        WHERE c.mois = ?
        ORDER BY c.cash_in DESC
    """, (mois,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_mois_cashflow_pos() -> list:
    """Liste les mois disponibles dans cashflow_pos."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT mois FROM cashflow_pos ORDER BY mois DESC"
    ).fetchall()
    conn.close()
    return [r["mois"] for r in rows]


def top_flop_pos(mois: str, type_flux: str, n: int = 20, ordre: str = "top") -> list:
    """Classement Top/Flop N des POS pour un mois et un type de flux."""
    if type_flux not in ("cash_in", "cash_out"):
        raise ValueError("type_flux doit être 'cash_in' ou 'cash_out'")
    direction = "DESC" if ordre == "top" else "ASC"
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT p.acceptorid, p.agent_msisdn, p.agent_name,
               c.cash_in, c.cash_out
        FROM cashflow_pos c
        JOIN pos p ON p.id = c.pos_id
        WHERE c.mois = ?
        ORDER BY c.{type_flux} {direction}
        LIMIT ?
    """, (mois, n)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Parrainages
# ---------------------------------------------------------------------------

def save_parrainage(personne: str, date_op: str, nb: int):
    """Ajoute ou cumule des parrainages pour une personne × date."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO parrainages (personne, date_op, nb)
        VALUES (?, ?, ?)
        ON CONFLICT(personne, date_op) DO UPDATE SET
            nb         = nb + excluded.nb,
            created_at = datetime('now')
    """, (personne, date_op, nb))
    conn.commit()
    conn.close()


def get_parrainages(personne: str = None,
                    date_debut: str = None,
                    date_fin: str = None) -> list:
    conn = get_connection()
    q = "SELECT * FROM parrainages WHERE 1=1"
    params = []
    if personne:
        q += " AND personne = ?"
        params.append(personne)
    if date_debut:
        q += " AND date_op >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= ?"
        params.append(date_fin)
    q += " ORDER BY date_op, personne"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_parrainage(personne: str, date_op: str):
    conn = get_connection()
    conn.execute("DELETE FROM parrainages WHERE personne = ? AND date_op = ?",
                 (personne, date_op))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Suivi personnes spécialement suivies
# ---------------------------------------------------------------------------

def save_suivi_personne(commercial_id: int, nom_personne: str,
                        montant: float, date_heure: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO suivi_personnes (commercial_id, nom_personne, montant, date_heure) VALUES (?,?,?,?)",
        (commercial_id, nom_personne.strip(), montant, date_heure)
    )
    conn.commit()
    conn.close()


def get_suivi_personnes(commercial_id: int = None,
                        date_debut: str = None,
                        date_fin: str = None) -> list:
    conn = get_connection()
    q = """
        SELECT s.*, c.dsm_name
        FROM suivi_personnes s
        JOIN commerciaux c ON c.id = s.commercial_id
        WHERE 1=1
    """
    params = []
    if commercial_id:
        q += " AND s.commercial_id = ?"
        params.append(commercial_id)
    if date_debut:
        q += " AND DATE(s.date_heure) >= ?"
        params.append(date_debut)
    if date_fin:
        q += " AND DATE(s.date_heure) <= ?"
        params.append(date_fin)
    q += " ORDER BY s.date_heure DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_suivi_personne(entry_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM suivi_personnes WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

def build_output_path(type_fichier: str, cle: str) -> Path:
    if type_fichier not in OUTPUT_DIRS:
        raise ValueError(f"type_fichier inconnu : {type_fichier}")
    nom_fichier = f"{cle}.xlsx".replace("/", "-").replace(" ", "_")
    return OUTPUT_DIRS[type_fichier] / nom_fichier


def save_import(type_fichier: str, cle: str, date_donnees: str,
                chemin_fichier, nb_lignes: int):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO imports
            (type_fichier, cle, date_donnees, chemin_fichier, nb_lignes, date_execution)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (type_fichier, cle, date_donnees, str(chemin_fichier), nb_lignes,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def get_import(type_fichier: str, cle: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM imports WHERE type_fichier = ? AND cle = ?", (type_fichier, cle)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_imports(type_fichier: str = None, limit: int = None, offset: int = 0):
    conn = get_connection()
    q = "SELECT * FROM imports"
    params: list = []
    if type_fichier:
        q += " WHERE type_fichier = ?"
        params.append(type_fichier)
    q += " ORDER BY date_execution DESC"
    if limit:
        q += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_imports(type_fichier: str = None) -> int:
    conn = get_connection()
    if type_fichier:
        n = conn.execute(
            "SELECT COUNT(*) FROM imports WHERE type_fichier = ?", (type_fichier,)
        ).fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
    conn.close()
    return n


def search_imports(texte: str):
    conn = get_connection()
    motif = f"%{texte}%"
    rows = conn.execute("""
        SELECT * FROM imports
        WHERE cle LIKE ? OR date_donnees LIKE ?
        ORDER BY date_execution DESC
    """, (motif, motif)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_import(type_fichier: str, cle: str):
    """Supprime l'enregistrement en base — jamais le fichier Excel sur disque."""
    conn = get_connection()
    conn.execute("DELETE FROM imports WHERE type_fichier = ? AND cle = ?",
                 (type_fichier, cle))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auto-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Base : {DB_PATH}")
    init_db()
    print("Schéma v2 initialisé.\n")
    print("=== Utilisateurs ===")
    for u in list_users():
        print(f"  [{u['role']:12s}] {u['username']:10s} — {u['nom']}")
    print("\n=== Commerciaux + aliases ===")
    for c in list_commerciaux():
        alias = c.get("alias_csv") or "—"
        print(f"  {c['dsm_name']:10s}  alias CSV : {alias}")
    print("\n=== Aliases map ===")
    for alias, com in get_alias_map().items():
        print(f"  {alias}  →  {com['dsm_name']}")
