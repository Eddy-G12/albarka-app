"""
pages/13_MoMo_App.py
=====================
MoMo App — Suivi des parrainages Mobile Money.
Super Admin exclusivement (saisie et gestion).

Fonctionnement :
  - Sélection d'une personne dans une liste prédéfinie
  - Saisie du nombre de parrainages effectués ce jour-là
  - Cumul automatique jour après jour, par personne
  - Export Excel sur une période choisie : jour par jour + total par personne

Personnes suivies (liste fixe, extensible depuis l'interface) :
  Antoine, Parfait, Erve, Ewane, Stéphane, Theo, Nathan
  + 2 personnes dont le nom sera précisé ultérieurement (slots "Personne 8", "Personne 9")
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from core import db
from core.auth import require_role, show_user_badge
from core.ui import apply_theme, show_page_header
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin")
show_user_badge()

show_page_header("MoMo App — Parrainages", "Saisie et suivi des parrainages Mobile Money")
st.divider()

# ── Liste des personnes suivies ───────────────────────────────────────────────
PERSONNES_DEFAUT = [
    "Antoine", "Parfait", "Erve", "Ewane", "Stéphane",
    "Theo", "Nathan", "Personne 8", "Personne 9",
]

# Permet d'ajouter des personnes via la session (non persistant, mais pratique)
if "momo_personnes_extra" not in st.session_state:
    st.session_state["momo_personnes_extra"] = []

toutes_personnes = PERSONNES_DEFAUT + st.session_state["momo_personnes_extra"]

tab_saisie, tab_dashboard, tab_gestion = st.tabs([
    "Saisie", "Dashboard", "Gestion des personnes"
])


# ===========================================================================
# ONGLET 1 — SAISIE
# ===========================================================================
with tab_saisie:
    st.subheader("Enregistrer des parrainages")
    st.caption(
        "Sélectionne une personne, entre le nombre de parrainages effectués "
        "à la date choisie, puis clique sur Enregistrer. "
        "Le total est cumulé automatiquement (si tu entres 3 pour aujourd'hui "
        "puis 2 pour aujourd'hui, le total sera 5)."
    )

    with st.form("form_parrainage", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        personne = col1.selectbox("Personne", toutes_personnes, key="sel_personne_p")
        date_p   = col2.date_input("Date", value=date.today(), key="date_p")
        nb_p     = col3.number_input(
            "Nb parrainages", min_value=1, max_value=500, value=1, step=1, key="nb_p"
        )
        submitted = st.form_submit_button("Enregistrer", use_container_width=True, type="primary")

        if submitted:
            try:
                db.save_parrainage(personne, str(date_p), int(nb_p))
                st.success(
                    f"✅ **{nb_p}** parrainage(s) enregistré(s) pour **{personne}** "
                    f"le {date_p.strftime('%d/%m/%Y')}."
                )
            except Exception as e:
                st.error(f"Erreur : {e}")

    # Aperçu des dernières saisies
    st.divider()
    st.markdown("**Dernières saisies (7 derniers jours)**")
    date_min_apercu = str(date.today() - timedelta(days=7))
    recents = db.get_parrainages(date_debut=date_min_apercu)
    if recents:
        df_rec = pd.DataFrame(recents)[["personne", "date_op", "nb"]].rename(columns={
            "personne": "Personne", "date_op": "Date", "nb": "Nb parrainages"
        })
        df_rec = df_rec.sort_values(["Date", "Personne"], ascending=[False, True])
        st.dataframe(df_rec, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune saisie sur les 7 derniers jours.")


# ===========================================================================
# ONGLET 2 — DASHBOARD
# ===========================================================================
with tab_dashboard:
    st.subheader("Tableau de bord des parrainages")

    col_d1, col_d2 = st.columns(2)
    date_deb = col_d1.date_input("Du", value=date.today().replace(day=1), key="deb_parr")
    date_fin = col_d2.date_input("Au", value=date.today(), key="fin_parr")

    if date_deb > date_fin:
        st.warning("La date de début doit être antérieure à la date de fin.")
    else:
        donnees = db.get_parrainages(
            date_debut=str(date_deb),
            date_fin=str(date_fin),
        )

        if not donnees:
            st.info("Aucun parrainage enregistré sur cette période.")
        else:
            df = pd.DataFrame(donnees)

            # ── Synthèse par personne ────────────────────────────────────────
            st.markdown("#### Totaux par personne")
            df_synthese = (
                df.groupby("personne", as_index=False)["nb"]
                .sum()
                .rename(columns={"personne": "Personne", "nb": "Total parrainages"})
                .sort_values("Total parrainages", ascending=False)
                .reset_index(drop=True)
            )
            df_synthese.insert(0, "#", range(1, len(df_synthese) + 1))

            total_global = int(df_synthese["Total parrainages"].sum())
            st.metric("Total réseau sur la période", f"{total_global:,}")
            st.dataframe(df_synthese, hide_index=True, use_container_width=True)

            # ── Graphique barres ────────────────────────────────────────────
            try:
                import plotly.graph_objects as go
                fig = go.Figure(go.Bar(
                    x=df_synthese["Personne"],
                    y=df_synthese["Total parrainages"],
                    marker_color="#F5A623",
                    text=df_synthese["Total parrainages"],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="Parrainages par personne",
                    height=360,
                    margin=dict(l=10, r=10, t=40, b=60),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(tickangle=-30),
                    yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                    font=dict(family="Arial"),
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass

            # ── Tableau jour par jour ───────────────────────────────────────
            st.divider()
            st.markdown("#### Détail jour par jour")

            # Pivot : dates en colonnes, personnes en lignes
            df_pivot = df.pivot_table(
                index="personne", columns="date_op", values="nb",
                aggfunc="sum", fill_value=0
            ).reset_index()
            df_pivot.columns.name = None
            df_pivot = df_pivot.rename(columns={"personne": "Personne"})

            # Renommer les colonnes de date en format lisible
            date_cols = [c for c in df_pivot.columns if c != "Personne"]
            rename_dates = {
                d: pd.Timestamp(d).strftime("%d/%m") for d in date_cols
            }
            df_pivot = df_pivot.rename(columns=rename_dates)

            # Ajouter colonne Total
            df_pivot["Total"] = df_pivot[list(rename_dates.values())].sum(axis=1)
            df_pivot = df_pivot.sort_values("Total", ascending=False)

            st.dataframe(df_pivot, hide_index=True, use_container_width=True)

            # ── Export Excel ────────────────────────────────────────────────
            st.divider()

            # DataFrame brut pour l'export (valeurs numériques)
            df_export_detail = df[["personne", "date_op", "nb"]].rename(columns={
                "personne": "Personne", "date_op": "Date", "nb": "Nb parrainages"
            }).sort_values(["Date", "Personne"])

            label_periode = (
                f"{date_deb.strftime('%d/%m/%Y')} — {date_fin.strftime('%d/%m/%Y')}"
            )
            xlsx = export_df_to_excel(
                {
                    "Synthèse":             df_synthese.drop(columns=["#"]),
                    "Détail journalier":    df_export_detail,
                    "Pivot":                df_pivot,
                },
                titre=f"Parrainages MoMo — {label_periode}",
                source_label="ALBARKA — MoMo App",
            )
            st.download_button(
                "Exporter (Excel)",
                data=xlsx,
                file_name=f"parrainages_{date_deb}_{date_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_parr",
            )


# ===========================================================================
# ONGLET 3 — GESTION DES PERSONNES
# ===========================================================================
with tab_gestion:
    st.subheader("Gestion des personnes suivies")

    st.markdown("**Personnes prédéfinies**")
    st.dataframe(
        pd.DataFrame({"Personne": PERSONNES_DEFAUT}),
        hide_index=True, use_container_width=True,
    )

    st.divider()
    st.markdown("**Ajouter une personne (session courante)**")
    st.caption(
        "L'ajout est temporaire (valable pendant la session). "
        "Pour un ajout permanent, modifie la liste PERSONNES_DEFAUT dans le code."
    )

    with st.form("form_add_personne"):
        new_personne = st.text_input("Nom de la personne")
        if st.form_submit_button("Ajouter"):
            if new_personne.strip() and new_personne.strip() not in toutes_personnes:
                st.session_state["momo_personnes_extra"].append(new_personne.strip())
                st.success(f"**{new_personne.strip()}** ajouté pour cette session.")
                st.rerun()
            elif new_personne.strip() in toutes_personnes:
                st.warning("Cette personne est déjà dans la liste.")
            else:
                st.error("Nom vide.")

    # Suppression d'entrées individuelles
    st.divider()
    st.markdown("**Supprimer des enregistrements**")
    st.caption("Supprime un enregistrement spécifique (personne × date) de la base.")

    col_sp, col_sd = st.columns(2)
    personne_sup = col_sp.selectbox(
        "Personne", toutes_personnes, key="sel_sup_personne"
    )
    date_sup = col_sd.date_input("Date", value=date.today(), key="date_sup")

    entr_existante = db.get_parrainages(
        personne=personne_sup,
        date_debut=str(date_sup),
        date_fin=str(date_sup),
    )

    if entr_existante:
        nb_existant = entr_existante[0]["nb"]
        st.info(
            f"Enregistrement trouvé : **{nb_existant}** parrainage(s) "
            f"pour **{personne_sup}** le {date_sup.strftime('%d/%m/%Y')}."
        )
        if st.button("Supprimer cet enregistrement", key="btn_sup_parr"):
            db.delete_parrainage(personne_sup, str(date_sup))
            st.success("Enregistrement supprimé.")
            st.rerun()
    else:
        st.info(f"Aucun enregistrement pour **{personne_sup}** le {date_sup.strftime('%d/%m/%Y')}.")
