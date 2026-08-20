"""
core/cashflow.py
=================

Pipeline complet du Lot B : import du listing Mobile Money -> calcul du
cash in / cash out par commercial et par mois -> stockage dans
transactions_momo -> classements Top 20 / Flop 20 -> alertes seuils.

Ne modifie pas core/db.py : réutilise get_connection() et get_seuil() tels
quels, et n'ajoute que ce qui est spécifique au cash in/cash out.

Règle de calcul (vérifiée sur des données réelles) :
  - Le montant (Amount) est déjà signé du point de vue du compte propre du
    commercial : négatif quand le compte propre est en "From name" (le
    commercial verse du cash -> cash-out), positif quand il est en
    "To name" (le commercial reçoit -> cash-in).
  - cash_out = somme des montants négatifs (en valeur absolue)
  - cash_in  = somme des montants positifs
"""

from pathlib import Path

import pandas as pd

from core.db import get_connection, get_seuil
from core.metrics import load_transactions_full, detect_self_account, _contrepartie  # noqa: F401


# ---------------------------------------------------------------------------
# Rapprochement fichier <-> commercial
# ---------------------------------------------------------------------------
def match_commercial_by_filename(nom_fichier: str, commerciaux: list) -> dict | None:
    """
    Tente de retrouver, parmi la liste des commerciaux (dicts avec au moins
    'dsm_name' et 'id'), celui dont le nom apparaît dans le nom du fichier.
    Retourne None si aucune correspondance claire n'est trouvée -- dans ce
    cas, l'appli doit demander à l'utilisateur de choisir manuellement.
    """
    base = Path(nom_fichier).stem.upper()
    correspondances = [c for c in commerciaux if c["dsm_name"].upper() in base]
    if len(correspondances) == 1:
        return correspondances[0]
    return None


# ---------------------------------------------------------------------------
# Calcul du cash in / cash out par mois
# ---------------------------------------------------------------------------
def compute_cashflow_by_month(df: pd.DataFrame, self_account: str = None) -> dict:
    """
    Retourne {"2026-07": {"cash_in": ..., "cash_out": ..., "nb_transactions": ...}, ...}
    à partir d'un DataFrame déjà nettoyé (issu de core.metrics.load_transactions_full).
    """
    if self_account is None:
        self_account = detect_self_account(df)

    df = df.copy()
    df["mois"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m")

    concerne = (df["From name"] == self_account) | (df["To name"] == self_account)
    df = df[concerne]

    resultat = {}
    for mois, groupe in df.groupby("mois"):
        cash_in = round(float(groupe.loc[groupe["Amount"] > 0, "Amount"].sum()), 2)
        cash_out = round(float(-groupe.loc[groupe["Amount"] < 0, "Amount"].sum()), 2)
        resultat[mois] = {
            "cash_in": cash_in,
            "cash_out": cash_out,
            "nb_transactions": int(len(groupe)),
        }
    return resultat


# ---------------------------------------------------------------------------
# Import complet (fichier -> base)
# ---------------------------------------------------------------------------
def import_cashflow_file(source, commercial_id: int, source_fichier_label: str) -> dict:
    """
    Lit, nettoie, calcule et enregistre le cash in/out pour un commercial,
    mois par mois (un fichier peut couvrir plusieurs mois).
    Écrase silencieusement un mois déjà enregistré pour ce commercial
    (UNIQUE(commercial_id, mois) + upsert), cohérent avec la règle déjà
    retenue pour les autres imports.
    Retourne un résumé {mois: {cash_in, cash_out, nb_transactions}}.
    """
    df = load_transactions_full(source)
    if df.empty:
        raise ValueError("Aucune transaction exploitable dans ce fichier.")

    self_account = detect_self_account(df)
    par_mois = compute_cashflow_by_month(df, self_account)

    conn = get_connection()
    for mois, valeurs in par_mois.items():
        conn.execute("""
            INSERT INTO transactions_momo (commercial_id, mois, cash_in, cash_out, nb_transactions, source_fichier)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(commercial_id, mois) DO UPDATE SET
                cash_in = excluded.cash_in,
                cash_out = excluded.cash_out,
                nb_transactions = excluded.nb_transactions,
                source_fichier = excluded.source_fichier,
                created_at = datetime('now')
        """, (commercial_id, mois, valeurs["cash_in"], valeurs["cash_out"],
              valeurs["nb_transactions"], source_fichier_label))
    conn.commit()
    conn.close()

    return {"compte_propre_detecte": self_account, "par_mois": par_mois}


# ---------------------------------------------------------------------------
# Lecture / consultation
# ---------------------------------------------------------------------------
def get_cashflow(mois: str = None, commercial_id: int = None) -> list:
    """Liste les lignes de cash in/out, jointes au nom du commercial, filtrable par mois et/ou commercial."""
    conn = get_connection()
    requete = """
        SELECT t.*, c.dsm_name
        FROM transactions_momo t
        JOIN commerciaux c ON c.id = t.commercial_id
        WHERE 1=1
    """
    params = []
    if mois:
        requete += " AND t.mois = ?"
        params.append(mois)
    if commercial_id:
        requete += " AND t.commercial_id = ?"
        params.append(commercial_id)
    requete += " ORDER BY c.dsm_name"
    rows = conn.execute(requete, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def top_flop_cashflow(mois: str, type_flux: str, n: int = 20, ordre: str = "top") -> list:
    """
    Classement Top N ou Flop N pour un mois et un type de flux donnés.
    type_flux : 'cash_in' ou 'cash_out'
    ordre     : 'top' (les plus hauts) ou 'flop' (les plus bas)
    """
    if type_flux not in ("cash_in", "cash_out"):
        raise ValueError("type_flux doit être 'cash_in' ou 'cash_out'")
    direction = "DESC" if ordre == "top" else "ASC"
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
    Pour un mois donné, retourne les commerciaux dont le cash_in ou le
    cash_out est SOUS le seuil configuré (get_seuil de core.db). Si aucun
    seuil n'est configuré pour ce mois ou en global, retourne des listes vides.
    """
    seuil_in = get_seuil("cash_in", mois) or get_seuil("cash_in", None)
    seuil_out = get_seuil("cash_out", mois) or get_seuil("cash_out", None)

    lignes = get_cashflow(mois=mois)
    alertes_in = [r for r in lignes if seuil_in and r["cash_in"] < seuil_in["valeur"]]
    alertes_out = [r for r in lignes if seuil_out and r["cash_out"] < seuil_out["valeur"]]

    return {
        "seuil_cash_in": seuil_in["valeur"] if seuil_in else None,
        "seuil_cash_out": seuil_out["valeur"] if seuil_out else None,
        "commerciaux_sous_seuil_cash_in": alertes_in,
        "commerciaux_sous_seuil_cash_out": alertes_out,
    }


# ---------------------------------------------------------------------------
# Auto-test : python3 -m core.cashflow
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from core.db import init_db, list_commerciaux, set_seuil

    init_db()
    commerciaux = list_commerciaux()
    print("Commerciaux en base :", [c["dsm_name"] for c in commerciaux])

    fichiers_test = {
        "PARFAIT.csv": "/mnt/user-data/uploads/PARFAIT.csv",
        "ANTOINE.csv": "/mnt/user-data/uploads/ANTOINE.csv",
    }

    for nom_fichier, chemin in fichiers_test.items():
        match = match_commercial_by_filename(nom_fichier, commerciaux)
        print(f"\n{nom_fichier} -> commercial détecté : {match['dsm_name'] if match else 'AUCUN'}")
        if not match:
            continue
        resume = import_cashflow_file(chemin, match["id"], nom_fichier)
        print(f"  Compte propre : {resume['compte_propre_detecte']}")
        for mois, v in resume["par_mois"].items():
            print(f"  {mois} : cash_in={v['cash_in']:,.0f}  cash_out={v['cash_out']:,.0f}  "
                  f"({v['nb_transactions']} transactions)")

    print("\n=== Contenu de transactions_momo ===")
    for row in get_cashflow():
        print(f"  {row['dsm_name']:10s} | {row['mois']} | cash_in={row['cash_in']:>12,.0f} "
              f"| cash_out={row['cash_out']:>12,.0f}")

    # Test des classements
    mois_test = list(get_cashflow())[0]["mois"] if get_cashflow() else None
    if mois_test:
        print(f"\n=== Top 3 cash_in ({mois_test}) ===")
        for r in top_flop_cashflow(mois_test, "cash_in", n=3, ordre="top"):
            print(f"  {r['dsm_name']:10s} : {r['cash_in']:,.0f}")

        print(f"\n=== Flop 3 cash_out ({mois_test}) ===")
        for r in top_flop_cashflow(mois_test, "cash_out", n=3, ordre="flop"):
            print(f"  {r['dsm_name']:10s} : {r['cash_out']:,.0f}")

        # Test des alertes seuil
        set_seuil("cash_in", 1_000_000, mois=mois_test, created_by=1)
        alertes = list_alertes_seuil(mois_test)
        print(f"\n=== Alertes seuil cash_in ({mois_test}, seuil={alertes['seuil_cash_in']:,.0f}) ===")
        for r in alertes["commerciaux_sous_seuil_cash_in"]:
            print(f"  {r['dsm_name']:10s} sous le seuil : {r['cash_in']:,.0f}")
