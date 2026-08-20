"""
core/appro.py
==============

Parsing et ingestion du fichier SUIVI PERFORMANCES CCIAUX DTD (format Excel
multi-mois, format large avec colonnes paires par commercial).

Structure du fichier (observée sur les données réelles) :
  - Plusieurs blocs mensuels dans le même classeur, séparés par un titre
    de type "JUILLET 2025", "AOUT 2025", etc.
  - Dans chaque bloc :
    * Ligne de sous-titre : "SUIVI PERFORMANCES CCIAUX DTD"
    * Ligne d'entête niveaux 1 : colonne JOURS, puis noms des commerciaux
      (chaque commercial occupe 2 colonnes : appro + destoc), colonne vide,
      puis les mêmes commerciaux pour les montants (2 colonnes chacun)
    * Ligne d'entête niveau 2 : "appro" / "destoc" alternés
    * Lignes de données : date en col 0, comptes paires col 1..., montants paires
    * Ligne TOTAL (ignorée à l'import — on recalcule depuis les données brutes)
    * Ligne "Moyenne service jour" (ignorée)

Règle de stockage :
  - Table `appro` : une ligne par (commercial_id, date_op, type_op)
  - INSERT OR REPLACE sur (commercial_id, date_op, type_op) — un retraitement
    de la même date écrase silencieusement l'ancien enregistrement.
  - Les lignes avec montant = 0 et nb_ops = 0 ou '-' sont ignorées.

Rapprochement commercial :
  - Le nom dans le header du fichier (ex. "PARFAIT") est comparé au dsm_name
    des commerciaux en base (insensible à la casse, strip des espaces).
  - Si aucun commercial en base ne correspond, la colonne est ignorée
    (avec un avertissement retourné dans le résumé).
"""

import io
import re
from pathlib import Path
from datetime import datetime

import pandas as pd

from core.db import get_connection, list_commerciaux

# Valeur numérique nulle représentée par '-' ou ' ' dans le fichier
NULL_VALUES = {"-", " ", "", "nan", "none"}

# Regex pour extraire les titres de blocs mensuels
_MOIS_FR = {
    "JANVIER": 1, "FEVRIER": 2, "FÉVRIER": 2, "MARS": 3, "AVRIL": 4,
    "MAI": 5, "JUIN": 6, "JUILLET": 7, "AOUT": 8, "AOÛT": 8,
    "SEPTEMBRE": 9, "OCTOBRE": 10, "NOVEMBRE": 11, "DECEMBRE": 12, "DÉCEMBRE": 12,
}
_RE_TITRE_MOIS = re.compile(
    r"^(" + "|".join(_MOIS_FR.keys()) + r")\s*(\d{4})", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_amount(val) -> float:
    """Convertit une valeur montant (ex. '26,270,000 FCFA' ou '26 270 000') en float."""
    if val is None:
        return 0.0
    s = str(val).strip()
    if s.upper() in NULL_VALUES or s == "nan":
        return 0.0
    # Supprime FCFA, espaces, virgules (séparateurs de milliers)
    s = re.sub(r"[FCFA\s,]", "", s, flags=re.IGNORECASE)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _clean_count(val) -> int:
    """Convertit un nombre d'opérations (ex. '42' ou '-') en int."""
    if val is None:
        return 0
    s = str(val).strip()
    if s in NULL_VALUES or s.lower() == "nan":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _parse_date(val) -> str | None:
    """Convertit une valeur date en str ISO (AAAA-MM-JJ) ou None."""
    if val is None or str(val).strip() in NULL_VALUES:
        return None
    if isinstance(val, (datetime,)):
        return val.date().isoformat()
    if hasattr(val, "date"):
        try:
            return val.date().isoformat()
        except Exception:
            pass
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _commerciaux_index(commerciaux: list) -> dict:
    """Retourne un dict {nom_upper_strip: dict_commercial}."""
    return {c["dsm_name"].upper().strip(): c for c in commerciaux}


# ---------------------------------------------------------------------------
# Lecture et parsing du fichier
# ---------------------------------------------------------------------------

def _read_raw(source) -> pd.DataFrame:
    """Lit le fichier Excel source en DataFrame brut (sans header, toutes colonnes)."""
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    else:
        raw = source.read() if hasattr(source, "read") else bytes(source)
    # header=None pour garder le contrôle total sur les lignes
    return pd.read_excel(io.BytesIO(raw), header=None, dtype=str)


def _find_month_blocks(df: pd.DataFrame) -> list[dict]:
    """
    Parcourt le DataFrame ligne par ligne et repère les débuts de blocs
    mensuels (ligne contenant uniquement un titre "MOIS AAAA").
    Retourne une liste de dicts {mois: int, annee: int, start_row: int}.
    """
    blocks = []
    for i, row in df.iterrows():
        for cell in row:
            if cell and str(cell).strip():
                m = _RE_TITRE_MOIS.match(str(cell).strip().upper())
                if m:
                    mois_str = m.group(1).upper()
                    annee = int(m.group(2))
                    # Gère les noms collés comme "AVRIL2026"
                    mois_num = _MOIS_FR.get(mois_str)
                    if mois_num:
                        blocks.append({"mois": mois_num, "annee": annee, "start_row": i})
                    break
    return blocks


def _find_header_row(df: pd.DataFrame, start: int, end: int) -> int | None:
    """
    Dans le bloc [start, end], trouve la ligne où 'JOURS' apparaît
    (c'est la ligne des noms de commerciaux, niveau 1 de l'en-tête).
    """
    for i in range(start, min(end, start + 15)):
        row = df.iloc[i]
        for cell in row:
            if str(cell).strip().upper() == "JOURS":
                return i
    return None


def _extract_commercial_names(df: pd.DataFrame, header_row: int) -> list[str]:
    """
    Extrait les noms de commerciaux depuis la ligne d'en-tête niveau 1.
    Les noms sont dans les cellules non-vides différentes de 'JOURS'.
    Retourne une liste ordonnée de noms (avec doublons possibles — un nom
    apparaît deux fois : une fois pour les comptes, une fois pour les montants).
    """
    row = df.iloc[header_row]
    names = []
    for cell in row:
        s = str(cell).strip().upper()
        if s and s not in ("JOURS", "NAN", "") and not s.startswith("SUIVI"):
            names.append(s)
    return names


def _parse_block(df: pd.DataFrame, header_row: int, data_start: int, data_end: int,
                 annee: int, mois: int) -> list[dict]:
    """
    Parse un bloc mensuel et retourne une liste de dicts :
    {dsm_name, date_op, type_op ('appro'|'destockage'), nb_ops, montant}

    Structure attendue dans le bloc :
      header_row   : JOURS | NOM1 | NOM1 | NOM2 | NOM2 | ... | (vide) | NOM1 | NOM1 | ...
      header_row+1 : JOURS | appro | destoc | appro | destoc | ... | (vide) | Total appro | Total destoc | ...
      data_start.. : DATE  | nb    | nb    | nb    | nb    | ...         | montant | montant | ...
    """
    row_h1 = df.iloc[header_row]
    row_h2 = df.iloc[header_row + 1] if header_row + 1 < len(df) else None

    # --- Repérer la colonne séparatrice (vide entre les comptes et les montants) ---
    # On cherche la première colonne vide après JOURS dans la ligne h1
    cols = list(row_h1.index)
    jours_col = None
    for j, cell in enumerate(row_h1):
        if str(cell).strip().upper() == "JOURS":
            jours_col = j
            break
    if jours_col is None:
        return []

    # Colonnes de gauche (comptes) : de jours_col+1 jusqu'à la colonne vide
    # Colonnes de droite (montants) : après la colonne vide
    separateur = None
    for j in range(jours_col + 1, len(row_h1)):
        cell = str(row_h1.iloc[j]).strip()
        if not cell or cell.upper() in ("NAN", ""):
            separateur = j
            break

    if separateur is None:
        return []

    # Noms des commerciaux côté gauche (comptes)
    noms_gauche = []
    j = jours_col + 1
    while j < separateur:
        cell = str(row_h1.iloc[j]).strip().upper()
        if cell and cell not in ("NAN", ""):
            noms_gauche.append((j, cell))  # (col_index, nom)
        j += 1

    # Noms des commerciaux côté droit (montants)
    noms_droite = []
    j = separateur + 1
    while j < len(row_h1):
        cell = str(row_h1.iloc[j]).strip().upper()
        if cell and cell not in ("NAN", ""):
            noms_droite.append((j, cell))
        j += 1

    # Construire le mapping : pour chaque commercial, ses colonnes
    # Côté gauche : colonnes par paire (appro, destoc)
    # Côté droit  : colonnes par paire (total_appro, total_destoc)
    # On s'appuie sur la ligne h2 pour confirmer appro/destoc
    mapping = {}  # nom -> {nb_appro_col, nb_destoc_col, mt_appro_col, mt_destoc_col}

    # Grouper les colonnes gauche par commercial (paires consécutives)
    seen_gauche = {}
    for col_idx, nom in noms_gauche:
        if nom not in seen_gauche:
            seen_gauche[nom] = []
        seen_gauche[nom].append(col_idx)

    seen_droite = {}
    for col_idx, nom in noms_droite:
        if nom not in seen_droite:
            seen_droite[nom] = []
        seen_droite[nom].append(col_idx)

    for nom in seen_gauche:
        cols_g = seen_gauche[nom]
        cols_d = seen_droite.get(nom, [])
        entry = {}
        if len(cols_g) >= 2:
            entry["nb_appro_col"]  = cols_g[0]
            entry["nb_destoc_col"] = cols_g[1]
        elif len(cols_g) == 1:
            entry["nb_appro_col"]  = cols_g[0]
            entry["nb_destoc_col"] = None
        if len(cols_d) >= 2:
            entry["mt_appro_col"]  = cols_d[0]
            entry["mt_destoc_col"] = cols_d[1]
        elif len(cols_d) == 1:
            entry["mt_appro_col"]  = cols_d[0]
            entry["mt_destoc_col"] = None
        if entry:
            mapping[nom] = entry

    # --- Parcourir les lignes de données ---
    lignes = []
    for i in range(data_start, data_end):
        if i >= len(df):
            break
        row = df.iloc[i]
        date_val = _parse_date(row.iloc[jours_col] if jours_col < len(row) else None)
        if not date_val:
            continue

        for nom, cols_map in mapping.items():
            # Comptes
            nb_appro  = _clean_count(row.iloc[cols_map["nb_appro_col"]]  if cols_map.get("nb_appro_col")  is not None and cols_map["nb_appro_col"]  < len(row) else None)
            nb_destoc = _clean_count(row.iloc[cols_map["nb_destoc_col"]] if cols_map.get("nb_destoc_col") is not None and cols_map["nb_destoc_col"] < len(row) else None)
            # Montants
            mt_appro  = _clean_amount(row.iloc[cols_map["mt_appro_col"]]  if cols_map.get("mt_appro_col")  is not None and cols_map["mt_appro_col"]  < len(row) else None)
            mt_destoc = _clean_amount(row.iloc[cols_map["mt_destoc_col"]] if cols_map.get("mt_destoc_col") is not None and cols_map["mt_destoc_col"] < len(row) else None)

            if nb_appro > 0 or mt_appro > 0:
                lignes.append({
                    "dsm_name": nom,
                    "date_op":  date_val,
                    "type_op":  "appro",
                    "nb_ops":   nb_appro,
                    "montant":  mt_appro,
                })
            if nb_destoc > 0 or mt_destoc > 0:
                lignes.append({
                    "dsm_name": nom,
                    "date_op":  date_val,
                    "type_op":  "destockage",
                    "nb_ops":   nb_destoc,
                    "montant":  mt_destoc,
                })

    return lignes


def parse_appro_file(source) -> tuple[list[dict], list[str]]:
    """
    Lit le fichier SUIVI PERFORMANCES CCIAUX DTD et retourne :
      - une liste de dicts {dsm_name, date_op, type_op, nb_ops, montant}
      - une liste de messages d'avertissement (commerciaux non reconnus, etc.)
    """
    df = _read_raw(source)
    blocks = _find_month_blocks(df)
    if not blocks:
        return [], ["Aucun bloc mensuel trouvé dans le fichier."]

    toutes_lignes = []
    avertissements = []

    for idx, bloc in enumerate(blocks):
        start = bloc["start_row"]
        end = blocks[idx + 1]["start_row"] if idx + 1 < len(blocks) else len(df)

        header_row = _find_header_row(df, start, end)
        if header_row is None:
            avertissements.append(
                f"Bloc {bloc['mois']:02d}/{bloc['annee']} : en-tête 'JOURS' non trouvée, bloc ignoré."
            )
            continue

        # Les données commencent 2 lignes après le header (h1 + h2)
        data_start = header_row + 2
        # Les données se terminent à la ligne TOTAL
        data_end = end
        for i in range(data_start, end):
            if i >= len(df):
                break
            cell0 = str(df.iloc[i, 0]).strip().upper()
            if cell0 in ("TOTAL", "TOTAUX"):
                data_end = i
                break

        lignes = _parse_block(df, header_row, data_start, data_end,
                               bloc["annee"], bloc["mois"])
        toutes_lignes.extend(lignes)

    return toutes_lignes, avertissements


# ---------------------------------------------------------------------------
# Import vers la base de données
# ---------------------------------------------------------------------------

def import_appro_file(source, source_fichier_label: str) -> dict:
    """
    Parse le fichier, rapproche les noms de commerciaux avec la base de données,
    et insère les lignes (upsert par commercial_id + date_op + type_op).

    Retourne un résumé :
    {
        "nb_lignes_inserees": int,
        "commerciaux_importes": list[str],
        "commerciaux_ignores": list[str],
        "avertissements": list[str],
    }
    """
    lignes, avertissements = parse_appro_file(source)
    if not lignes:
        raise ValueError(
            "Aucune ligne exploitable trouvée dans le fichier. "
            + " | ".join(avertissements)
        )

    commerciaux = list_commerciaux()
    idx_com = _commerciaux_index(commerciaux)

    conn = get_connection()
    nb_inseres = 0
    noms_importes = set()
    noms_ignores = set()

    for ligne in lignes:
        nom = ligne["dsm_name"].upper().strip()
        commercial = idx_com.get(nom)

        # Tentative de correspondance partielle si pas de match exact
        if commercial is None:
            for key, com in idx_com.items():
                if nom in key or key in nom:
                    commercial = com
                    break

        if commercial is None:
            noms_ignores.add(ligne["dsm_name"])
            continue

        conn.execute("""
            INSERT INTO appro (commercial_id, date_op, type_op, montant, source_fichier)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(commercial_id, date_op, type_op) DO UPDATE SET
                montant        = excluded.montant,
                source_fichier = excluded.source_fichier,
                created_at     = datetime('now')
        """, (
            commercial["id"],
            ligne["date_op"],
            ligne["type_op"],
            ligne["montant"],
            source_fichier_label,
        ))
        nb_inseres += 1
        noms_importes.add(commercial["dsm_name"])

    conn.commit()
    conn.close()

    if noms_ignores:
        avertissements.append(
            f"Commerciaux non trouvés en base (colonnes ignorées) : "
            f"{', '.join(sorted(noms_ignores))}"
        )

    return {
        "nb_lignes_inserees":  nb_inseres,
        "commerciaux_importes": sorted(noms_importes),
        "commerciaux_ignores":  sorted(noms_ignores),
        "avertissements":       avertissements,
    }


# ---------------------------------------------------------------------------
# Lecture / consultation
# ---------------------------------------------------------------------------

def get_appro(commercial_id: int = None, mois: str = None,
              type_op: str = None) -> list[dict]:
    """
    Liste les opérations appro/destockage avec le nom du commercial.
    Filtrable par commercial_id, mois (AAAA-MM) et/ou type_op.
    """
    conn = get_connection()
    q = """
        SELECT a.*, c.dsm_name
        FROM appro a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE 1=1
    """
    params = []
    if commercial_id:
        q += " AND a.commercial_id = ?"
        params.append(commercial_id)
    if mois:
        q += " AND strftime('%Y-%m', a.date_op) = ?"
        params.append(mois)
    if type_op:
        q += " AND a.type_op = ?"
        params.append(type_op)
    q += " ORDER BY c.dsm_name, a.date_op"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_appro_par_mois(mois: str = None) -> list[dict]:
    """
    Agrège les opérations appro et destockage par commercial et par mois.
    Retourne une liste de dicts :
    {dsm_name, mois, nb_appro, montant_appro, nb_destockage, montant_destockage}
    """
    conn = get_connection()
    q = """
        SELECT
            c.dsm_name,
            strftime('%Y-%m', a.date_op) AS mois,
            SUM(CASE WHEN a.type_op = 'appro'       THEN 1 ELSE 0 END) AS nb_appro,
            SUM(CASE WHEN a.type_op = 'appro'       THEN a.montant ELSE 0 END) AS montant_appro,
            SUM(CASE WHEN a.type_op = 'destockage'  THEN 1 ELSE 0 END) AS nb_destockage,
            SUM(CASE WHEN a.type_op = 'destockage'  THEN a.montant ELSE 0 END) AS montant_destockage
        FROM appro a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE 1=1
    """
    params = []
    if mois:
        q += " AND strftime('%Y-%m', a.date_op) = ?"
        params.append(mois)
    q += " GROUP BY c.dsm_name, strftime('%Y-%m', a.date_op) ORDER BY mois DESC, c.dsm_name"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mois_disponibles_appro() -> list[str]:
    """Retourne la liste des mois (AAAA-MM) pour lesquels des données appro existent."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y-%m', date_op) AS mois FROM appro ORDER BY mois DESC"
    ).fetchall()
    conn.close()
    return [r["mois"] for r in rows]


# ---------------------------------------------------------------------------
# Migration schéma : ajoute la colonne nb_ops si elle n'existe pas
# (rétrocompatibilité avec la table créée sans cette colonne)
# ---------------------------------------------------------------------------
def _ensure_nb_ops_column():
    conn = get_connection()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(appro)").fetchall()]
    if "nb_ops" not in cols:
        conn.execute("ALTER TABLE appro ADD COLUMN nb_ops INTEGER DEFAULT 0")
        conn.commit()
    conn.close()


_ensure_nb_ops_column()


# ---------------------------------------------------------------------------
# Auto-test CLI : python3 -m core.appro <fichier.xlsx>
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python3 -m core.appro <fichier_suivi.xlsx>")
        sys.exit(1)

    chemin = sys.argv[1]
    print(f"Parsing de {chemin} ...")
    lignes, warns = parse_appro_file(chemin)
    print(f"{len(lignes)} lignes parsées.")

    noms = sorted({l["dsm_name"] for l in lignes})
    print(f"Commerciaux détectés : {noms}")

    dates = sorted({l["date_op"] for l in lignes})
    print(f"Période : {dates[0] if dates else '—'} → {dates[-1] if dates else '—'}")

    if warns:
        print("\nAvertissements :")
        for w in warns:
            print(f"  ⚠ {w}")

    # Affiche les 5 premières lignes
    print("\n5 premières lignes :")
    for l in lignes[:5]:
        print(f"  {l}")
