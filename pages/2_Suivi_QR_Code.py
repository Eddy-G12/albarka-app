"""
pages/2_Suivi_QR_Code.py
=========================
Volet Suivi QR Code — réservé au Super Admin.
Classification des agents par statut d'utilisation QR Code.
"""

import re
import streamlit as st
from datetime import date
from pathlib import Path

from core import db
from core.auth import require_role, show_user_badge
from core.qr_code import read_qr_file, classify, build_report_workbook

st.set_page_config(page_title="Suivi QR Code — ALBARKA", layout="wide")

require_role("super_admin")
show_user_badge()

CACHE_QR_DIR = db.DATA_DIR / "qr_code" / "_cache"
CACHE_QR_DIR.mkdir(parents=True, exist_ok=True)

CACHE_COLUMNS = [
    "pos_msisdn", "pos_name", "segment_group", "dsm_name",
    "region", "territory", "site_name", "statut", "priorite", "days_since_last_use"
]


def guess_date_from_filename(name: str):
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def save_qr_cache(df_classified, date_iso: str):
    import pandas as pd
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    df_classified[CACHE_COLUMNS].to_csv(path, index=False)


st.title("Suivi QR Code — classification des agents")
st.write(
    "Dépose le fichier QR Code (.xlsx ou .gz compressé). Chaque agent est classé "
    "en 4 statuts : Sans QR Code, QR non utilisé (+30j), Risque d'inactivité (20-29j), Actif."
)

fichier_qr = st.file_uploader("Fichier QR Code", type=["xlsx", "gz"], key="up_qr")

date_defaut = date.today()
date_devinee = False
if fichier_qr is not None:
    devinee = guess_date_from_filename(fichier_qr.name)
    if devinee:
        date_defaut = devinee
        date_devinee = True

date_ref = st.date_input("Date de référence", value=date_defaut, key="date_qr", format="DD/MM/YYYY")

if fichier_qr is not None:
    if date_devinee:
        st.caption(f"Date détectée automatiquement depuis le nom du fichier : **{date_defaut.strftime('%d/%m/%Y')}**")
    else:
        st.warning("Aucune date détectée dans le nom du fichier — vérifie que la date de référence ci-dessus est correcte avant de générer le rapport.")

if st.button("Générer le rapport", key="btn_qr") and fichier_qr is not None:
    try:
        df_raw = read_qr_file(fichier_qr)
        if df_raw.empty:
            st.error("Aucune ligne lue dans le fichier — vérifie le format.")
        else:
            df_classified = classify(df_raw, date_ref)
            date_iso = date_ref.isoformat()

            deja_existant = db.get_import("qr_code", date_iso) is not None

            wb = build_report_workbook(df_classified, date_ref, source_label="ALBARKA")
            chemin = db.build_output_path("qr_code", date_iso)
            wb.save(chemin)
            save_qr_cache(df_classified, date_iso)
            db.save_import("qr_code", date_iso, date_iso, chemin, nb_lignes=len(df_classified))

            if deja_existant:
                st.info(f"Un traitement pour le {date_ref.strftime('%d/%m/%Y')} existait déjà : il a été remplacé.")
            st.success(f"{len(df_classified)} agents traités → {chemin.name}")

            counts = df_classified["statut"].value_counts()
            cols = st.columns(4)
            for col, statut in zip(cols, ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]):
                col.metric(statut, int(counts.get(statut, 0)))

            with open(chemin, "rb") as fh:
                st.download_button(
                    f"Télécharger {chemin.name}", data=fh.read(), file_name=chemin.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_qr"
                )
    except Exception as e:
        st.error(f"Erreur : {e}")
