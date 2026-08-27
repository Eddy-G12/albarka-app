"""
core/transactions.py
=====================

Nettoyage des fichiers CSV de transactions Mobile Money et génération
du classeur Excel (3 onglets).

Logique de nettoyage (restaurée à l'identique de la version validée) :
  - délimiteur virgule
  - colonnes conservées : Date, Type, From name, To name, Amount
  - Date réduite au jour (sans l'heure)
  - Type = Transfer uniquement
  - exclusion des lignes ALBARKA GN SARL / ALBARKA GN SARL 5 (To name et From name)

Fonctions additionnelles v2 (non utilisées par le nettoyage, utilisées par
pages/1_Transactions.py pour les clients servis et l'appro) :
  - compute_points_touches(df)
  - extract_clients_servis(df, alias)
  - extract_appro_from_workbook(wb_path, alias)
"""

from pathlib import Path
from io import BytesIO
from datetime import datetime

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT_NAME      = "Arial"
HEADER_FILL    = "1F4E78"
SUBHEADER_FILL = "2E75B6"
BAND_FILL      = "F2F6FA"
TOTAL_BG       = "EAF1F8"
GREY           = "666666"
THIN           = Side(style="thin", color="D9D9D9")
BORDER         = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

EXCLUDED_NAMES = ["ALBARKA GN SARL", "ALBARKA GN SARL 5"]


# ---------------------------------------------------------------------------
# Nettoyage — logique originale validée, inchangée
# ---------------------------------------------------------------------------

def clean_transactions(source) -> pd.DataFrame:
    """
    Lit et nettoie un fichier CSV de transactions.
    `source` peut être un chemin de fichier ou un objet fichier (ex. upload Streamlit).
    Retourne un DataFrame avec les colonnes Date (jour seul), Type, From name, To name, Amount.
    """
    df = pd.read_csv(source)
    df = df[["Date", "Type", "From name", "To name", "Amount"]].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df[df["Type"] == "Transfer"]
    df = df[~df["To name"].isin(EXCLUDED_NAMES)]
    df = df[~df["From name"].isin(EXCLUDED_NAMES)]
    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Styles internes
# ---------------------------------------------------------------------------

def _style_header(ws, row, ncols, fill=HEADER_FILL, size=10):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font      = Font(name=FONT_NAME, size=size, bold=True, color="FFFFFF")
        cell.fill      = PatternFill("solid", fgColor=fill)
        cell.border    = BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_data_sheet(wb, df, source_label):
    ws = wb.create_sheet("Données")
    ws.sheet_view.showGridLines = False
    ws["A1"] = f"Données nettoyées — Transferts ({source_label})"
    ws["A1"].font = Font(name=FONT_NAME, size=13, bold=True, color=HEADER_FILL)
    ws["A2"] = f"{len(df)} transactions (Type = Transfer, hors ALBARKA GN SARL / ALBARKA GN SARL 5)"
    ws["A2"].font = Font(name=FONT_NAME, size=10, italic=True, color=GREY)

    cols = ["Date", "Type", "From name", "To name", "Amount"]
    start_row = 4
    for j, h in enumerate(cols, start=1):
        ws.cell(row=start_row, column=j, value=h)
    _style_header(ws, start_row, len(cols))

    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(cols, start=1):
            val = row[col]
            if col == "Date":
                val = val.strftime("%d/%m/%Y")
            cell = ws.cell(row=i, column=j, value=val)
            cell.font   = Font(name=FONT_NAME, size=10)
            cell.border = BORDER
            if col == "Amount":
                cell.number_format = "#,##0"
            if i % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=BAND_FILL)

    widths = {"Date": 12, "Type": 10, "From name": 38, "To name": 38, "Amount": 14}
    for j, h in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(j)].width = widths[h]
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)


def _write_pivot_sheet(wb, sheet_name, title, name_col, df):
    dates   = sorted(df["Date"].unique())
    grouped = df.groupby([name_col, "Date"])["Amount"].agg(["sum", "count"]).reset_index()
    names   = sorted(df[name_col].unique())

    rows = []
    for name in names:
        total_sum, total_cnt = 0, 0
        per_date = {}
        for d in dates:
            match = grouped[(grouped[name_col] == name) & (grouped["Date"] == d)]
            s = int(match["sum"].sum())   if len(match) else 0
            c = int(match["count"].sum()) if len(match) else 0
            per_date[d] = (s, c)
            total_sum += s
            total_cnt += c
        rows.append({"name": name, "per_date": per_date,
                     "total_sum": total_sum, "total_cnt": total_cnt})
    rows.sort(key=lambda r: r["total_sum"], reverse=True)

    ws = wb.create_sheet(sheet_name[:31])
    ws.sheet_view.showGridLines = False
    ws["A1"] = title
    ws["A1"].font = Font(name=FONT_NAME, size=13, bold=True, color=HEADER_FILL)
    ws["A2"] = f"{len(rows)} entrées distinctes — Montants en XAF"
    ws["A2"].font = Font(name=FONT_NAME, size=10, italic=True, color=GREY)

    row1, row2 = 4, 5
    ws.cell(row=row1, column=1, value=name_col)
    ws.merge_cells(start_row=row1, start_column=1, end_row=row2, end_column=1)
    col = 2
    for d in dates:
        ws.cell(row=row1, column=col, value=d.strftime("%d/%m/%Y"))
        ws.merge_cells(start_row=row1, start_column=col, end_row=row1, end_column=col + 1)
        ws.cell(row=row2, column=col,     value="Somme Montant")
        ws.cell(row=row2, column=col + 1, value="Nb Transactions")
        col += 2
    ws.cell(row=row1, column=col, value="TOTAL")
    ws.merge_cells(start_row=row1, start_column=col, end_row=row1, end_column=col + 1)
    ws.cell(row=row2, column=col,     value="Somme Montant")
    ws.cell(row=row2, column=col + 1, value="Nb Transactions")
    total_col = col
    ncols     = col + 1

    _style_header(ws, row1, ncols)
    _style_header(ws, row2, ncols, fill=SUBHEADER_FILL, size=9)

    data_start = row2 + 1
    for i, r in enumerate(rows, start=data_start):
        ws.cell(row=i, column=1, value=r["name"]).font = Font(name=FONT_NAME, size=10)
        ws.cell(row=i, column=1).border = BORDER
        col = 2
        for d in dates:
            s, c = r["per_date"][d]
            cs = ws.cell(row=i, column=col,     value=s if c > 0 else "")
            cs.number_format = "#,##0"
            cc = ws.cell(row=i, column=col + 1, value=c if c > 0 else "")
            for cell in (cs, cc):
                cell.font      = Font(name=FONT_NAME, size=10)
                cell.border    = BORDER
                cell.alignment = Alignment(horizontal="center")
            col += 2
        cs = ws.cell(row=i, column=total_col,     value=r["total_sum"])
        cs.number_format = "#,##0"
        cs.font = Font(name=FONT_NAME, size=10, bold=True)
        cc = ws.cell(row=i, column=total_col + 1, value=r["total_cnt"])
        cc.font = Font(name=FONT_NAME, size=10, bold=True)
        for cell in (cs, cc):
            cell.border    = BORDER
            cell.alignment = Alignment(horizontal="center")
            cell.fill      = PatternFill("solid", fgColor=TOTAL_BG)
        if i % 2 == 0:
            for c_ in range(2, total_col):
                cell = ws.cell(row=i, column=c_)
                if cell.fill.fgColor.rgb in (None, "00000000"):
                    cell.fill = PatternFill("solid", fgColor="F7FAFC")

    gt_row = data_start + len(rows)
    ws.cell(row=gt_row, column=1, value="TOTAL GÉNÉRAL")
    _style_header(ws, gt_row, 1)
    col = 2
    for d in dates:
        s = sum(r["per_date"][d][0] for r in rows)
        c = sum(r["per_date"][d][1] for r in rows)
        sc = ws.cell(row=gt_row, column=col,     value=s)
        cc = ws.cell(row=gt_row, column=col + 1, value=c)
        sc.number_format = "#,##0"
        col += 2
    tot_s = sum(r["total_sum"] for r in rows)
    tot_c = sum(r["total_cnt"] for r in rows)
    ws.cell(row=gt_row, column=total_col,     value=tot_s).number_format = "#,##0"
    ws.cell(row=gt_row, column=total_col + 1, value=tot_c)
    _style_header(ws, gt_row, ncols)

    ws.column_dimensions["A"].width = 42
    for c_ in range(2, ncols + 1):
        ws.column_dimensions[get_column_letter(c_)].width = 15
    ws.freeze_panes = ws.cell(row=data_start, column=2)


def build_transactions_workbook(df: pd.DataFrame, source_label: str = "") -> Workbook:
    """Construit le classeur complet : Données + TCD par To Name + TCD par From Name."""
    wb = Workbook()
    wb.remove(wb.active)
    _write_data_sheet(wb, df, source_label)
    _write_pivot_sheet(wb, "TCD - To Name",
                       "Tableau croisé — Par bénéficiaire (To Name)", "To name", df)
    _write_pivot_sheet(wb, "TCD - From Name",
                       "Tableau croisé — Par expéditeur (From Name)", "From name", df)
    return wb


# ---------------------------------------------------------------------------
# Fonctions v2 — points touchés, clients servis, appro depuis TCD
# (utilisées par pages/1_Transactions.py — n'impactent pas le nettoyage)
# ---------------------------------------------------------------------------

def compute_points_touches(df: pd.DataFrame) -> dict:
    """
    Points touchés = nb de lignes de transactions par jour (comptage brut, sans dédup).
    Retourne {total, par_jour: {date_str: int}, moyenne_par_jour: float}.
    """
    par_jour = {}
    for d, grp in df.groupby("Date"):
        par_jour[str(d)] = len(grp)
    total    = len(df)
    nb_jours = len(par_jour)
    return {
        "total":            total,
        "par_jour":         par_jour,
        "moyenne_par_jour": round(total / nb_jours, 2) if nb_jours else 0.0,
    }


def extract_clients_servis(df: pd.DataFrame, alias: str) -> list[dict]:
    """
    Extrait les contreparties du commercial (identifié par son alias dans From/To name)
    et les agrège par (date_op, nom_contrepartie).
    Retourne [{date_op, nom_contrepartie, msisdn_contrepartie, nb_transactions}].
    msisdn_contrepartie = nom_contrepartie (fallback — CSV sans colonne téléphone).
    """
    alias_upper = alias.strip().upper()
    agg: dict[tuple, dict] = {}

    for _, row in df.iterrows():
        from_name = str(row["From name"]).strip().upper()
        to_name   = str(row["To name"]).strip().upper()

        if from_name == alias_upper:
            nom_cp = row["To name"]
        elif to_name == alias_upper:
            nom_cp = row["From name"]
        else:
            continue

        key = (str(row["Date"]), nom_cp)
        if key not in agg:
            agg[key] = {
                "date_op":             str(row["Date"]),
                "nom_contrepartie":    nom_cp,
                "msisdn_contrepartie": nom_cp,  # fallback : nom utilisé comme clé
                "nb_transactions":     0,
            }
        agg[key]["nb_transactions"] += 1

    return list(agg.values())


def extract_appro_from_workbook(wb_path, alias: str) -> list[dict]:
    """
    Lit le classeur Excel généré par build_transactions_workbook() et extrait
    l'appro (TCD - From Name) et le destockage (TCD - To Name) de l'alias.

    Logique :
      - TCD - From Name → ligne alias → montant/nb par date = APPRO
      - TCD - To Name   → ligne alias → montant/nb par date = DESTOCKAGE

    Retourne [{date_op, type_op, montant, nb_ops}].
    """
    if isinstance(wb_path, (str, Path)):
        wb = load_workbook(wb_path, read_only=True, data_only=True)
    else:
        wb_path.seek(0)
        wb = load_workbook(BytesIO(wb_path.read()), read_only=True, data_only=True)

    alias_upper = alias.strip().upper()
    resultats   = []

    for sheet_name, type_op in [("TCD - From Name", "appro"), ("TCD - To Name", "destockage")]:
        if sheet_name not in wb.sheetnames:
            continue
        ws   = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 5:
            continue

        # Ligne 4 (index 3) = dates fusionnées (format dd/mm/YYYY)
        # Ligne 5 (index 4) = sous-headers "Somme Montant" / "Nb Transactions"
        header_dates = rows[3]
        header_sub   = rows[4]

        # Construire le mapping colonne → (type_valeur, date_iso)
        date_cols: dict[int, tuple] = {}
        current_date = None
        for col_i, val in enumerate(header_dates):
            if col_i == 0:
                continue
            if val is not None:
                d = _parse_date_header(val)
                if d:
                    current_date = d
            if current_date and col_i < len(header_sub) and header_sub[col_i] is not None:
                sous = str(header_sub[col_i]).strip().lower()
                if "somme" in sous or "montant" in sous:
                    date_cols[col_i] = ("montant", current_date)
                elif "nb" in sous or "transaction" in sous:
                    date_cols[col_i] = ("nb", current_date)

        # Trouver la ligne de l'alias
        for row in rows[5:]:
            if row[0] is None:
                continue
            nom_cell = str(row[0]).strip().upper()
            if nom_cell == alias_upper or alias_upper in nom_cell:
                par_date: dict[str, dict] = {}
                for col_i, (type_val, date_iso) in date_cols.items():
                    if col_i >= len(row):
                        continue
                    val = row[col_i]
                    if val is None or str(val).strip() in ("", "-", "nan"):
                        continue
                    try:
                        v = float(str(val).replace(",", "").replace(" ", ""))
                    except ValueError:
                        continue
                    if v == 0:
                        continue
                    if date_iso not in par_date:
                        par_date[date_iso] = {"montant": 0.0, "nb": 0}
                    if type_val == "montant":
                        par_date[date_iso]["montant"] = v
                    else:
                        par_date[date_iso]["nb"] = int(v)

                for date_iso, vals in par_date.items():
                    if vals["montant"] > 0 or vals["nb"] > 0:
                        resultats.append({
                            "date_op": date_iso,
                            "type_op": type_op,
                            "montant": vals["montant"],
                            "nb_ops":  vals["nb"],
                        })
                break

    wb.close()
    return resultats


def _parse_date_header(val) -> str | None:
    """Parse un en-tête de date (str dd/mm/YYYY ou objet date) en ISO."""
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Auto-test CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    chemin_test = sys.argv[1] if len(sys.argv) > 1 else None
    if not chemin_test:
        print("Usage : python3 core/transactions.py <fichier.csv>")
        sys.exit(1)
    label = Path(chemin_test).stem
    print(f"Lecture de {chemin_test} ...")
    df = clean_transactions(chemin_test)
    print(f"{len(df)} lignes conservées après nettoyage.")
    print(f"To Name distincts : {df['To name'].nunique()}")
    print(f"From Name distincts : {df['From name'].nunique()}")
    wb = build_transactions_workbook(df, source_label=label)
    out_path = f"/tmp/test_transactions_{label}.xlsx"
    wb.save(out_path)
    print(f"Rapport généré : {out_path}")
    print(f"Onglets : {wb.sheetnames}")
