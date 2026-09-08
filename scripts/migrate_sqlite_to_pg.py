#!/usr/bin/env python3
"""
scripts/migrate_sqlite_to_pg.py
================================
Migre toutes les données de data/albarka.db vers PostgreSQL.

Usage :
    cd /home/giovanni/Documents/stage/albarka-app
    source .venv/bin/activate
    python3 scripts/migrate_sqlite_to_pg.py

La variable DATABASE_URL doit être définie dans .env ou dans l'environnement.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Charger .env manuellement
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import psycopg2
import psycopg2.extras

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = BASE_DIR / "data" / "albarka.db"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERREUR : DATABASE_URL non définie dans .env")
    sys.exit(1)

if not SQLITE_PATH.exists():
    print(f"ERREUR : {SQLITE_PATH} introuvable")
    sys.exit(1)

# Ordre important : respecter les clés étrangères
TABLES_ORDRE = [
    "utilisateurs",
    "commerciaux",
    "aliases_commerciaux",
    "seuils",
    "portefeuilles",
    "clients",
    "clients_servis",
    "pos",
    "cashflow_pos",
    "transactions_momo",
    "appro",
    "parrainages",
    "suivi_personnes",
    "imports",
]


def get_sqlite_data(table: str) -> tuple[list, list]:
    """Retourne (colonnes, lignes) depuis SQLite."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            return [], []
        cols = list(rows[0].keys())
        data = [tuple(r) for r in rows]
        return cols, data
    except Exception as e:
        print(f"  ⚠ Table {table} : {e}")
        return [], []
    finally:
        conn.close()


def migrate_table(pg_conn, table: str):
    cols, rows = get_sqlite_data(table)
    if not rows:
        print(f"  {table:30s} : vide ou absente, ignorée")
        return 0

    placeholders = ", ".join(["%s"] * len(cols))
    col_list     = ", ".join(cols)
    # ON CONFLICT DO NOTHING pour éviter les doublons si on relance la migration
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING"
    )

    with pg_conn.cursor() as cur:
        try:
            psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
            pg_conn.commit()
            print(f"  {table:30s} : {len(rows)} lignes migrées")
            return len(rows)
        except Exception as e:
            pg_conn.rollback()
            print(f"  {table:30s} : ERREUR — {e}")
            return 0


def reset_sequences(pg_conn):
    """Remet à jour les séquences SERIAL après insertion directe des IDs."""
    tables_serial = [
        "utilisateurs", "commerciaux", "aliases_commerciaux", "seuils",
        "portefeuilles", "clients", "clients_servis", "pos", "cashflow_pos",
        "transactions_momo", "appro", "parrainages", "suivi_personnes", "imports",
    ]
    with pg_conn.cursor() as cur:
        for table in tables_serial:
            try:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE(MAX(id), 1)
                    ) FROM {table}
                """)
            except Exception:
                pg_conn.rollback()
    pg_conn.commit()
    print("\nSéquences SERIAL remises à jour.")


def main():
    print(f"Source SQLite : {SQLITE_PATH}")
    print(f"Cible PG      : {DATABASE_URL.split('@')[-1]}")
    print("-" * 50)

    pg_conn = psycopg2.connect(DATABASE_URL)
    total = 0

    for table in TABLES_ORDRE:
        total += migrate_table(pg_conn, table)

    reset_sequences(pg_conn)
    pg_conn.close()

    print("-" * 50)
    print(f"Migration terminée — {total} lignes transférées au total.")


if __name__ == "__main__":
    main()
