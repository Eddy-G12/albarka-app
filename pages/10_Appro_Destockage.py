"""
pages/10_Appro_Destockage.py — v2
====================================
Volet Approvisionnement / Destockage.

Source v2 : calculé automatiquement depuis le TCD du classeur Transactions
lors du dépôt des CSV dans la page Transactions.
Aucun fichier séparé à déposer ici.

Super Admin et Admin consultent et exportent.
Commercial : ses propres données uniquement.

Onglets :
  1. Dashboard mensuel   — synthèse par commercial + classements
  2. Évolution mensuelle — courbes tous mois disponibles
  3. Détail journalier   — vue jour par jour filtrable
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from core import db
from core.auth import require_role, show_user_badge, get_role, get_current_user, is_commercial
from core.ui import apply_theme, show_page_header
from core.appro import (
    get_appro_par_mois,
    get_mois_disponibles_appro,
    get_appro_par_jour,
)
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin", "admin", "commercial")
show_user_badge()

role = get_role()
user = get_current_user()

show_page_header("Appro / Destockage", "Calculé depuis les TCD Transactions — par commercial et par jour")
st.divider()

# Contexte commercial
com_info = None
if is_commercial():
    com_info = db.get_commercial_by_user_id(user["id"])
    if not com_info:
        st.error("Ton compte n'est pas lié à un profil commercial. Contacte l'administrateur.")
        st.stop()

mois_dispo = get_mois_disponibles_appro()

if not mois_dispo:
    st.info(
        "Aucune donnée d'appro/destockage disponible. "
        "Les données sont calculées automatiquement lors du dépôt des fichiers CSV "
        "de transactions dans le module **Transactions** (pour les commerciaux ayant un alias)."
    )
    st.stop()

tab_dash, tab_evol, tab_detail = st.tabs([
    "Dashboard mensuel",
    "Évolution mensuelle",
    "Détail journalier",
])


# ===========================================================================
# ONGLET 1 — DASHBOARD MENSUEL
# ===========================================================================
with tab_dash:
    mois_sel = st.selectbox(
        "Mois",
        mois_dispo,
        format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
        key="sel_mois_appro",
    )
    label_mois = pd.Timestamp(mois_sel + "-01").strftime("%B %Y").capitalize()

    donnees = get_appro_par_mois(mois=mois_sel)

    # Filtrage commercial si rôle = commercial
    if is_commercial():
        donnees = [d for d in donnees if d["dsm_name"] == com_info["dsm_name"]]

    if not donnees:
        st.info(f"Aucune donnée pour {label_mois}.")
    else:
        df = pd.DataFrame(donnees)

        # Métriques globales réseau
        if not is_commercial():
            total_nb_appro  = int(df["nb_appro"].sum())
            total_mt_appro  = float(df["montant_appro"].sum())
            total_nb_destoc = int(df["nb_destockage"].sum())
            total_mt_destoc = float(df["montant_destockage"].sum())

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Nb appros (réseau)",      f"{total_nb_appro:,}")
            m2.metric("Montant appros",           f"{total_mt_appro:,.0f} FCFA")
            m3.metric("Nb destockages (réseau)",  f"{total_nb_destoc:,}")
            m4.metric("Montant destockages",      f"{total_mt_destoc:,.0f} FCFA")
            st.divider()

        # Tableau récapitulatif
        st.subheader(f"Récapitulatif par commercial — {label_mois}")
        df_aff = df.copy().sort_values("montant_appro", ascending=False)
        df_aff_fmt = df_aff.copy()
        df_aff_fmt["montant_appro"]      = df_aff_fmt["montant_appro"].map("{:,.0f}".format)
        df_aff_fmt["montant_destockage"] = df_aff_fmt["montant_destockage"].map("{:,.0f}".format)
        df_aff_fmt = df_aff_fmt.rename(columns={
            "dsm_name":          "Commercial",
            "nb_appro":          "Nb appros",
            "montant_appro":     "Montant appros (FCFA)",
            "nb_destockage":     "Nb destockages",
            "montant_destockage":"Montant destockages (FCFA)",
        }).drop(columns=["mois"], errors="ignore")
        st.dataframe(df_aff_fmt, hide_index=True, use_container_width=True)

        st.divider()

        # Graphique barres groupées
        if not is_commercial() and len(df) > 1:
            fig = go.Figure()
            df_chart = df.sort_values("montant_appro", ascending=False)
            fig.add_trace(go.Bar(
                name="Appros", x=df_chart["dsm_name"], y=df_chart["montant_appro"],
                marker_color="#2980B9",
                text=df_chart["montant_appro"].apply(lambda v: f"{v:,.0f}"),
                textposition="outside",
            ))
            fig.add_trace(go.Bar(
                name="Destockages", x=df_chart["dsm_name"], y=df_chart["montant_destockage"],
                marker_color="#8E44AD",
                text=df_chart["montant_destockage"].apply(lambda v: f"{v:,.0f}"),
                textposition="outside",
            ))
            fig.update_layout(
                barmode="group", title=f"Appros vs Destockages — {label_mois}",
                height=380, margin=dict(l=10, r=10, t=40, b=60),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickangle=-30), yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                font=dict(family="Arial"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Classements
        if not is_commercial():
            st.divider()
            col_ca, col_cd = st.columns(2)
            with col_ca:
                st.markdown("#### Top appros (montant)")
                df_top_a = (
                    df.sort_values("montant_appro", ascending=False)
                    [["dsm_name", "nb_appro", "montant_appro"]]
                    .rename(columns={"dsm_name": "Commercial",
                                     "nb_appro": "Nb ops",
                                     "montant_appro": "Montant (FCFA)"})
                )
                df_top_a.insert(0, "#", range(1, len(df_top_a) + 1))
                df_top_a["Montant (FCFA)"] = df_top_a["Montant (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_top_a, hide_index=True, use_container_width=True)

            with col_cd:
                st.markdown("#### Top destockages (montant)")
                df_top_d = (
                    df.sort_values("montant_destockage", ascending=False)
                    [["dsm_name", "nb_destockage", "montant_destockage"]]
                    .rename(columns={"dsm_name": "Commercial",
                                     "nb_destockage": "Nb ops",
                                     "montant_destockage": "Montant (FCFA)"})
                )
                df_top_d.insert(0, "#", range(1, len(df_top_d) + 1))
                df_top_d["Montant (FCFA)"] = df_top_d["Montant (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_top_d, hide_index=True, use_container_width=True)

        # Export Excel
        st.divider()
        df_export = df.copy().rename(columns={
            "dsm_name":          "Commercial",
            "nb_appro":          "Nb appros",
            "montant_appro":     "Montant appros (FCFA)",
            "nb_destockage":     "Nb destockages",
            "montant_destockage":"Montant destockages (FCFA)",
        }).drop(columns=["mois"], errors="ignore")

        xlsx_dash = export_df_to_excel(
            {f"Récap {label_mois}": df_export},
            titre=f"Appro / Destockage — {label_mois}",
            source_label="ALBARKA — Transactions",
        )
        st.download_button(
            "Exporter (Excel)",
            data=xlsx_dash,
            file_name=f"appro_{mois_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_appro_dash",
        )


# ===========================================================================
# ONGLET 2 — ÉVOLUTION MENSUELLE
# ===========================================================================
with tab_evol:
    st.subheader("Évolution mensuelle")

    tous_donnees = get_appro_par_mois()

    if is_commercial():
        tous_donnees = [d for d in tous_donnees if d["dsm_name"] == com_info["dsm_name"]]

    if not tous_donnees:
        st.info("Pas de données historiques disponibles.")
    else:
        df_evol = pd.DataFrame(tous_donnees)

        if not is_commercial():
            # Courbes réseau agrégées
            df_net = (
                df_evol.groupby("mois", as_index=False)
                .agg(montant_appro=("montant_appro","sum"),
                     montant_destockage=("montant_destockage","sum"))
                .sort_values("mois")
            )
            df_net["mois_label"] = df_net["mois"].apply(
                lambda m: pd.Timestamp(m + "-01").strftime("%b %Y")
            )

            rows_long = []
            for _, r in df_net.iterrows():
                rows_long.append({"Mois": r["mois_label"], "Montant (FCFA)": r["montant_appro"],      "Type": "Appros"})
                rows_long.append({"Mois": r["mois_label"], "Montant (FCFA)": r["montant_destockage"], "Type": "Destockages"})

            fig_evol = px.line(
                pd.DataFrame(rows_long),
                x="Mois", y="Montant (FCFA)", color="Type",
                markers=True, title="Évolution Appros / Destockages réseau",
                color_discrete_map={"Appros": "#2980B9", "Destockages": "#8E44AD"},
            )
            fig_evol.update_layout(
                height=380, margin=dict(l=10,r=10,t=40,b=60),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickangle=-30, showgrid=True, gridcolor="#EEEEEE"),
                yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                font=dict(family="Arial"),
            )
            st.plotly_chart(fig_evol, use_container_width=True)

            # Pivot tableau appros par commercial
            col_pa, col_pd = st.columns(2)
            with col_pa:
                st.markdown("**Montant appros par commercial × mois**")
                df_pivot_a = (
                    df_evol.pivot_table(
                        index="dsm_name", columns="mois",
                        values="montant_appro", aggfunc="sum", fill_value=0
                    ).reset_index().rename(columns={"dsm_name": "Commercial"})
                )
                df_pivot_a_fmt = df_pivot_a.copy()
                for col in df_pivot_a_fmt.columns:
                    if col != "Commercial":
                        df_pivot_a_fmt[col] = df_pivot_a_fmt[col].map("{:,.0f}".format)
                st.dataframe(df_pivot_a_fmt, hide_index=True, use_container_width=True)

            with col_pd:
                st.markdown("**Montant destockages par commercial × mois**")
                df_pivot_d = (
                    df_evol.pivot_table(
                        index="dsm_name", columns="mois",
                        values="montant_destockage", aggfunc="sum", fill_value=0
                    ).reset_index().rename(columns={"dsm_name": "Commercial"})
                )
                df_pivot_d_fmt = df_pivot_d.copy()
                for col in df_pivot_d_fmt.columns:
                    if col != "Commercial":
                        df_pivot_d_fmt[col] = df_pivot_d_fmt[col].map("{:,.0f}".format)
                st.dataframe(df_pivot_d_fmt, hide_index=True, use_container_width=True)

        else:
            # Vue commercial : courbes personnelles
            df_com_evol = df_evol.sort_values("mois")
            df_com_evol["mois_label"] = df_com_evol["mois"].apply(
                lambda m: pd.Timestamp(m + "-01").strftime("%b %Y")
            )
            fig_com = go.Figure()
            fig_com.add_trace(go.Scatter(
                x=df_com_evol["mois_label"], y=df_com_evol["montant_appro"],
                name="Appros", mode="lines+markers", marker_color="#2980B9",
            ))
            fig_com.add_trace(go.Scatter(
                x=df_com_evol["mois_label"], y=df_com_evol["montant_destockage"],
                name="Destockages", mode="lines+markers", marker_color="#8E44AD",
            ))
            fig_com.update_layout(
                title=f"Évolution — {com_info['dsm_name']}", height=360,
                margin=dict(l=10,r=10,t=40,b=60),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickangle=-30, showgrid=True, gridcolor="#EEEEEE"),
                yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                font=dict(family="Arial"),
            )
            st.plotly_chart(fig_com, use_container_width=True)

        # Export Excel évolution
        st.divider()
        sheets_evol: dict = {}
        if not is_commercial():
            sheets_evol["Pivot appros"]      = df_pivot_a
            sheets_evol["Pivot destockages"] = df_pivot_d
        else:
            df_com_export = df_evol[["mois","montant_appro","nb_appro",
                                      "montant_destockage","nb_destockage"]].rename(columns={
                "mois": "Mois",
                "montant_appro": "Montant appros (FCFA)",
                "nb_appro": "Nb appros",
                "montant_destockage": "Montant destockages (FCFA)",
                "nb_destockage": "Nb destockages",
            })
            sheets_evol[f"Évolution {com_info['dsm_name']}"] = df_com_export

        xlsx_evol = export_df_to_excel(
            sheets_evol,
            titre="Évolution Appro / Destockage",
            source_label="ALBARKA — Transactions",
        )
        st.download_button(
            "Exporter évolution (Excel)",
            data=xlsx_evol,
            file_name="appro_evolution.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_appro_evol",
        )


# ===========================================================================
# ONGLET 3 — DÉTAIL JOURNALIER
# ===========================================================================
with tab_detail:
    st.subheader("Détail journalier")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        if is_commercial():
            com_detail = com_info
        else:
            commerciaux_all = db.list_commerciaux()
            com_detail = col_f1.selectbox(
                "Commercial",
                [None] + commerciaux_all,
                format_func=lambda c: "Tous" if c is None else c["dsm_name"],
                key="sel_com_detail_appro",
            )

    mois_det = col_f2.selectbox(
        "Mois",
        [None] + mois_dispo,
        format_func=lambda m: "Tous les mois" if m is None else pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
        key="sel_mois_detail_appro",
    )

    type_det = col_f3.selectbox(
        "Type",
        [None, "appro", "destockage"],
        format_func=lambda t: "Tous" if t is None else t.capitalize(),
        key="sel_type_detail_appro",
    )

    lignes = get_appro_par_jour(
        commercial_id=com_detail["id"] if com_detail else None,
        mois=mois_det,
    )

    if type_det:
        lignes = [l for l in lignes if l["type_op"] == type_det]

    if not lignes:
        st.info("Aucune donnée pour ce filtre.")
    else:
        df_det = pd.DataFrame(lignes)[
            ["dsm_name", "date_op", "type_op", "nb_ops", "montant", "source_fichier"]
        ].rename(columns={
            "dsm_name":      "Commercial",
            "date_op":       "Date",
            "type_op":       "Type",
            "nb_ops":        "Nb ops",
            "montant":       "Montant (FCFA)",
            "source_fichier":"Fichier source",
        })
        df_det["Type"] = df_det["Type"].map({"appro": "Appro", "destockage": "Destockage"})
        df_det["Montant (FCFA)"] = df_det["Montant (FCFA)"].map("{:,.0f}".format)

        st.dataframe(df_det, hide_index=True, use_container_width=True)

        # Export
        xlsx_det = export_df_to_excel(
            {"Détail journalier": df_det},
            titre="Appro / Destockage — Détail journalier",
            source_label="ALBARKA — Transactions",
        )
        st.download_button(
            "Exporter détail (Excel)",
            data=xlsx_det,
            file_name="appro_detail.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_appro_det",
        )
