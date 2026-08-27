"""
core/cashflow.py — v2
======================

Pipeline Cash Flow source SAE MTN.

Source : fichier SAE_ALBARKA_[MOIS]_[ANNEE].xlsx ou .csv
Structure attendue : une ligne par POS (agent terrain), colonnes clés :
  - acceptorid      : identifiant unique du POS
  - agent_msisdn    : numéro MSISDN de l'agent
  - agent_name      : nom de l'agent
  - cash_in_com     : montant cash in du POS pour la période
  - cash_out_com    : montant cash out du POS pour la période

Classements Top/Flop : au niveau des POS individuels (pas des commerciaux).
Alertes seuils : inchangées — seuils configurables par l'Admin/Super Admin.

MoM multi-fichiers :
  - Dépôt de 2 ou 3 fichiers SAE de mois différents
  - Top 20 par mois, Flop 10 par mois, POS constants dans le Top/Flop,
    Top 10 cumulé sur tous les mois fournis
"""

from io import BytesIO
from pathlib import Path

import pandas as pd

from core.db import (
    get_connection, get_seuil,
    upsert_pos, save_cashflow_pos,
    get_cashflow_pos, list_mois_cashflow_pos, top_flop_pos,
)

# Noms de colonnes SAE possibles (insensible à la casse — on normalise à l'import)
_COL_ACCEPTORID   = ["acceptorid", "acceptor_id", "pos_id", "id"]
_COL_MSISDN       = ["agent_msisdn", "msisdn", "telephone", "phone"]
_COL_NAME         = ["agent_name", "name", "nom", "pos_name", "agentname"]
_COL_CASH_IN      = ["cash_in_com", "cash_in", "cashin", "total_cash_in"]
_COL_CASH_OUT     = ["cash_out_com", "cash_out", "cashout", "total_cash_out"]


# ---------------------------------------------------------------------------
# Helpers de détection de colonnes
# ---------------------------------------------------------------------------

def _find_col(df_cols: list[str], candidates: list[str]) -> str | None:
    """Trouve la première colonne correspondant à l'un des candidats (insensible casse)."""
    lower_cols = {c.lower().strip(): c for c in df_cols}
    for cand in candidates:
        if cand.lower() in lower_cols:
            return lower_cols[cand.lower()]
    return None


def _detect_mois_from_filename(nom: str) -> str | None:
    """
    Tente d'extraire le mois (AAAA-MM) depuis le nom de fichier.
    Patterns reconnus : SAE_ALBARKA_JUILLET_2026, SAE_2026_07, 2026-07, ...
    """
    import re
    mois_fr = {
        "JANVIER": "01", "FEVRIER": "02", "FÉVRIER": "02", "MARS": "03",
        "AVRIL": "04", "MAI": "05", "JUIN": "06", "JUILLET": "07",
        "AOUT": "08", "AOÛT": "08", "SEPTEMBRE": "09", "OCTOBRE": "10",
        "NOVEMBRE": "11", "DECEMBRE": "12", "DÉCEMBRE": "12",
    }
    nom_upper = Path(nom).stem.upper()

    # Pattern AAAA-MM ou AAAA_MM
    m = re.search(r"(20\d{2})[-_](\d{2})", nom_upper)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    # Pattern NOM_MOIS_AAAA
    for mois_nom, mois_num in mois_fr.items():
        if mois_nom in nom_upper:
            annee = re.search(r"20\d{2}", nom_upper)
            if annee:
                return f"{annee.group()}-{mois_num}"

    return None


# ---------------------------------------------------------------------------
# Lecture et parsing du fichier SAE
# ---------------------------------------------------------------------------

def read_sae_file(source, nom_fichier: str = "") -> pd.DataFrame:
    """
    Lit un fichier SAE MTN (.xlsx ou .csv).
    Retourne un DataFrame avec les colonnes normalisées :
      acceptorid, agent_msisdn, agent_name, cash_in, cash_out

    `source` : chemin (str/Path), bytes, ou objet fichier.
    """
    # Lecture
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    elif isinstance(source, bytes):
        raw = source
    else:
        source.seek(0)
        raw = source.read()

    ext = Path(nom_fichier).suffix.lower() if nom_fichier else ""
    if ext == ".csv" or (not ext and raw[:2] != b"\x50\x4b"):
        # Tenter CSV avec différents séparateurs
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(BytesIO(raw), sep=sep, dtype=str)
                if len(df.columns) > 1:
                    break
            except Exception:
                continue
    else:
        df = pd.read_excel(BytesIO(raw), dtype=str)

    # Normaliser les noms de colonnes
    df.columns = df.columns.str.strip()

    col_id   = _find_col(list(df.columns), _COL_ACCEPTORID)
    col_msisdn = _find_col(list(df.columns), _COL_MSISDN)
    col_name = _find_col(list(df.columns), _COL_NAME)
    col_ci   = _find_col(list(df.columns), _COL_CASH_IN)
    col_co   = _find_col(list(df.columns), _COL_CASH_OUT)

    if not col_id or not col_ci:
        raise ValueError(
            f"Colonnes requises introuvables dans le fichier SAE.\n"
            f"Colonnes détectées : {list(df.columns)}\n"
            f"Attendu (au moins) : acceptorid + cash_in_com"
        )

    def _to_float(series: pd.Series) -> pd.Series:
        return (
            series.astype(str)
            .str.replace(r"[\s,]", "", regex=True)
            .str.replace(r"[^\d.\-]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0.0)
        )

    out = pd.DataFrame()
    out["acceptorid"]   = df[col_id].astype(str).str.strip()
    out["agent_msisdn"] = df[col_msisdn].astype(str).str.strip() if col_msisdn else ""
    out["agent_name"]   = df[col_name].astype(str).str.strip()   if col_name   else ""
    out["cash_in"]      = _to_float(df[col_ci])
    out["cash_out"]     = _to_float(df[col_co]) if col_co else 0.0

    # Exclure les lignes sans acceptorid valide
    out = out[out["acceptorid"].notna() & (out["acceptorid"] != "") & (out["acceptorid"] != "nan")]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Import SAE → base
# ---------------------------------------------------------------------------

def import_sae_file(source, nom_fichier: str, mois: str = None) -> dict:
    """
    Lit le fichier SAE, upsert les POS et leurs cash in/out dans la base.

    mois : format AAAA-MM. Si None, tente de le détecter depuis nom_fichier.

    Retourne un résumé :
    {
      "mois": str,
      "nb_pos": int,
      "total_cash_in": float,
      "total_cash_out": float,
    }
    """
    if not mois:
        mois = _detect_mois_from_filename(nom_fichier)
    if not mois:
        raise ValueError(
            "Impossible de détecter le mois depuis le nom du fichier. "
            "Précisez-le manuellement (format AAAA-MM)."
        )

    df = read_sae_file(source, nom_fichier)
    if df.empty:
        raise ValueError("Aucun POS valide trouvé dans le fichier.")

    for _, row in df.iterrows():
        pos_id = upsert_pos(
            acceptorid=row["acceptorid"],
            agent_msisdn=row["agent_msisdn"] or None,
            agent_name=row["agent_name"]     or None,
        )
        save_cashflow_pos(
            pos_id=pos_id,
            mois=mois,
            cash_in=float(row["cash_in"]),
            cash_out=float(row["cash_out"]),
            source_fichier=nom_fichier,
        )

    return {
        "mois":           mois,
        "nb_pos":         len(df),
        "total_cash_in":  float(df["cash_in"].sum()),
        "total_cash_out": float(df["cash_out"].sum()),
    }


# ---------------------------------------------------------------------------
# Alertes seuil (inchangées — seuils globaux ou par mois)
# ---------------------------------------------------------------------------

def list_alertes_seuil_pos(mois: str) -> dict:
    """
    Pour un mois donné, retourne les POS dont le cash_in ou cash_out
    est sous le seuil configuré.
    """
    seuil_in  = get_seuil("cash_in",  mois) or get_seuil("cash_in",  None)
    seuil_out = get_seuil("cash_out", mois) or get_seuil("cash_out", None)

    lignes = get_cashflow_pos(mois)

    sous_ci = []
    sous_co = []

    val_ci  = seuil_in["valeur"]  if seuil_in  else None
    val_co  = seuil_out["valeur"] if seuil_out else None

    for ligne in lignes:
        if val_ci  is not None and ligne["cash_in"]  < val_ci:
            sous_ci.append(ligne)
        if val_co is not None and ligne["cash_out"] < val_co:
            sous_co.append(ligne)

    return {
        "seuil_cash_in":                   val_ci,
        "seuil_cash_out":                  val_co,
        "pos_sous_seuil_cash_in":          sous_ci,
        "pos_sous_seuil_cash_out":         sous_co,
    }


# ---------------------------------------------------------------------------
# MoM multi-fichiers
# ---------------------------------------------------------------------------

def compute_mom_multi(fichiers: list[dict]) -> dict:
    """
    Analyse MoM sur 2 ou 3 fichiers SAE.

    `fichiers` : liste de dicts {source, nom_fichier, mois (optionnel)}

    Retourne :
    {
      "mois_list": ["2026-05", "2026-06", ...],
      "top20": {mois: [pos_dict, ...]},
      "flop10": {mois: [pos_dict, ...]},
      "top10_cumule": [pos_dict avec cash_in_total, cash_out_total, ...],
      "constants_top": [pos_dict],   # POS dans le Top20 de TOUS les mois
      "constants_flop": [pos_dict],  # POS dans le Flop10 de TOUS les mois
      "dataframes": {mois: pd.DataFrame},
    }
    """
    mois_list = []
    dataframes: dict[str, pd.DataFrame] = {}

    for f in fichiers:
        source = f["source"]
        nom    = f["nom_fichier"]
        mois   = f.get("mois") or _detect_mois_from_filename(nom)
        if not mois:
            raise ValueError(
                f"Impossible de détecter le mois pour {nom}. "
                "Précisez-le manuellement."
            )
        df = read_sae_file(source, nom)
        df["mois"] = mois
        dataframes[mois] = df
        mois_list.append(mois)

    mois_list = sorted(set(mois_list))

    # Top 20 et Flop 10 par mois
    top20  = {}
    flop10 = {}
    for mois, df in dataframes.items():
        top20[mois]  = (
            df.nlargest(20, "cash_in")
            [["acceptorid", "agent_msisdn", "agent_name", "cash_in", "cash_out"]]
            .to_dict("records")
        )
        flop10[mois] = (
            df.nsmallest(10, "cash_in")
            [["acceptorid", "agent_msisdn", "agent_name", "cash_in", "cash_out"]]
            .to_dict("records")
        )

    # POS constants dans le Top20 de TOUS les mois
    sets_top = [
        {r["acceptorid"] for r in top20[m]} for m in mois_list if m in top20
    ]
    ids_constants_top = set.intersection(*sets_top) if sets_top else set()

    # POS constants dans le Flop10 de TOUS les mois
    sets_flop = [
        {r["acceptorid"] for r in flop10[m]} for m in mois_list if m in flop10
    ]
    ids_constants_flop = set.intersection(*sets_flop) if sets_flop else set()

    # Infos des POS constants (depuis le premier DataFrame disponible)
    first_df = next(iter(dataframes.values()))

    def _pos_info(ids: set) -> list[dict]:
        return (
            first_df[first_df["acceptorid"].isin(ids)]
            [["acceptorid", "agent_msisdn", "agent_name"]]
            .to_dict("records")
        )

    constants_top  = _pos_info(ids_constants_top)
    constants_flop = _pos_info(ids_constants_flop)

    # Top 10 cumulé : somme cash_in sur tous les mois, classement des 10 premiers
    all_dfs = pd.concat(list(dataframes.values()), ignore_index=True)
    cumul = (
        all_dfs.groupby(["acceptorid", "agent_msisdn", "agent_name"], as_index=False)
        .agg(cash_in_total=("cash_in", "sum"), cash_out_total=("cash_out", "sum"))
        .nlargest(10, "cash_in_total")
    )
    top10_cumule = cumul.to_dict("records")

    return {
        "mois_list":       mois_list,
        "top20":           top20,
        "flop10":          flop10,
        "top10_cumule":    top10_cumule,
        "constants_top":   constants_top,
        "constants_flop":  constants_flop,
        "dataframes":      dataframes,
    }


# ---------------------------------------------------------------------------
# Compatibilité v1 — fonctions sur transactions_momo (agrégats par commercial)
# Conservées pour les pages Dashboard Global, Mon Dashboard, Comparaison MoM
# et Réactivité Commerciale qui les importent encore.
# ---------------------------------------------------------------------------

from pathlib import Path as _Path


def match_commercial_by_filename(nom_fichier: str, commerciaux: list) -> dict | None:
    """
    Tente de retrouver le commercial dont le dsm_name apparaît dans le nom
    du fichier. Retourne None si aucune correspondance unique n'est trouvée.
    (Conservé pour compatibilité avec pages/12_Reactivite_Commerciale.py)
    """
    base = _Path(nom_fichier).stem.upper()
    correspondances = [c for c in commerciaux if c["dsm_name"].upper() in base]
    if len(correspondances) == 1:
        return correspondances[0]
    return None


def get_cashflow(mois: str = None, commercial_id: int = None) -> list:
    """
    Lit les agrégats cash in / cash out depuis la table transactions_momo
    (données historiques — source : anciens imports CSV par commercial).
    Filtrable par mois (AAAA-MM) et/ou commercial_id.
    (Conservé pour compatibilité avec Dashboard Global, Mon Dashboard, MoM)
    """
    from core.db import get_connection
    conn = get_connection()
    q = """
        SELECT t.*, c.dsm_name
        FROM transactions_momo t
        JOIN commerciaux c ON c.id = t.commercial_id
        WHERE 1=1
    """
    params: list = []
    if mois:
        q += " AND t.mois = ?"
        params.append(mois)
    if commercial_id:
        q += " AND t.commercial_id = ?"
        params.append(commercial_id)
    q += " ORDER BY c.dsm_name"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def top_flop_cashflow(mois: str, type_flux: str, n: int = 20,
                      ordre: str = "top") -> list:
    """
    Classement Top/Flop N des commerciaux depuis transactions_momo.
    (Conservé pour compatibilité avec Dashboard Global et Mon Dashboard)
    """
    if type_flux not in ("cash_in", "cash_out"):
        raise ValueError("type_flux doit être 'cash_in' ou 'cash_out'")
    direction = "DESC" if ordre == "top" else "ASC"
    from core.db import get_connection
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT t.*, c.dsm_name
        FROM transactions_momo t
        JOIN commerciaux c ON c.id = t.commercial_id
        WHERE t.mois = ?
        ORDER BY t.{type_flux} {direction}
        LIMIT ?
    """, (mois, n)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_alertes_seuil(mois: str) -> dict:
    """
    Alertes seuil sur transactions_momo (commerciaux, pas POS).
    (Conservé pour compatibilité avec Dashboard Global)
    """
    from core.db import get_connection, get_seuil
    seuil_in  = get_seuil("cash_in",  mois) or get_seuil("cash_in",  None)
    seuil_out = get_seuil("cash_out", mois) or get_seuil("cash_out", None)
    lignes    = get_cashflow(mois=mois)

    val_ci  = seuil_in["valeur"]  if seuil_in  else None
    val_co  = seuil_out["valeur"] if seuil_out else None

    return {
        "seuil_cash_in":                    val_ci,
        "seuil_cash_out":                   val_co,
        "commerciaux_sous_seuil_cash_in":   [r for r in lignes if val_ci  and r["cash_in"]  < val_ci],
        "commerciaux_sous_seuil_cash_out":  [r for r in lignes if val_co and r["cash_out"] < val_co],
    }
