"""
pages/6_Cash_Flow.py
=====================
Volet Cash in / Cash out — Super Admin et Admin.

Trois sections accessibles via des onglets :
  1. Import        : dépôt du listing Mobile Money d'un commercial → calcul → stockage
  2. Classements   : Top 20 / Flop 20 cash in et cash out pour un mois donné
  3. Alertes seuil : commerciaux sous le seuil configuré pour un mois donné
"""

import streamlit as st
import pandas as pd

from core import db
from core.auth import require_role, show_user_badge, get_current_user
from core.cashflow import (
    import_cashflow_file,
    get_cashflow,
    top_flop_cashflow,
    list_alertes_seuil,
    match_commercial_by_filename,
)
from core.export import export_df_to_excel

st.set_page_config(page_title="Cash Flow — ALBARKA", layout="wide")

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
show_user_badge()

st.title("Cash in / Cash out")

tab_import, tab_classements, tab_alertes = st.tabs([
    "Import",
    "Classements",
    "Alertes seuil",
])


# ===========================================================================
# ONGLET 1 : IMPORT
# ===========================================================================
with tab_import:
    st.subheader("Importer un listing Mobile Money")
    st.write(
        "Dépose le fichier CSV d'un commercial. Le compte propre est détecté "
        "automatiquement. Le cash in / cash out est calculé mois par mois et "
        "stocké en base (un retraitement du même fichier écrase les données existantes)."
    )

    commerciaux = db.list_commerciaux()
    if not commerciaux:
        st.warning("Aucun commercial trouvé en base. Créez d'abord les comptes dans Administration.")
        st.stop()

    fichier_csv = st.file_uploader("Fichier CSV de transactions", type=["csv"], key="up_cashflow")

    # Pré-sélection du commercial depuis le nom de fichier
    commercial_selectionne = None
    if fichier_csv is not None:
        match = match_commercial_by_filename(fichier_csv.name, commerciaux)
        if match:
            noms = [c["dsm_name"] for c in commerciaux]
            idx_defaut = noms.index(match["dsm_name"])
            st.caption(f"Commercial détecté depuis le nom du fichier : **{match['dsm_name']}**")
        else:
            idx_defaut = 0
            st.warning(
                "Impossible de détecter le commercial depuis le nom du fichier "
                "— sélectionne-le manuellement ci-dessous."
            )
        commercial_selectionne = st.selectbox(
            "Commercial",
            commerciaux,
            index=idx_defaut,
            format_func=lambda c: c["dsm_name"],
            key="sel_commercial_cashflow",
        )
    else:
        commercial_selectionne = st.selectbox(
            "Commercial",
            commerciaux,
            format_func=lambda c: c["dsm_name"],
            key="sel_commercial_cashflow_empty",
        )

    if st.button("Calculer et enregistrer", key="btn_import_cashflow") and fichier_csv is not None:
        try:
            # Reset du curseur si déjà lu par le file_uploader
            fichier_csv.seek(0)
            resultat = import_cashflow_file(
                fichier_csv,
                commercial_id=commercial_selectionne["id"],
                source_fichier_label=fichier_csv.name,
            )

            compte = resultat["compte_propre_detecte"]
            par_mois = resultat["par_mois"]

            st.success(
                f"Import réussi — compte propre détecté : **{compte}** — "
                f"{len(par_mois)} mois enregistré(s)."
            )

            # Tableau récapitulatif des mois importés
            rows = []
            for mois, vals in sorted(par_mois.items()):
                rows.append({
                    "Mois": mois,
                    "Cash in (FCFA)": vals["cash_in"],
                    "Cash out (FCFA)": vals["cash_out"],
                    "Nb transactions": vals["nb_transactions"],
                })
            df_recap = pd.DataFrame(rows)
            df_recap["Cash in (FCFA)"] = df_recap["Cash in (FCFA)"].map("{:,.0f}".format)
            df_recap["Cash out (FCFA)"] = df_recap["Cash out (FCFA)"].map("{:,.0f}".format)
            st.dataframe(df_recap, hide_index=True, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors de l'import : {e}")


# ===========================================================================
# ONGLET 2 : CLASSEMENTS
# ===========================================================================
with tab_classements:
    st.subheader("Classements Top 20 / Flop 20")
    st.write(
        "Sélectionne un mois pour afficher les classements cash in et cash out "
        "de façon **indépendante** (un commercial peut être Top cash in et Flop cash out)."
    )

    # Liste des mois disponibles en base
    toutes_lignes = get_cashflow()
    mois_disponibles = sorted({r["mois"] for r in toutes_lignes}, reverse=True)

    if not mois_disponibles:
        st.info("Aucune donnée cash in / cash out en base. Importe d'abord des fichiers dans l'onglet Import.")
    else:
        mois_choisi = st.selectbox(
            "Mois", mois_disponibles,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_classements",
        )

        n_affiche = st.slider("Nombre de commerciaux à afficher", 5, 20, 10, key="slider_n_classements")

        st.divider()

        col_ci, col_co = st.columns(2)

        # ---------- CASH IN ----------
        with col_ci:
            st.markdown("#### Cash In")
            sub_col1, sub_col2 = st.columns(2)

            with sub_col1:
                st.markdown("**Top**")
                top_ci = top_flop_cashflow(mois_choisi, "cash_in", n=n_affiche, ordre="top")
                if top_ci:
                    df_top_ci = pd.DataFrame([
                        {"#": i + 1, "Commercial": r["dsm_name"], "Cash in (FCFA)": r["cash_in"]}
                        for i, r in enumerate(top_ci)
                    ])
                    df_top_ci["Cash in (FCFA)"] = df_top_ci["Cash in (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_top_ci, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

            with sub_col2:
                st.markdown("**Flop**")
                flop_ci = top_flop_cashflow(mois_choisi, "cash_in", n=n_affiche, ordre="flop")
                if flop_ci:
                    df_flop_ci = pd.DataFrame([
                        {"#": i + 1, "Commercial": r["dsm_name"], "Cash in (FCFA)": r["cash_in"]}
                        for i, r in enumerate(flop_ci)
                    ])
                    df_flop_ci["Cash in (FCFA)"] = df_flop_ci["Cash in (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_flop_ci, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

        # ---------- CASH OUT ----------
        with col_co:
            st.markdown("#### Cash Out")
            sub_col3, sub_col4 = st.columns(2)

            with sub_col3:
                st.markdown("**Top**")
                top_co = top_flop_cashflow(mois_choisi, "cash_out", n=n_affiche, ordre="top")
                if top_co:
                    df_top_co = pd.DataFrame([
                        {"#": i + 1, "Commercial": r["dsm_name"], "Cash out (FCFA)": r["cash_out"]}
                        for i, r in enumerate(top_co)
                    ])
                    df_top_co["Cash out (FCFA)"] = df_top_co["Cash out (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_top_co, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

            with sub_col4:
                st.markdown("**Flop**")
                flop_co = top_flop_cashflow(mois_choisi, "cash_out", n=n_affiche, ordre="flop")
                if flop_co:
                    df_flop_co = pd.DataFrame([
                        {"#": i + 1, "Commercial": r["dsm_name"], "Cash out (FCFA)": r["cash_out"]}
                        for i, r in enumerate(flop_co)
                    ])
                    df_flop_co["Cash out (FCFA)"] = df_flop_co["Cash out (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_flop_co, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

        st.divider()

        # Vue complète du mois
        with st.expander("Voir toutes les données du mois"):
            lignes_mois = get_cashflow(mois=mois_choisi)
            if lignes_mois:
                df_mois = pd.DataFrame([
                    {
                        "Commercial": r["dsm_name"],
                        "Cash in (FCFA)": r["cash_in"],
                        "Cash out (FCFA)": r["cash_out"],
                        "Nb transactions": r["nb_transactions"],
                    }
                    for r in lignes_mois
                ]).sort_values("Cash in (FCFA)", ascending=False)
                df_mois["Cash in (FCFA)"] = df_mois["Cash in (FCFA)"].map("{:,.0f}".format)
                df_mois["Cash out (FCFA)"] = df_mois["Cash out (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_mois, hide_index=True, use_container_width=True)
            else:
                st.info("Pas de données pour ce mois.")

        # --- Export Excel classements ---
        st.divider()
        label_mois = pd.Timestamp(mois_choisi + "-01").strftime("%B %Y").capitalize()

        # Reconstruction des DataFrames bruts (valeurs numériques) pour l'export
        def _df_raw(records, col_flux, label_col):
            return pd.DataFrame([
                {"#": i + 1, "Commercial": r["dsm_name"], label_col: r[col_flux]}
                for i, r in enumerate(records)
            ]) if records else pd.DataFrame()

        sheets_classements = {}
        if top_ci:
            sheets_classements["Top Cash In"] = _df_raw(top_ci, "cash_in", "Cash in (FCFA)")
        if flop_ci:
            sheets_classements["Flop Cash In"] = _df_raw(flop_ci, "cash_in", "Cash in (FCFA)")
        if top_co:
            sheets_classements["Top Cash Out"] = _df_raw(top_co, "cash_out", "Cash out (FCFA)")
        if flop_co:
            sheets_classements["Flop Cash Out"] = _df_raw(flop_co, "cash_out", "Cash out (FCFA)")

        # Onglet complet du mois (valeurs brutes)
        lignes_export = get_cashflow(mois=mois_choisi)
        if lignes_export:
            sheets_classements["Données complètes"] = pd.DataFrame([
                {
                    "Commercial": r["dsm_name"],
                    "Cash in (FCFA)": r["cash_in"],
                    "Cash out (FCFA)": r["cash_out"],
                    "Nb transactions": r["nb_transactions"],
                }
                for r in lignes_export
            ]).sort_values("Cash in (FCFA)", ascending=False)

        if sheets_classements:
            xlsx_classements = export_df_to_excel(
                sheets_classements,
                titre=f"Cash Flow — Classements — {label_mois}",
                source_label="ALBARKA — Cash Flow",
            )
            st.download_button(
                label="Exporter les classements (Excel)",
                data=xlsx_classements,
                file_name=f"cashflow_classements_{mois_choisi}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_classements_cashflow",
            )


# ===========================================================================
# ONGLET 3 : ALERTES SEUIL
# ===========================================================================
with tab_alertes:
    st.subheader("Alertes — commerciaux sous le seuil")
    st.write(
        "Liste les commerciaux dont le cash in ou le cash out du mois est "
        "**inférieur au seuil configuré**. Les seuils se configurent dans "
        "Administration → Seuils cash in / cash out."
    )

    toutes_lignes_alertes = get_cashflow()
    mois_disponibles_alertes = sorted({r["mois"] for r in toutes_lignes_alertes}, reverse=True)

    if not mois_disponibles_alertes:
        st.info("Aucune donnée en base. Importe d'abord des fichiers dans l'onglet Import.")
    else:
        mois_alerte = st.selectbox(
            "Mois",
            mois_disponibles_alertes,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_alertes",
        )

        alertes = list_alertes_seuil(mois_alerte)

        col_seuils_a, col_seuils_b = st.columns(2)
        col_seuils_a.metric(
            "Seuil cash in",
            f"{alertes['seuil_cash_in']:,.0f} FCFA" if alertes["seuil_cash_in"] else "Non défini",
        )
        col_seuils_b.metric(
            "Seuil cash out",
            f"{alertes['seuil_cash_out']:,.0f} FCFA" if alertes["seuil_cash_out"] else "Non défini",
        )

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Cash in sous le seuil")
            sous_ci = alertes["commerciaux_sous_seuil_cash_in"]
            if not alertes["seuil_cash_in"]:
                st.info("Aucun seuil cash in configuré.")
            elif not sous_ci:
                st.success("Tous les commerciaux sont au-dessus du seuil.")
            else:
                for r in sous_ci:
                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        c1.markdown(f"**{r['dsm_name']}**")
                        c2.markdown(
                            f"<span style='color:red'>{r['cash_in']:,.0f} FCFA</span>",
                            unsafe_allow_html=True,
                        )

        with col_b:
            st.markdown("#### Cash out sous le seuil")
            sous_co = alertes["commerciaux_sous_seuil_cash_out"]
            if not alertes["seuil_cash_out"]:
                st.info("Aucun seuil cash out configuré.")
            elif not sous_co:
                st.success("Tous les commerciaux sont au-dessus du seuil.")
            else:
                for r in sous_co:
                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        c1.markdown(f"**{r['dsm_name']}**")
                        c2.markdown(
                            f"<span style='color:red'>{r['cash_out']:,.0f} FCFA</span>",
                            unsafe_allow_html=True,
                        )

        if alertes["seuil_cash_in"] or alertes["seuil_cash_out"]:
            total_alertes = len(alertes["commerciaux_sous_seuil_cash_in"]) + len(alertes["commerciaux_sous_seuil_cash_out"])
            if total_alertes:
                st.warning(
                    f"{total_alertes} alerte(s) détectée(s) pour "
                    f"{pd.Timestamp(mois_alerte + '-01').strftime('%B %Y').capitalize()}. "
                    "Pense à ajuster les seuils dans Administration si besoin."
                )

        # --- Export Excel alertes ---
        st.divider()
        label_mois_alerte = pd.Timestamp(mois_alerte + "-01").strftime("%B %Y").capitalize()
        sheets_alertes = {}

        sous_ci_export = alertes.get("commerciaux_sous_seuil_cash_in", [])
        sous_co_export = alertes.get("commerciaux_sous_seuil_cash_out", [])

        if sous_ci_export:
            sheets_alertes["Alerte Cash In"] = pd.DataFrame([
                {
                    "Commercial": r["dsm_name"],
                    "Cash in (FCFA)": r["cash_in"],
                    "Seuil (FCFA)": alertes["seuil_cash_in"],
                    "Écart (FCFA)": r["cash_in"] - alertes["seuil_cash_in"],
                }
                for r in sous_ci_export
            ])
        if sous_co_export:
            sheets_alertes["Alerte Cash Out"] = pd.DataFrame([
                {
                    "Commercial": r["dsm_name"],
                    "Cash out (FCFA)": r["cash_out"],
                    "Seuil (FCFA)": alertes["seuil_cash_out"],
                    "Écart (FCFA)": r["cash_out"] - alertes["seuil_cash_out"],
                }
                for r in sous_co_export
            ])

        if sheets_alertes:
            xlsx_alertes = export_df_to_excel(
                sheets_alertes,
                titre=f"Cash Flow — Alertes seuil — {label_mois_alerte}",
                source_label="ALBARKA — Cash Flow",
            )
            st.download_button(
                label="Exporter les alertes (Excel)",
                data=xlsx_alertes,
                file_name=f"cashflow_alertes_{mois_alerte}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_alertes_cashflow",
            )
        else:
            st.info("Aucune alerte à exporter pour ce mois.")
