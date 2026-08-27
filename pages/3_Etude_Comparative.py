"""
pages/3_Etude_Comparative.py
=============================
Volet Étude comparative QR Code — Super Admin et Admin.
Compare deux dates, rapprochées par numéro de téléphone.
"""

import re
import streamlit as st
import pandas as pd
from datetime import date

from core import db
from core.auth import require_role, show_user_badge
from core.qr_code import read_qr_file, classify, build_report_workbook
from core.comparaison import build_comparative_workbook

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
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
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    df_classified[CACHE_COLUMNS].to_csv(path, index=False)


def load_qr_cache(date_iso: str) -> pd.DataFrame:
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    return pd.read_csv(path, dtype={"pos_msisdn": str})


def qr_cache_dates_available():
    imports = db.list_imports("qr_code")
    dates = []
    for imp in imports:
        if (CACHE_QR_DIR / f"{imp['cle']}.csv").exists():
            dates.append(imp["cle"])
    return sorted(dates, reverse=True)


st.title("Etude comparative QR Code")
st.write("Compare deux dates, rapprochées par numéro de téléphone.")

mode = st.radio(
    "Source des données",
    ["Réutiliser deux dates déjà traitées", "Déposer deux nouveaux fichiers"],
    key="mode_compare"
)

df_a = df_b = None
label_a = label_b = None

if mode == "Réutiliser deux dates déjà traitées":
    dates_dispo = qr_cache_dates_available()
    if len(dates_dispo) < 2:
        st.warning(
            "Il faut au moins deux dates déjà traitées dans le volet Suivi QR Code pour utiliser ce mode."
        )
    else:
        col1, col2 = st.columns(2)
        date_a_iso = col1.selectbox(
            "Date A (la plus ancienne)", dates_dispo,
            index=min(1, len(dates_dispo) - 1), key="sel_date_a"
        )
        date_b_iso = col2.selectbox(
            "Date B (la plus récente)", dates_dispo,
            index=0, key="sel_date_b"
        )
        if st.button("Comparer", key="btn_compare_cache"):
            if date_a_iso == date_b_iso:
                st.error("Choisis deux dates différentes.")
            else:
                df_a = load_qr_cache(date_a_iso)
                df_b = load_qr_cache(date_b_iso)
                label_a = pd.Timestamp(date_a_iso).strftime("%d/%m/%Y")
                label_b = pd.Timestamp(date_b_iso).strftime("%d/%m/%Y")

else:
    col1, col2 = st.columns(2)
    with col1:
        fichier_a = st.file_uploader(
            "Fichier A (date la plus ancienne)", type=["xlsx", "gz"], key="up_cmp_a"
        )
        default_a = date.today()
        date_devinee_a = False
        if fichier_a is not None:
            devinee_a = guess_date_from_filename(fichier_a.name)
            if devinee_a:
                default_a = devinee_a
                date_devinee_a = True
        date_a_input = st.date_input(
            "Date de référence A", value=default_a, key="date_cmp_a", format="DD/MM/YYYY"
        )
        if fichier_a is not None:
            if date_devinee_a:
                st.caption(f"Date détectée : **{default_a.strftime('%d/%m/%Y')}**")
            else:
                st.warning("Aucune date détectée dans le nom du fichier A — vérifie la date ci-dessus.")

    with col2:
        fichier_b = st.file_uploader(
            "Fichier B (date la plus récente)", type=["xlsx", "gz"], key="up_cmp_b"
        )
        default_b = date.today()
        date_devinee_b = False
        if fichier_b is not None:
            devinee_b = guess_date_from_filename(fichier_b.name)
            if devinee_b:
                default_b = devinee_b
                date_devinee_b = True
        date_b_input = st.date_input(
            "Date de référence B", value=default_b, key="date_cmp_b", format="DD/MM/YYYY"
        )
        if fichier_b is not None:
            if date_devinee_b:
                st.caption(f"Date détectée : **{default_b.strftime('%d/%m/%Y')}**")
            else:
                st.warning("Aucune date détectée dans le nom du fichier B — vérifie la date ci-dessus.")

    if st.button("Comparer", key="btn_compare_upload") and fichier_a is not None and fichier_b is not None:
        df_a = classify(read_qr_file(fichier_a), date_a_input)
        df_b = classify(read_qr_file(fichier_b), date_b_input)
        label_a = date_a_input.strftime("%d/%m/%Y")
        label_b = date_b_input.strftime("%d/%m/%Y")
        for f, d_ref, dfc in [(fichier_a, date_a_input, df_a), (fichier_b, date_b_input, df_b)]:
            d_iso = d_ref.isoformat()
            chemin = db.build_output_path("qr_code", d_iso)
            build_report_workbook(dfc, d_ref, source_label="ALBARKA").save(chemin)
            save_qr_cache(dfc, d_iso)
            db.save_import("qr_code", d_iso, d_iso, chemin, nb_lignes=len(dfc))

if df_a is not None and df_b is not None:
    try:
        wb = build_comparative_workbook(df_a, df_b, label_a, label_b, source_label="ALBARKA")
        date_a_iso_out = pd.to_datetime(label_a, dayfirst=True).date().isoformat()
        date_b_iso_out = pd.to_datetime(label_b, dayfirst=True).date().isoformat()
        cle_compare = f"{date_a_iso_out}_vs_{date_b_iso_out}"
        chemin = db.build_output_path("comparatif", cle_compare)
        wb.save(chemin)
        db.save_import("comparatif", cle_compare, date_b_iso_out, chemin, nb_lignes=len(df_a) + len(df_b))

        st.success(f"Comparaison générée : {label_a} → {label_b}")

        resume = pd.DataFrame({
            "Statut": ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"],
            label_a: [int((df_a["statut"] == s).sum()) for s in
                      ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]],
            label_b: [int((df_b["statut"] == s).sum()) for s in
                      ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]],
        })
        st.dataframe(resume, hide_index=True, use_container_width=True)

        with open(chemin, "rb") as fh:
            st.download_button(
                f"Télécharger {chemin.name}", data=fh.read(), file_name=chemin.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_compare"
            )
    except Exception as e:
        st.error(f"Erreur lors de la comparaison : {e}")
