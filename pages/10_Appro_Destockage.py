"""
pages/10_Appro_Destockage.py
=============================
Volet Approvisionnement / Destockage — Super Admin et Admin.

Deux onglets :
  1. Import   : dépôt du fichier SUIVI PERFORMANCES CCIAUX DTD (.xlsx)
                → parsing multi-mois → stockage en base
  2. Dashboard : vue agrégée par commercial et par mois
                (volumes, montants, classements)
"""

import streamlit as st
import pandas as pd

from core import db
from core.auth import require_role, show_user_badge
from core.appro import (
    import_appro_file,
    get_appro_par_mois,
    get_mois_disponibles_appro,
    get_appro,
)
from core.export import export_df_to_excel

st.set_page_config(page_title="Appro / Destockage — ALBARKA", layout="wide")

require_role("super_admin", "admin")
show_user_badge()

st.title("Approvisionnement / Destockage")
st.write("Suivi des performances CCIAUX — appros et destockages par commercial.")

tab_import, tab_dashboard = st.tabs(["Import", "Dashboard"])


# ===========================================================================
# ONGLET 1 : IMPORT
# ===========================================================================
with tab_import:
    st.subheader("Importer le fichier SUIVI PERFORMANCES CCIAUX DTD")
    st.write(
        "Le fichier peut couvrir plusieurs mois. Chaque bloc mensuel est "
        "détecté automatiquement. Un retraitement de la même date pour le "
        "même commercial écrase silencieusement les données existantes."
    )

    fichier = st.file_uploader(
        "Fichier Excel (.xlsx)", type=["xlsx"], key="up_appro"
    )

    if st.button("Importer", key="btn_import_appro") and fichier is not None:
        with st.spinner("Parsing en cours..."):
            try:
                fichier.seek(0)
                resultat = import_appro_file(fichier, source_fichier_label=fichier.name)

                st.success(
                    f"Import terminé — **{resultat['nb_lignes_inserees']}** lignes enregistrées."
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Commerciaux importés**")
                    if resultat["commerciaux_importes"]:
                        for nom in resultat["commerciaux_importes"]:
                            st.write(f"OK — {nom}")
                    else:
                        st.info("Aucun.")

                with col2:
                    st.markdown("**Commerciaux ignorés** (non trouvés en base)")
                    if resultat["commerciaux_ignores"]:
                        for nom in resultat["commerciaux_ignores"]:
                            st.write(f"Ignoré — {nom}")
                        st.caption(
                            "Ces noms n'ont pas de correspondance dans la base. "
                            "Vérifie que les comptes existent dans Administration."
                        )
                    else:
                        st.success("Tous les commerciaux ont été reconnus.")

                if resultat["avertissements"]:
                    st.divider()
                    st.markdown("**Avertissements**")
                    for w in resultat["avertissements"]:
                        st.warning(w)

            except Exception as e:
                st.error(f"Erreur lors de l'import : {e}")


# ===========================================================================
# ONGLET 2 : DASHBOARD
# ===========================================================================
with tab_dashboard:
    mois_dispo = get_mois_disponibles_appro()

    if not mois_dispo:
        st.info("Aucune donnée disponible. Importe d'abord un fichier dans l'onglet Import.")
        st.stop()

    # --- Sélection du mois ---
    mois_choisi = st.selectbox(
        "Mois",
        mois_dispo,
        format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
        key="sel_mois_appro_dashboard",
    )

    donnees = get_appro_par_mois(mois=mois_choisi)

    if not donnees:
        st.info(f"Aucune donnée pour {pd.Timestamp(mois_choisi + '-01').strftime('%B %Y').capitalize()}.")
        st.stop()

    df = pd.DataFrame(donnees)

    st.divider()

    # --- Métriques globales ---
    st.subheader("Vue globale du mois")

    total_nb_appro   = int(df["nb_appro"].sum())
    total_mt_appro   = float(df["montant_appro"].sum())
    total_nb_destoc  = int(df["nb_destockage"].sum())
    total_mt_destoc  = float(df["montant_destockage"].sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Nb appros (total)",        f"{total_nb_appro:,}")
    m2.metric("Montant appros",            f"{total_mt_appro:,.0f} FCFA")
    m3.metric("Nb destockages (total)",    f"{total_nb_destoc:,}")
    m4.metric("Montant destockages",       f"{total_mt_destoc:,.0f} FCFA")

    st.divider()

    # --- Tableau récapitulatif ---
    st.subheader("Récapitulatif par commercial")

    df_affich = df.copy()
    df_affich = df_affich.sort_values("montant_appro", ascending=False)
    df_affich["montant_appro"]      = df_affich["montant_appro"].map("{:,.0f}".format)
    df_affich["montant_destockage"] = df_affich["montant_destockage"].map("{:,.0f}".format)
    df_affich = df_affich.rename(columns={
        "dsm_name":          "Commercial",
        "nb_appro":          "Nb appros",
        "montant_appro":     "Montant appros (FCFA)",
        "nb_destockage":     "Nb destockages",
        "montant_destockage":"Montant destockages (FCFA)",
    })
    df_affich = df_affich.drop(columns=["mois"], errors="ignore")
    st.dataframe(df_affich, hide_index=True, use_container_width=True)

    st.divider()

    # --- Classements côte à côte ---
    st.subheader("Classements")

    col_a, col_d = st.columns(2)

    with col_a:
        st.markdown("#### Appros — Top par montant")
        df_top_a = (
            pd.DataFrame(donnees)
            .sort_values("montant_appro", ascending=False)
            [["dsm_name", "nb_appro", "montant_appro"]]
            .rename(columns={
                "dsm_name":     "Commercial",
                "nb_appro":     "Nb ops",
                "montant_appro":"Montant (FCFA)",
            })
        )
        df_top_a["Montant (FCFA)"] = df_top_a["Montant (FCFA)"].map("{:,.0f}".format)
        df_top_a.insert(0, "#", range(1, len(df_top_a) + 1))
        st.dataframe(df_top_a, hide_index=True, use_container_width=True)

    with col_d:
        st.markdown("#### Destockages — Top par montant")
        df_top_d = (
            pd.DataFrame(donnees)
            .sort_values("montant_destockage", ascending=False)
            [["dsm_name", "nb_destockage", "montant_destockage"]]
            .rename(columns={
                "dsm_name":          "Commercial",
                "nb_destockage":     "Nb ops",
                "montant_destockage":"Montant (FCFA)",
            })
        )
        df_top_d["Montant (FCFA)"] = df_top_d["Montant (FCFA)"].map("{:,.0f}".format)
        df_top_d.insert(0, "#", range(1, len(df_top_d) + 1))
        st.dataframe(df_top_d, hide_index=True, use_container_width=True)

    st.divider()

    # --- Évolution sur tous les mois disponibles ---
    st.subheader("Évolution mensuelle")

    tous_mois = get_appro_par_mois()
    if tous_mois:
        df_evol = pd.DataFrame(tous_mois)

        # Pivot appros
        col_evol_a, col_evol_d = st.columns(2)

        with col_evol_a:
            st.markdown("**Montant appros par commercial (tous mois)**")
            df_pivot_a = (
                df_evol.pivot_table(
                    index="dsm_name", columns="mois",
                    values="montant_appro", aggfunc="sum", fill_value=0
                )
                .reset_index()
                .rename(columns={"dsm_name": "Commercial"})
            )
            # Formater les colonnes de montants
            for col in df_pivot_a.columns:
                if col != "Commercial":
                    df_pivot_a[col] = df_pivot_a[col].map("{:,.0f}".format)
            st.dataframe(df_pivot_a, hide_index=True, use_container_width=True)

        with col_evol_d:
            st.markdown("**Montant destockages par commercial (tous mois)**")
            df_pivot_d = (
                df_evol.pivot_table(
                    index="dsm_name", columns="mois",
                    values="montant_destockage", aggfunc="sum", fill_value=0
                )
                .reset_index()
                .rename(columns={"dsm_name": "Commercial"})
            )
            for col in df_pivot_d.columns:
                if col != "Commercial":
                    df_pivot_d[col] = df_pivot_d[col].map("{:,.0f}".format)
            st.dataframe(df_pivot_d, hide_index=True, use_container_width=True)

    st.divider()

    # --- Détail jour par jour (expander) ---
    with st.expander(f"Détail journalier — {pd.Timestamp(mois_choisi + '-01').strftime('%B %Y').capitalize()}"):
        commerciaux_dispo = db.list_commerciaux()
        filtre_com = st.selectbox(
            "Commercial",
            [None] + commerciaux_dispo,
            format_func=lambda c: "Tous" if c is None else c["dsm_name"],
            key="filtre_com_detail_appro",
        )

        lignes_detail = get_appro(
            commercial_id=filtre_com["id"] if filtre_com else None,
            mois=mois_choisi,
        )

        if lignes_detail:
            df_detail = pd.DataFrame(lignes_detail)[
                ["dsm_name", "date_op", "type_op", "montant"]
            ].rename(columns={
                "dsm_name": "Commercial",
                "date_op":  "Date",
                "type_op":  "Type",
                "montant":  "Montant (FCFA)",
            })
            df_detail["Montant (FCFA)"] = df_detail["Montant (FCFA)"].map("{:,.0f}".format)
            df_detail["Type"] = df_detail["Type"].map(
                {"appro": "Appro", "destockage": "Destockage"}
            )
            st.dataframe(df_detail, hide_index=True, use_container_width=True)
        else:
            st.info("Aucune donnée journalière pour ce filtre.")

    # --- Export Excel dashboard ---
    st.divider()
    label_mois_appro = pd.Timestamp(mois_choisi + "-01").strftime("%B %Y").capitalize()

    # Résumé global mois (valeurs numériques pour l'export)
    df_recap_export = pd.DataFrame(donnees).rename(columns={
        "dsm_name":          "Commercial",
        "nb_appro":          "Nb appros",
        "montant_appro":     "Montant appros (FCFA)",
        "nb_destockage":     "Nb destockages",
        "montant_destockage":"Montant destockages (FCFA)",
    }).drop(columns=["mois"], errors="ignore").sort_values("Montant appros (FCFA)", ascending=False)

    # Classement appros (brut)
    df_cls_appro = (
        pd.DataFrame(donnees)
        .sort_values("montant_appro", ascending=False)
        [["dsm_name", "nb_appro", "montant_appro"]]
        .rename(columns={"dsm_name": "Commercial", "nb_appro": "Nb ops", "montant_appro": "Montant (FCFA)"})
        .reset_index(drop=True)
    )
    df_cls_appro.insert(0, "#", range(1, len(df_cls_appro) + 1))

    # Classement destockages (brut)
    df_cls_destoc = (
        pd.DataFrame(donnees)
        .sort_values("montant_destockage", ascending=False)
        [["dsm_name", "nb_destockage", "montant_destockage"]]
        .rename(columns={"dsm_name": "Commercial", "nb_destockage": "Nb ops", "montant_destockage": "Montant (FCFA)"})
        .reset_index(drop=True)
    )
    df_cls_destoc.insert(0, "#", range(1, len(df_cls_destoc) + 1))

    # Évolution mensuelle (pivot appros et destocs, valeurs numériques)
    sheets_appro = {
        f"Récap {label_mois_appro}": df_recap_export,
        "Classement Appros":         df_cls_appro,
        "Classement Destockages":    df_cls_destoc,
    }

    if tous_mois:
        df_evol_raw = pd.DataFrame(tous_mois)
        df_pivot_appro_export = (
            df_evol_raw.pivot_table(
                index="dsm_name", columns="mois",
                values="montant_appro", aggfunc="sum", fill_value=0
            ).reset_index().rename(columns={"dsm_name": "Commercial"})
        )
        df_pivot_destoc_export = (
            df_evol_raw.pivot_table(
                index="dsm_name", columns="mois",
                values="montant_destockage", aggfunc="sum", fill_value=0
            ).reset_index().rename(columns={"dsm_name": "Commercial"})
        )
        sheets_appro["Évolution Appros"] = df_pivot_appro_export
        sheets_appro["Évolution Destockages"] = df_pivot_destoc_export

    xlsx_appro = export_df_to_excel(
        sheets_appro,
        titre=f"Appro / Destockage — {label_mois_appro}",
        source_label="ALBARKA — Appro/Destockage",
    )
    st.download_button(
        label="Exporter le dashboard (Excel)",
        data=xlsx_appro,
        file_name=f"appro_destockage_{mois_choisi}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_appro_dashboard",
    )
