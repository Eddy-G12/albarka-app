"""
pages/1_Transactions.py
========================
Volet Transactions — réservé au Super Admin.
Import des listings Mobile Money CSV, nettoyage et tableaux croisés Excel.
"""

import io
import zipfile
import streamlit as st
from pathlib import Path

from core import db
from core.auth import require_role, show_user_badge
from core.transactions import clean_transactions, build_transactions_workbook

st.set_page_config(page_title="Transactions — ALBARKA", layout="wide")

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin")
show_user_badge()

st.title("Transactions — nettoyage et tableaux croisés")
st.write(
    "Dépose un ou plusieurs fichiers CSV. Pour chacun : seules les colonnes "
    "Date, Type, From name, To name, Amount sont conservées ; la date est "
    "réduite au jour ; seules les lignes Type = Transfer sont gardées ; "
    "les lignes ALBARKA GN SARL / ALBARKA GN SARL 5 sont exclues."
)

# Initialise la liste des fichiers générés dans la session
if "transactions_chemins" not in st.session_state:
    st.session_state["transactions_chemins"] = []

fichiers = st.file_uploader(
    "Fichiers CSV", type=["csv"], accept_multiple_files=True, key="up_transactions"
)

if st.button("Traiter les fichiers", key="btn_transactions") and fichiers:
    # Réinitialise la liste pour ce nouveau traitement
    st.session_state["transactions_chemins"] = []

    for f in fichiers:
        try:
            cle = Path(f.name).stem
            df = clean_transactions(f)
            if df.empty:
                st.warning(f"{f.name} : aucune ligne exploitable après nettoyage.")
                continue

            wb = build_transactions_workbook(df, source_label=cle)
            chemin = db.build_output_path("transactions", cle)
            wb.save(chemin)

            date_donnees = str(df["Date"].max())
            db.save_import("transactions", cle, date_donnees, chemin, nb_lignes=len(df))

            st.session_state["transactions_chemins"].append(chemin)

            st.success(f"{f.name} — {len(df)} lignes conservées → {chemin.name}")
            with open(chemin, "rb") as fh:
                st.download_button(
                    f"Télécharger {chemin.name}", data=fh.read(), file_name=chemin.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_transactions_{cle}"
                )
        except Exception as e:
            st.error(f"{f.name} — erreur : {e}")

# ---------------------------------------------------------------------------
# Bouton "tout télécharger" — visible dès qu'au moins 2 fichiers ont été générés
# ---------------------------------------------------------------------------
chemins_session = st.session_state.get("transactions_chemins", [])
chemins_existants = [p for p in chemins_session if Path(p).exists()]

if len(chemins_existants) >= 2:
    st.divider()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for chemin in chemins_existants:
            zf.write(chemin, arcname=Path(chemin).name)
    buf.seek(0)

    st.download_button(
        label=f"Télécharger tous les fichiers ({len(chemins_existants)}) en ZIP",
        data=buf,
        file_name="transactions_export.zip",
        mime="application/zip",
        key="dl_transactions_zip",
    )
