"""
core/db.py
==========

Couche de persistance de l'appli ALBARKA.

Tables :
  - imports          : historique des fichiers traités (QR Code, transactions, comparatifs)
  - utilisateurs     : comptes de connexion (super_admin / admin / commercial)
  - commerciaux      : les agents terrain (DSM), liés à un compte utilisateur
  - seuils           : seuils configurables cash in / cash out par l'Admin/Super Admin
  - portefeuilles    : portefeuilles de clients rattachés à un commercial
  - clients          : clients d'un portefeuille
  - transactions_momo: données cash in / cash out calculées depuis le listing Mobile Money
  - appro            : opérations d'approvisionnement / destockage par commercial

Règle : INSERT OR REPLACE sur (type_fichier, cle) pour les imports — un
retraitement de la même clé écrase silencieusement l'ancien enregistrement.
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

    # --- Table historique des imports (existante, inchangée) ---
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

    # --- Utilisateurs ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL UNIQUE,
            nom        TEXT NOT NULL,
            role       TEXT NOT NULL CHECK(role IN ('super_admin','admin','commercial')),
            password_hash TEXT NOT NULL,
            actif      INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # --- Commerciaux (agents terrain / DSM) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commerciaux (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id) ON DELETE SET NULL,
            dsm_name      TEXT NOT NULL UNIQUE,
            telephone     TEXT,
            zone          TEXT,
            actif         INTEGER NOT NULL DEFAULT 1
        )
    """)

    # --- Seuils configurables ---
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

    # --- Portefeuilles ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portefeuilles (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id  INTEGER NOT NULL REFERENCES commerciaux(id) ON DELETE CASCADE,
            nom            TEXT NOT NULL,
            date_import    TEXT NOT NULL,
            nb_clients     INTEGER DEFAULT 0
        )
    """)

    # --- Clients d'un portefeuille ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            portefeuille_id  INTEGER NOT NULL REFERENCES portefeuilles(id) ON DELETE CASCADE,
            nom              TEXT NOT NULL,
            telephone        TEXT,
            localite         TEXT
        )
    """)

    # --- Transactions Mobile Money (cash in / cash out) ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions_momo (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            mois          TEXT NOT NULL,
            cash_in       REAL NOT NULL DEFAULT 0,
            cash_out      REAL NOT NULL DEFAULT 0,
            nb_transactions INTEGER DEFAULT 0,
            source_fichier TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id, mois)
        )
    """)

    # --- Appro / Destockage ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appro (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER REFERENCES commerciaux(id) ON DELETE SET NULL,
            date_op       TEXT NOT NULL,
            type_op       TEXT NOT NULL CHECK(type_op IN ('appro','destockage')),
            nb_ops        INTEGER DEFAULT 0,
            montant       REAL NOT NULL,
            source_fichier TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(commercial_id, date_op, type_op)
        )
    """)

    conn.commit()
    conn.close()

    _seed_users()


# ---------------------------------------------------------------------------
# Gestion des mots de passe
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


# ---------------------------------------------------------------------------
# Seed : données initiales (utilisateurs + commerciaux)
# ---------------------------------------------------------------------------

def _seed_users():
    """Insère les comptes par défaut si la table est vide."""
    conn = get_connection()

    # Comptes Super Admin et Admin
    comptes_base = [
        ("giovanni", "Giovanni", "super_admin", "sadmin123"),
        ("theo",     "Theo",     "admin",       "admin123"),
    ]
    for username, nom, role, mdp in comptes_base:
        existing = conn.execute(
            "SELECT id FROM utilisateurs WHERE username = ?", (username,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (?,?,?,?)",
                (username, nom, role, hash_password(mdp))
            )

    # Commerciaux (DSM) — mot de passe = prénom en minuscules + "123"
    commerciaux = [
        ("parfait",  "PARFAIT",  "parfait123"),
        ("stephane", "STEPHANE", "stephane123"),
        ("franck",   "FRANCK",   "franck123"),
        ("antoine",  "ANTOINE",  "antoine123"),
        ("prosper",  "PROSPER",  "prosper123"),
        ("erve",     "ERVE",     "erve123"),
    ]
    for username, dsm_name, mdp in commerciaux:
        existing = conn.execute(
            "SELECT id FROM utilisateurs WHERE username = ?", (username,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO utilisateurs (username, nom, role, password_hash) VALUES (?,?,?,?)",
                (username, dsm_name, "commercial", hash_password(mdp))
            )
        user = conn.execute(
            "SELECT id FROM utilisateurs WHERE username = ?", (username,)
        ).fetchone()
        if user:
            existing_com = conn.execute(
                "SELECT id FROM commerciaux WHERE dsm_name = ?", (dsm_name,)
            ).fetchone()
            if not existing_com:
                conn.execute(
                    "INSERT INTO commerciaux (utilisateur_id, dsm_name) VALUES (?,?)",
                    (user["id"], dsm_name)
                )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str):
    """
    Vérifie les identifiants. Retourne un dict avec id, username, nom, role
    si OK, ou None si échec.
    """
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
    rows = conn.execute("SELECT id, username, nom, role, actif, created_at FROM utilisateurs ORDER BY role, nom").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, nom: str, role: str, password: str, dsm_name: str = None):
    """Crée un compte utilisateur. Si role='commercial', crée aussi l'entrée commerciaux."""
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
                (user["id"], dsm_name)
            )
    conn.commit()
    conn.close()


def get_commercial_by_user_id(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM commerciaux WHERE utilisateur_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_commerciaux():
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, u.username, u.nom as user_nom
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        WHERE c.actif = 1
        ORDER BY c.dsm_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
        ON CONFLICT(type_flux, mois) DO UPDATE SET valeur=excluded.valeur, created_at=datetime('now')
    """, (type_flux, valeur, mois, created_by))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Portefeuilles et clients
# ---------------------------------------------------------------------------

def create_portefeuille(commercial_id: int, nom: str, date_import: str, clients: list) -> int:
    """
    Crée un portefeuille et insère ses clients.
    `clients` est une liste de dicts avec les clés : nom, telephone (optionnel), localite (optionnel).
    Retourne l'id du portefeuille créé.
    """
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO portefeuilles (commercial_id, nom, date_import, nb_clients) VALUES (?,?,?,?)",
        (commercial_id, nom, date_import, len(clients))
    )
    portefeuille_id = cur.lastrowid
    for client in clients:
        conn.execute(
            "INSERT INTO clients (portefeuille_id, nom, telephone, localite) VALUES (?,?,?,?)",
            (portefeuille_id, client.get("nom", ""), client.get("telephone"), client.get("localite"))
        )
    conn.commit()
    conn.close()
    return portefeuille_id


def list_portefeuilles(commercial_id: int = None) -> list:
    """Liste les portefeuilles, optionnellement filtrés par commercial."""
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
    """Retourne un portefeuille par son id, avec le nom du commercial."""
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
    """Retourne tous les clients d'un portefeuille."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clients WHERE portefeuille_id = ? ORDER BY nom",
        (portefeuille_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_portefeuille(portefeuille_id: int):
    """Supprime un portefeuille et tous ses clients (CASCADE)."""
    conn = get_connection()
    conn.execute("DELETE FROM portefeuilles WHERE id = ?", (portefeuille_id,))
    conn.commit()
    conn.close()


def get_telephones_clients(portefeuille_id: int) -> set:
    """Retourne l'ensemble des numéros de téléphone des clients d'un portefeuille (normalisés)."""
    clients = list_clients(portefeuille_id)
    telephones = set()
    for c in clients:
        tel = c.get("telephone")
        if tel:
            # Normalisation : supprime espaces, tirets, préfixe +237 ou 00237
            tel_norm = str(tel).strip().replace(" ", "").replace("-", "")
            for prefixe in ("+237", "00237"):
                if tel_norm.startswith(prefixe):
                    tel_norm = tel_norm[len(prefixe):]
            telephones.add(tel_norm)
    return telephones


# ---------------------------------------------------------------------------
# Gestion des utilisateurs (modification / désactivation)
# ---------------------------------------------------------------------------

def update_user(user_id: int, nom: str = None, password: str = None):
    """
    Met à jour le nom et/ou le mot de passe d'un utilisateur.
    Seuls les champs fournis (non None) sont modifiés.
    """
    conn = get_connection()
    if nom is not None:
        conn.execute("UPDATE utilisateurs SET nom = ? WHERE id = ?", (nom, user_id))
    if password is not None:
        conn.execute("UPDATE utilisateurs SET password_hash = ? WHERE id = ?",
                     (hash_password(password), user_id))
    conn.commit()
    conn.close()


def toggle_user_actif(user_id: int) -> bool:
    """
    Bascule le statut actif/inactif d'un utilisateur.
    Retourne le nouveau statut (True = actif).
    """
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


def toggle_commercial_actif(commercial_id: int) -> bool:
    """
    Bascule le statut actif/inactif d'un commercial (colonne commerciaux.actif).
    Synchronise également le compte utilisateur lié (utilisateurs.actif) pour
    que la désactivation bloque aussi la connexion.
    Retourne le nouveau statut (True = actif).
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT actif, utilisateur_id FROM commerciaux WHERE id = ?", (commercial_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Commercial {commercial_id} introuvable.")
    nouveau = 0 if row["actif"] else 1
    conn.execute("UPDATE commerciaux SET actif = ? WHERE id = ?", (nouveau, commercial_id))
    # Synchronise le compte utilisateur si lié
    if row["utilisateur_id"]:
        conn.execute(
            "UPDATE utilisateurs SET actif = ? WHERE id = ?",
            (nouveau, row["utilisateur_id"])
        )
    conn.commit()
    conn.close()
    return bool(nouveau)


def update_commercial(commercial_id: int, telephone: str = None, zone: str = None,
                      dsm_name: str = None):
    """
    Met à jour les informations d'un commercial (téléphone, zone, dsm_name).
    Seuls les champs fournis (non None) sont modifiés.
    """
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


def list_commerciaux_complet() -> list:
    """
    Liste tous les commerciaux (actifs et inactifs), avec les infos
    de leur compte utilisateur associé.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.id, c.dsm_name, c.telephone, c.zone, c.actif AS com_actif,
               u.id AS user_id, u.username, u.nom AS user_nom, u.actif AS user_actif
        FROM commerciaux c
        LEFT JOIN utilisateurs u ON c.utilisateur_id = u.id
        ORDER BY c.dsm_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Imports (inchangé par rapport à l'ancienne version)
# ---------------------------------------------------------------------------

def build_output_path(type_fichier: str, cle: str) -> Path:
    if type_fichier not in OUTPUT_DIRS:
        raise ValueError(f"type_fichier inconnu : {type_fichier}")
    nom_fichier = f"{cle}.xlsx".replace("/", "-").replace(" ", "_")
    return OUTPUT_DIRS[type_fichier] / nom_fichier


def save_import(type_fichier: str, cle: str, date_donnees: str, chemin_fichier, nb_lignes: int):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO imports (type_fichier, cle, date_donnees, chemin_fichier, nb_lignes, date_execution)
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


def list_imports(type_fichier: str = None):
    conn = get_connection()
    if type_fichier:
        rows = conn.execute(
            "SELECT * FROM imports WHERE type_fichier = ? ORDER BY date_execution DESC", (type_fichier,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM imports ORDER BY date_execution DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
    conn = get_connection()
    conn.execute("DELETE FROM imports WHERE type_fichier = ? AND cle = ?", (type_fichier, cle))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auto-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Base : {DB_PATH}")
    init_db()
    print("Schéma initialisé.\n")

    print("=== Utilisateurs créés ===")
    for u in list_users():
        print(f"  [{u['role']:12s}] {u['username']:10s} — {u['nom']}")

    print("\n=== Test authentification ===")
    u = authenticate_user("giovanni", "sadmin123")
    print(f"  Giovanni : {'OK' if u else 'ECHEC'} — rôle : {u['role'] if u else '-'}")
    u = authenticate_user("parfait", "parfait123")
    print(f"  Parfait  : {'OK' if u else 'ECHEC'} — rôle : {u['role'] if u else '-'}")
    u = authenticate_user("theo", "mauvais_mdp")
    print(f"  Theo (mauvais mdp) : {'OK' if u else 'ECHEC — normal'}")

    print("\n=== Commerciaux ===")
    for c in list_commerciaux():
        print(f"  {c['dsm_name']:10s} (user_id={c['utilisateur_id']})")
