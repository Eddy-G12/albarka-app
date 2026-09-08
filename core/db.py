"""
core/db.py — PostgreSQL
========================

Couche de persistance ALBARKA v3 — PostgreSQL via psycopg2.

Changements vs SQLite :
  - get_connection() utilise psycopg2 + DATABASE_URL depuis l'environnement
  - Placeholders ? → %s
  - INSERT OR REPLACE → INSERT ... ON CONFLICT DO UPDATE
  - datetime('now') → NOW()
  - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
  - sqlite3.Row → RealDictCursor (accès par nom de colonne, retourne dict)
  - PRAGMA foreign_keys → FK activées par défaut dans PostgreSQL
  - DATE(col) → col::date

Toutes les fonctions publiques conservent exactement la même signature
et les mêmes types de retour qu'avant : le reste de l'application
(pages Streamlit, endpoints FastAPI) n'a pas besoin de changer.
"""

import hashlib
import os
from pathlib import Path
from datetime import datetime

import psycopg2
import psycopg2.extras

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

OUTPUT_DIRS = {
    "qr_code":      DATA_DIR / "qr_code",
    "transactions": DATA_DIR / "transactions",
    "comparatif":   DATA_DIR / "comparatifs",
}

# ---------------------------------------------------------------------------
# URL de connexion PostgreSQL
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "La variable d'environnement DATABASE_URL est absente. "
            "Exemple : postgresql://giovanni@localhost/albarka"
        )
    return url


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection():
    """Ouvre et retourne une connexion psycopg2 avec RealDictCursor par défaut."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for d in OUTPUT_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    return conn


def _cursor(conn):
    """Raccourci : curseur qui retourne des dict (équivalent sqlite3.Row)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _fetchall(conn, query: str, params=()) -> list:
    with _cursor(conn) as cur:
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def _fetchone(conn, query: str, params=()) -> dict | None:
    with _cursor(conn) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def _execute(conn, query: str, params=()):
    with _cursor(conn) as cur:
        cur.execute(query, params)


# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

def init_db():
    """Crée toutes les tables si elles n'existent pas. À appeler au démarrage."""
    conn = get_connection()

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS imports (
            id             SERIAL PRIMARY KEY,
            type_fichier   TEXT NOT NULL,
            cle            TEXT NOT NULL,
            date_donnees   TEXT,
            chemin_fichier TEXT NOT NULL,
            nb_lignes      INTEGER,
            date_execution TEXT NOT NULL,
            UNIQUE(type_fichier, cle)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id            SERIAL PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE,
            nom           TEXT NOT NULL,
            role          TEXT NOT NULL CHECK(role IN ('super_admin','admin','commercial')),
            password_hash TEXT NOT NULL,
            actif         INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT (NOW()::text)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS commerciaux (
            id             SERIAL PRIMARY KEY,
            utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id) ON DELETE SET NULL,
            dsm_name       TEXT NOT NULL UNIQUE,
            telephone      TEXT,
            zone           TEXT,
            actif          INTEGER NOT NULL DEFAULT 1
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS aliases_commerciaux (
            id            SERIAL PRIMARY KEY,
            commercial_id INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            alias         TEXT NOT NULL,
            actif         INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(commercial_id)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS seuils (
            id         SERIAL PRIMARY KEY,
            type_flux  TEXT NOT NULL CHECK(type_flux IN ('cash_in','cash_out')),
            valeur     REAL NOT NULL,
            mois       TEXT,
            created_by INTEGER REFERENCES utilisateurs(id),
            created_at TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(type_flux, mois)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS portefeuilles (
            id            SERIAL PRIMARY KEY,
            commercial_id INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            nom           TEXT NOT NULL,
            date_import   TEXT NOT NULL,
            nb_clients    INTEGER DEFAULT 0
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS clients (
            id              SERIAL PRIMARY KEY,
            portefeuille_id INTEGER NOT NULL REFERENCES portefeuilles(id) ON DELETE CASCADE,
            nom             TEXT NOT NULL,
            telephone       TEXT,
            localite        TEXT
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS clients_servis (
            id                  SERIAL PRIMARY KEY,
            commercial_id       INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            date_op             TEXT NOT NULL,
            nom_contrepartie    TEXT,
            msisdn_contrepartie TEXT NOT NULL,
            nb_transactions     INTEGER NOT NULL DEFAULT 1,
            source_fichier      TEXT,
            created_at          TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(commercial_id, date_op, msisdn_contrepartie)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS pos (
            id           SERIAL PRIMARY KEY,
            acceptorid   TEXT NOT NULL UNIQUE,
            agent_msisdn TEXT,
            agent_name   TEXT,
            created_at   TEXT NOT NULL DEFAULT (NOW()::text)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS cashflow_pos (
            id             SERIAL PRIMARY KEY,
            pos_id         INTEGER NOT NULL REFERENCES pos(id) ON DELETE CASCADE,
            mois           TEXT NOT NULL,
            cash_in        REAL NOT NULL DEFAULT 0,
            cash_out       REAL NOT NULL DEFAULT 0,
            source_fichier TEXT,
            created_at     TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(pos_id, mois)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS transactions_momo (
            id              SERIAL PRIMARY KEY,
            commercial_id   INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            mois            TEXT NOT NULL,
            cash_in         REAL NOT NULL DEFAULT 0,
            cash_out        REAL NOT NULL DEFAULT 0,
            nb_transactions INTEGER DEFAULT 0,
            source_fichier  TEXT,
            created_at      TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(commercial_id, mois)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS appro (
            id            SERIAL PRIMARY KEY,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            date_op       TEXT NOT NULL,
            type_op       TEXT NOT NULL CHECK(type_op IN ('appro','destockage')),
            nb_ops        INTEGER DEFAULT 0,
            montant       REAL NOT NULL DEFAULT 0,
            source_fichier TEXT,
            created_at    TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(commercial_id, date_op, type_op)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS parrainages (
            id         SERIAL PRIMARY KEY,
            personne   TEXT NOT NULL,
            date_op    TEXT NOT NULL,
            nb         INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (NOW()::text),
            UNIQUE(personne, date_op)
        )
    """)

    _execute(conn, """
        CREATE TABLE IF NOT EXISTS suivi_personnes (
            id            SERIAL PRIMARY KEY,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            nom_personne  TEXT NOT NULL,
            montant       REAL NOT NULL DEFAULT 0,
            date_heure    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (NOW()::text)
        )
    """)

    conn.commit()
    _run_migrations(conn)
    conn.commit()
    conn.close()
    _seed_users()


def _run_migrations(conn):
    """Migrations idempotentes sur schéma existant."""
    # nb_ops sur appro
    try:
        _execute(conn, "ALTER TABLE appro ADD COLUMN IF NOT EXISTS nb_ops INTEGER DEFAULT 0")
    except Exception:
        conn.rollback()

    # Index unique appro
    try:
        _execute(conn, """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_appro_unique
            ON appro(commercial_id, date_op, type_op)
        """)
    except Exception:
        conn.rollback()


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
    conn = get_connection()

    comptes_base = [
        ("giovanni", "Giovanni", "super_admin", "sadmin123"),
        ("theo",     "Theo",     "admin",       "admin123"),
    ]
    for username, nom, role, mdp in comptes_base:
        if not _fetchone(conn, "SELECT id FROM utilisateurs WHERE username = %s", (username,)):
            _execute(conn,
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (%s,%s,%s,%s)",
                (username, nom, role, hash_password(mdp))
            )

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
        if not _fetchone(conn, "SELECT id FROM utilisateurs WHERE username = %s", (username,)):
            _execute(conn,
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (%s,%s,%s,%s)",
                (username, dsm_name, "commercial", hash_password(mdp))
            )
        user = _fetchone(conn, "SELECT id FROM utilisateurs WHERE username = %s", (username,))
        if user:
            if not _fetchone(conn, "SELECT id FROM commerciaux WHERE dsm_name = %s", (dsm_name,)):
                _execute(conn,
                    "INSERT INTO commerciaux (utilisateur_id, dsm_name) VALUES (%s,%s)",
                    (user["id"], dsm_name)
                )
            if alias:
                com = _fetchone(conn, "SELECT id FROM commerciaux WHERE dsm_name = %s", (dsm_name,))
                if com and not _fetchone(conn,
                    "SELECT id FROM aliases_commerciaux WHERE commercial_id = %s", (com["id"],)
                ):
                    _execute(conn,
                        "INSERT INTO aliases_commerciaux (commercial_id, alias) VALUES (%s,%s)",
                        (com["id"], alias)
                    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str):
    conn = get_connection()
    row = _fetchone(conn,
        "SELECT * FROM utilisateurs WHERE username = %s AND actif = 1",
        (username.lower().strip(),)
    )
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return row
    return None


def get_user_by_id(user_id: int):
    conn = get_connection()
    row = _fetchone(conn, "SELECT * FROM utilisateurs WHERE id = %s", (user_id,))
    conn.close()
    return row


def list_users():
    conn = get_connection()
    rows = _fetchall(conn,
        "SELECT id, username, nom, role, actif, created_at FROM utilisateurs ORDER BY role, nom"
    )
    conn.close()
    return rows


def create_user(username: str, nom: str, role: str, password: str, dsm_name: str = None):
    conn = get_connection()
    _execute(conn,
        "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (%s,%s,%s,%s)",
        (username.lower().strip(), nom, role, hash_password(password))
    )
    if role == "commercial" and dsm_name:
        user = _fetchone(conn, "SELECT id FROM utilisateurs WHERE username = %s",
                         (username.lower().strip(),))
        if user:
            _execute(conn,
                "INSERT INTO commerciaux (utilisateur_id, dsm_name) VALUES (%s,%s)",
                (user["id"], dsm_name.strip().upper())
            )
    conn.commit()
    conn.close()


def update_user(user_id: int, nom: str = None, password: str = None):
    conn = get_connection()
    if nom is not None:
        _execute(conn, "UPDATE utilisateurs SET nom = %s WHERE id = %s", (nom, user_id))
    if password is not None:
        _execute(conn, "UPDATE utilisateurs SET password_hash = %s WHERE id = %s",
                 (hash_password(password), user_id))
    conn.commit()
    conn.close()


def toggle_user_actif(user_id: int) -> bool:
    conn = get_connection()
    row = _fetchone(conn, "SELECT actif FROM utilisateurs WHERE id = %s", (user_id,))
    if not row:
        conn.close()
        raise ValueError(f"Utilisateur {user_id} introuvable.")
    nouveau = 0 if row["actif"] else 1
    _execute(conn, "UPDATE utilisateurs SET actif = %s WHERE id = %s", (nouveau, user_id))
    conn.commit()
    conn.close()
    return bool(nouveau)


def get_commercial_by_user_id(user_id: int):
    conn = get_connection()
    row = _fetchone(conn, "SELECT * FROM commerciaux WHERE utilisateur_id = %s", (user_id,))
    conn.close()
    return row


def list_commerciaux() -> list:
    conn = get_connection()
    rows = _fetchall(conn, """
        SELECT c.*, u.username, u.nom AS user_nom,
               a.alias AS alias_csv
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        LEFT JOIN aliases_commerciaux a ON a.commercial_id = c.id AND a.actif = 1
        WHERE c.actif = 1
        ORDER BY c.dsm_name
    """)
    conn.close()
    return rows


def list_commerciaux_complet() -> list:
    conn = get_connection()
    rows = _fetchall(conn, """
        SELECT c.id, c.dsm_name, c.telephone, c.zone, c.actif AS com_actif,
               u.id AS user_id, u.username, u.nom AS user_nom, u.actif AS user_actif,
               a.alias AS alias_csv
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        LEFT JOIN aliases_commerciaux a ON a.commercial_id = c.id AND a.actif = 1
        ORDER BY c.dsm_name
    """)
    conn.close()
    return rows


def toggle_commercial_actif(commercial_id: int) -> bool:
    conn = get_connection()
    row = _fetchone(conn,
        "SELECT actif, utilisateur_id FROM commerciaux WHERE id = %s", (commercial_id,))
    if not row:
        conn.close()
        raise ValueError(f"Commercial {commercial_id} introuvable.")
    nouveau = 0 if row["actif"] else 1
    _execute(conn, "UPDATE commerciaux SET actif = %s WHERE id = %s", (nouveau, commercial_id))
    if row["utilisateur_id"]:
        _execute(conn, "UPDATE utilisateurs SET actif = %s WHERE id = %s",
                 (nouveau, row["utilisateur_id"]))
    conn.commit()
    conn.close()
    return bool(nouveau)


def update_commercial(commercial_id: int, telephone: str = None, zone: str = None,
                      dsm_name: str = None):
    conn = get_connection()
    if telephone is not None:
        _execute(conn, "UPDATE commerciaux SET telephone = %s WHERE id = %s",
                 (telephone.strip() or None, commercial_id))
    if zone is not None:
        _execute(conn, "UPDATE commerciaux SET zone = %s WHERE id = %s",
                 (zone.strip() or None, commercial_id))
    if dsm_name is not None and dsm_name.strip():
        _execute(conn, "UPDATE commerciaux SET dsm_name = %s WHERE id = %s",
                 (dsm_name.strip().upper(), commercial_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Aliases commerciaux
# ---------------------------------------------------------------------------

def get_alias(commercial_id: int) -> str | None:
    conn = get_connection()
    row = _fetchone(conn,
        "SELECT alias FROM aliases_commerciaux WHERE commercial_id = %s AND actif = 1",
        (commercial_id,)
    )
    conn.close()
    return row["alias"] if row else None


def set_alias(commercial_id: int, alias: str | None):
    conn = get_connection()
    if not alias or not alias.strip():
        _execute(conn,
            "UPDATE aliases_commerciaux SET actif = 0 WHERE commercial_id = %s",
            (commercial_id,)
        )
    else:
        _execute(conn, """
            INSERT INTO aliases_commerciaux (commercial_id, alias, actif)
            VALUES (%s, %s, 1)
            ON CONFLICT(commercial_id) DO UPDATE SET
                alias      = EXCLUDED.alias,
                actif      = 1,
                created_at = NOW()::text
        """, (commercial_id, alias.strip()))
    conn.commit()
    conn.close()


def list_aliases() -> list:
    conn = get_connection()
    rows = _fetchall(conn, """
        SELECT c.id AS commercial_id, c.dsm_name, a.alias
        FROM aliases_commerciaux a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE a.actif = 1
        ORDER BY c.dsm_name
    """)
    conn.close()
    return rows


def get_alias_map() -> dict:
    conn = get_connection()
    rows = _fetchall(conn, """
        SELECT c.id, c.dsm_name, a.alias
        FROM aliases_commerciaux a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE a.actif = 1
    """)
    conn.close()
    return {r["alias"].upper().strip(): r for r in rows}


# ---------------------------------------------------------------------------
# Seuils
# ---------------------------------------------------------------------------

def get_seuil(type_flux: str, mois: str = None):
    conn = get_connection()
    if mois:
        row = _fetchone(conn,
            "SELECT * FROM seuils WHERE type_flux = %s AND mois = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (type_flux, mois)
        )
    else:
        row = _fetchone(conn,
            "SELECT * FROM seuils WHERE type_flux = %s AND mois IS NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (type_flux,)
        )
    conn.close()
    return row


def set_seuil(type_flux: str, valeur: float, mois: str = None, created_by: int = None):
    conn = get_connection()
    _execute(conn, """
        INSERT INTO seuils (type_flux, valeur, mois, created_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(type_flux, mois) DO UPDATE SET
            valeur     = EXCLUDED.valeur,
            created_at = NOW()::text
    """, (type_flux, valeur, mois, created_by))
    conn.commit()
    conn.close()


def list_seuils() -> list:
    conn = get_connection()
    rows = _fetchall(conn, "SELECT * FROM seuils ORDER BY created_at DESC")
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Portefeuilles et clients
# ---------------------------------------------------------------------------

def create_portefeuille(commercial_id: int, nom: str, date_import: str,
                        clients: list) -> int:
    conn = get_connection()
    with _cursor(conn) as cur:
        cur.execute(
            "INSERT INTO portefeuilles (commercial_id, nom, date_import, nb_clients) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (commercial_id, nom, date_import, len(clients))
        )
        pf_id = cur.fetchone()["id"]
    for client in clients:
        _execute(conn,
            "INSERT INTO clients (portefeuille_id, nom, telephone, localite) "
            "VALUES (%s,%s,%s,%s)",
            (pf_id, client.get("nom", ""), client.get("telephone"), client.get("localite"))
        )
    conn.commit()
    conn.close()
    return pf_id


def list_portefeuilles(commercial_id: int = None) -> list:
    conn = get_connection()
    if commercial_id:
        rows = _fetchall(conn, """
            SELECT p.*, c.dsm_name
            FROM portefeuilles p
            JOIN commerciaux c ON c.id = p.commercial_id
            WHERE p.commercial_id = %s
            ORDER BY p.date_import DESC
        """, (commercial_id,))
    else:
        rows = _fetchall(conn, """
            SELECT p.*, c.dsm_name
            FROM portefeuilles p
            JOIN commerciaux c ON c.id = p.commercial_id
            ORDER BY c.dsm_name, p.date_import DESC
        """)
    conn.close()
    return rows


def get_portefeuille(portefeuille_id: int) -> dict | None:
    conn = get_connection()
    row = _fetchone(conn, """
        SELECT p.*, c.dsm_name
        FROM portefeuilles p
        JOIN commerciaux c ON c.id = p.commercial_id
        WHERE p.id = %s
    """, (portefeuille_id,))
    conn.close()
    return row


def list_clients(portefeuille_id: int) -> list:
    conn = get_connection()
    rows = _fetchall(conn,
        "SELECT * FROM clients WHERE portefeuille_id = %s ORDER BY nom",
        (portefeuille_id,)
    )
    conn.close()
    return rows


def delete_portefeuille(portefeuille_id: int):
    conn = get_connection()
    _execute(conn, "DELETE FROM portefeuilles WHERE id = %s", (portefeuille_id,))
    conn.commit()
    conn.close()


def get_telephones_clients(portefeuille_id: int) -> set:
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

def save_clients_servis(commercial_id: int, contreparties: list[dict],
                        source_fichier: str = None, date_op: str = None):
    conn = get_connection()
    for cp in contreparties:
        msisdn = str(cp.get("msisdn_contrepartie", "")).strip()
        if not msisdn:
            continue
        d_op = cp.get("date_op") or date_op
        if not d_op:
            continue
        _execute(conn, """
            INSERT INTO clients_servis
                (commercial_id, date_op, nom_contrepartie, msisdn_contrepartie,
                 nb_transactions, source_fichier)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT(commercial_id, date_op, msisdn_contrepartie) DO UPDATE SET
                nom_contrepartie = EXCLUDED.nom_contrepartie,
                nb_transactions  = clients_servis.nb_transactions + EXCLUDED.nb_transactions,
                source_fichier   = EXCLUDED.source_fichier,
                created_at       = NOW()::text
        """, (commercial_id, d_op,
              cp.get("nom_contrepartie"),
              msisdn,
              cp.get("nb_transactions", 1),
              source_fichier))
    conn.commit()
    conn.close()


def get_msisdns_servis(commercial_id: int, date_debut: str = None,
                       date_fin: str = None) -> set:
    conn = get_connection()
    q = "SELECT msisdn_contrepartie FROM clients_servis WHERE commercial_id = %s"
    params = [commercial_id]
    if date_debut:
        q += " AND date_op >= %s"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= %s"
        params.append(date_fin)
    rows = _fetchall(conn, q, params)
    conn.close()
    return {r["msisdn_contrepartie"] for r in rows}


def list_clients_servis(commercial_id: int = None, date_debut: str = None,
                        date_fin: str = None) -> list:
    conn = get_connection()
    q = """
        SELECT msisdn_contrepartie, nom_contrepartie,
               SUM(nb_transactions) AS nb_total,
               MIN(date_op) AS premiere_date,
               MAX(date_op) AS derniere_date
        FROM clients_servis
        WHERE 1=1
    """
    params = []
    if commercial_id is not None:
        q += " AND commercial_id = %s"
        params.append(commercial_id)
    if date_debut:
        q += " AND date_op >= %s"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= %s"
        params.append(date_fin)
    q += " GROUP BY msisdn_contrepartie, nom_contrepartie ORDER BY nb_total DESC"
    rows = _fetchall(conn, q, params)
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# POS et Cash Flow SAE
# ---------------------------------------------------------------------------

def upsert_pos(acceptorid: str, agent_msisdn: str = None,
               agent_name: str = None) -> int:
    conn = get_connection()
    _execute(conn, """
        INSERT INTO pos (acceptorid, agent_msisdn, agent_name)
        VALUES (%s, %s, %s)
        ON CONFLICT(acceptorid) DO UPDATE SET
            agent_msisdn = COALESCE(EXCLUDED.agent_msisdn, pos.agent_msisdn),
            agent_name   = COALESCE(EXCLUDED.agent_name,   pos.agent_name)
    """, (acceptorid, agent_msisdn, agent_name))
    row = _fetchone(conn, "SELECT id FROM pos WHERE acceptorid = %s", (acceptorid,))
    pos_id = row["id"]
    conn.commit()
    conn.close()
    return pos_id


def save_cashflow_pos(pos_id: int, mois: str, cash_in: float,
                      cash_out: float, source_fichier: str = None):
    conn = get_connection()
    _execute(conn, """
        INSERT INTO cashflow_pos (pos_id, mois, cash_in, cash_out, source_fichier)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT(pos_id, mois) DO UPDATE SET
            cash_in        = EXCLUDED.cash_in,
            cash_out       = EXCLUDED.cash_out,
            source_fichier = EXCLUDED.source_fichier,
            created_at     = NOW()::text
    """, (pos_id, mois, cash_in, cash_out, source_fichier))
    conn.commit()
    conn.close()


def get_cashflow_pos(mois: str) -> list:
    conn = get_connection()
    rows = _fetchall(conn, """
        SELECT p.acceptorid, p.agent_msisdn, p.agent_name,
               c.mois, c.cash_in, c.cash_out, c.source_fichier
        FROM cashflow_pos c
        JOIN pos p ON p.id = c.pos_id
        WHERE c.mois = %s
        ORDER BY c.cash_in DESC
    """, (mois,))
    conn.close()
    return rows


def list_mois_cashflow_pos() -> list:
    conn = get_connection()
    rows = _fetchall(conn,
        "SELECT DISTINCT mois FROM cashflow_pos ORDER BY mois DESC"
    )
    conn.close()
    return [r["mois"] for r in rows]


def top_flop_pos(mois: str, type_flux: str, n: int = 20, ordre: str = "top") -> list:
    if type_flux not in ("cash_in", "cash_out"):
        raise ValueError("type_flux doit être 'cash_in' ou 'cash_out'")
    direction = "DESC" if ordre == "top" else "ASC"
    # Pas d'interpolation f-string sur le nom de colonne — on valide au-dessus
    col = "cash_in" if type_flux == "cash_in" else "cash_out"
    conn = get_connection()
    rows = _fetchall(conn, f"""
        SELECT p.acceptorid, p.agent_msisdn, p.agent_name,
               c.cash_in, c.cash_out
        FROM cashflow_pos c
        JOIN pos p ON p.id = c.pos_id
        WHERE c.mois = %s
        ORDER BY c.{col} {direction}
        LIMIT %s
    """, (mois, n))
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Parrainages
# ---------------------------------------------------------------------------

def save_parrainage(personne: str, date_op: str, nb: int):
    conn = get_connection()
    _execute(conn, """
        INSERT INTO parrainages (personne, date_op, nb)
        VALUES (%s, %s, %s)
        ON CONFLICT(personne, date_op) DO UPDATE SET
            nb         = parrainages.nb + EXCLUDED.nb,
            created_at = NOW()::text
    """, (personne, date_op, nb))
    conn.commit()
    conn.close()


def get_parrainages(personne: str = None, date_debut: str = None,
                    date_fin: str = None) -> list:
    conn = get_connection()
    q = "SELECT * FROM parrainages WHERE 1=1"
    params = []
    if personne:
        q += " AND personne = %s"
        params.append(personne)
    if date_debut:
        q += " AND date_op >= %s"
        params.append(date_debut)
    if date_fin:
        q += " AND date_op <= %s"
        params.append(date_fin)
    q += " ORDER BY date_op, personne"
    rows = _fetchall(conn, q, params)
    conn.close()
    return rows


def delete_parrainage(personne: str, date_op: str):
    conn = get_connection()
    _execute(conn, "DELETE FROM parrainages WHERE personne = %s AND date_op = %s",
             (personne, date_op))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Suivi personnes
# ---------------------------------------------------------------------------

def save_suivi_personne(commercial_id: int, nom_personne: str,
                        montant: float, date_heure: str):
    conn = get_connection()
    _execute(conn,
        "INSERT INTO suivi_personnes "
        "(commercial_id, nom_personne, montant, date_heure) VALUES (%s,%s,%s,%s)",
        (commercial_id, nom_personne.strip(), montant, date_heure)
    )
    conn.commit()
    conn.close()


def get_suivi_personnes(commercial_id: int = None, date_debut: str = None,
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
        q += " AND s.commercial_id = %s"
        params.append(commercial_id)
    if date_debut:
        q += " AND s.date_heure::date >= %s"
        params.append(date_debut)
    if date_fin:
        q += " AND s.date_heure::date <= %s"
        params.append(date_fin)
    q += " ORDER BY s.date_heure DESC"
    rows = _fetchall(conn, q, params)
    conn.close()
    return rows


def delete_suivi_personne(entry_id: int):
    conn = get_connection()
    _execute(conn, "DELETE FROM suivi_personnes WHERE id = %s", (entry_id,))
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
    _execute(conn, """
        INSERT INTO imports
            (type_fichier, cle, date_donnees, chemin_fichier, nb_lignes, date_execution)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(type_fichier, cle) DO UPDATE SET
            date_donnees   = EXCLUDED.date_donnees,
            chemin_fichier = EXCLUDED.chemin_fichier,
            nb_lignes      = EXCLUDED.nb_lignes,
            date_execution = EXCLUDED.date_execution
    """, (type_fichier, cle, date_donnees, str(chemin_fichier), nb_lignes,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def get_import(type_fichier: str, cle: str):
    conn = get_connection()
    row = _fetchone(conn,
        "SELECT * FROM imports WHERE type_fichier = %s AND cle = %s",
        (type_fichier, cle)
    )
    conn.close()
    return row


def list_imports(type_fichier: str = None, limit: int = None, offset: int = 0):
    conn = get_connection()
    q = "SELECT * FROM imports"
    params: list = []
    if type_fichier:
        q += " WHERE type_fichier = %s"
        params.append(type_fichier)
    q += " ORDER BY date_execution DESC"
    if limit:
        q += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    rows = _fetchall(conn, q, params)
    conn.close()
    return rows


def count_imports(type_fichier: str = None) -> int:
    conn = get_connection()
    if type_fichier:
        row = _fetchone(conn,
            "SELECT COUNT(*) AS n FROM imports WHERE type_fichier = %s", (type_fichier,))
    else:
        row = _fetchone(conn, "SELECT COUNT(*) AS n FROM imports")
    conn.close()
    return row["n"] if row else 0


def search_imports(texte: str):
    conn = get_connection()
    motif = f"%{texte}%"
    rows = _fetchall(conn, """
        SELECT * FROM imports
        WHERE cle LIKE %s OR date_donnees LIKE %s
        ORDER BY date_execution DESC
    """, (motif, motif))
    conn.close()
    return rows


def delete_import(type_fichier: str, cle: str):
    conn = get_connection()
    _execute(conn, "DELETE FROM imports WHERE type_fichier = %s AND cle = %s",
             (type_fichier, cle))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auto-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("Schéma PostgreSQL initialisé.\n")
    print("=== Utilisateurs ===")
    for u in list_users():
        print(f"  [{u['role']:12s}] {u['username']:10s} — {u['nom']}")
    print("\n=== Commerciaux + aliases ===")
    for c in list_commerciaux():
        alias = c.get("alias_csv") or "—"
        print(f"  {c['dsm_name']:10s}  alias CSV : {alias}")
    print("\n=== Alias map ===")
    for alias, com in get_alias_map().items():
        print(f"  {alias}  →  {com['dsm_name']}")
