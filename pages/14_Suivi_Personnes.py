"""
pages/14_Suivi_Personnes.py
============================
Suivi des personnes spécialement suivies.
Super Admin exclusivement (saisie et gestion).

Fonctionnement :
  - Pour chacun des commerciaux concernés (Césaire, Antoine, Parfait, Erve, Stéphane),
    saisie du nom de la personne spécialement suivie, du montant associé,
    avec la date et l'heure.
  - L'appli conserve, jour après jour, la liste des personnes suivies et
    le montant total cumulé associé à chacune.

Commerciaux concernés : CESAIRE, ANTOINE, PARFAIT, ERVE, STEPHANE
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from core import db
from core.auth import require_role, show_user_badge
from core.ui import apply_theme, show_page_header
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin")
show_user_badge()

show_page_header("Suivi Personnes", "Suivi des personnes spécialement suivies — saisie manuelle")
st.divider()

# ── Commerciaux concernés ─────────────────────────────────────────────────────
DSM_CONCERNES = ["CESAIRE", "ANTOINE", "PARFAIT", "ERVE", "STEPHANE"]

# Récupérer les commerciaux depuis la base et filtrer ceux concernés
tous_commerciaux = db.list_commerciaux()
commerciaux_concernes = [
    c for c in tous_commerciaux
    if c["dsm_name"].upper() in DSM_CONCERNES
]

if not commerciaux_concernes:
    st.warning(
        "Aucun des commerciaux concernés (Césaire, Antoine, Parfait, Erve, Stéphane) "
        "n'est trouvé en base. Vérifie que leurs comptes existent dans Administration."
    )
    st.stop()

tab_saisie, tab_dashboard, tab_suppression = st.tabs([
    "Saisie", "Dashboard", "Gestion"
])


# ===========================================================================
# ONGLET 1 — SAISIE
# ===========================================================================
with tab_saisie:
    st.subheader("Enregistrer une entrée")
    st.caption(
        "Sélectionne le commercial, entre le nom de la personne suivie, "
        "le montant associé et la date/heure."
    )

    with st.form("form_suivi", clear_on_submit=True):
        col1, col2 = st.columns(2)
        com_sel = col1.selectbox(
            "Commercial",
            commerciaux_concernes,
            format_func=lambda c: c["dsm_name"],
            key="sel_com_suivi",
        )
        nom_personne = col2.text_input("Nom de la personne suivie")

        col3, col4, col5 = st.columns(3)
        montant = col3.number_input(
            "Montant (FCFA)", min_value=0, step=1000, value=0, key="montant_suivi"
        )
        date_s = col4.date_input("Date", value=date.today(), key="date_suivi")
        heure_s = col5.time_input("Heure", value=datetime.now().time(), key="heure_suivi")

        submitted = st.form_submit_button("Enregistrer", use_container_width=True, type="primary")
        if submitted:
            if not nom_personne.strip():
                st.error("Le nom de la personne est obligatoire.")
            elif montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                date_heure_str = f"{date_s} {heure_s.strftime('%H:%M:%S')}"
                try:
                    db.save_suivi_personne(
                        commercial_id=com_sel["id"],
                        nom_personne=nom_personne.strip(),
                        montant=float(montant),
                        date_heure=date_heure_str,
                    )
                    st.success(
                        f"✅ Enregistré — **{nom_personne.strip()}** pour "
                        f"**{com_sel['dsm_name']}** : {montant:,.0f} FCFA "
                        f"le {date_s.strftime('%d/%m/%Y')} à {heure_s.strftime('%H:%M')}."
                    )
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # Aperçu des dernières entrées
    st.divider()
    st.markdown("**Dernières entrées enregistrées**")
    recents = db.get_suivi_personnes()
    if recents:
        df_rec = pd.DataFrame(recents[:20])
        df_rec = df_rec[["dsm_name", "nom_personne", "montant", "date_heure"]].rename(columns={
            "dsm_name":    "Commercial",
            "nom_personne":"Personne suivie",
            "montant":     "Montant (FCFA)",
            "date_heure":  "Date/Heure",
        })
        df_rec["Montant (FCFA)"] = df_rec["Montant (FCFA)"].map("{:,.0f}".format)
        st.dataframe(df_rec, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune entrée enregistrée.")


# ===========================================================================
# ONGLET 2 — DASHBOARD
# ===========================================================================
with tab_dashboard:
    st.subheader("Dashboard — personnes suivies")

    # Filtres
    col_f1, col_f2, col_f3 = st.columns(3)
    com_filtre = col_f1.selectbox(
        "Commercial",
        [None] + commerciaux_concernes,
        format_func=lambda c: "Tous" if c is None else c["dsm_name"],
        key="sel_com_dash_suivi",
    )
    date_deb_d = col_f2.date_input("Du", value=date.today().replace(day=1), key="deb_suivi_d")
    date_fin_d = col_f3.date_input("Au", value=date.today(), key="fin_suivi_d")

    donnees = db.get_suivi_personnes(
        commercial_id=com_filtre["id"] if com_filtre else None,
        date_debut=str(date_deb_d),
        date_fin=str(date_fin_d),
    )

    if not donnees:
        st.info("Aucune donnée sur cette période.")
    else:
        df = pd.DataFrame(donnees)

        # ── Synthèse par commercial × personne ──────────────────────────────
        st.markdown("#### Cumul par commercial × personne suivie")
        df_synthese = (
            df.groupby(["dsm_name", "nom_personne"], as_index=False)["montant"]
            .agg(["sum", "count"])
            .rename(columns={
                "dsm_name":    "Commercial",
                "nom_personne":"Personne suivie",
                "sum":         "Montant cumulé (FCFA)",
                "count":       "Nb entrées",
            })
            .sort_values(["Commercial", "Montant cumulé (FCFA)"], ascending=[True, False])
            .reset_index(drop=True)
        )
        df_synthese["Montant cumulé (FCFA)"] = df_synthese["Montant cumulé (FCFA)"].map("{:,.0f}".format)
        st.dataframe(df_synthese, hide_index=True, use_container_width=True)

        # ── Métriques globales ───────────────────────────────────────────────
        st.divider()
        total_montant = float(df["montant"].sum())
        nb_personnes  = df["nom_personne"].nunique()
        nb_entrees    = len(df)

        m1, m2, m3 = st.columns(3)
        m1.metric("Montant total cumulé",  f"{total_montant:,.0f} FCFA")
        m2.metric("Personnes distinctes",  nb_personnes)
        m3.metric("Nb entrées",            f"{nb_entrees:,}")

        # ── Tableau chronologique ────────────────────────────────────────────
        st.divider()
        st.markdown("#### Historique chronologique")
        df_chrono = df[["dsm_name","nom_personne","montant","date_heure"]].copy()
        df_chrono = df_chrono.rename(columns={
            "dsm_name":    "Commercial",
            "nom_personne":"Personne suivie",
            "montant":     "Montant (FCFA)",
            "date_heure":  "Date/Heure",
        }).sort_values("Date/Heure", ascending=False)
        df_chrono["Montant (FCFA)"] = df_chrono["Montant (FCFA)"].map("{:,.0f}".format)
        st.dataframe(df_chrono, hide_index=True, use_container_width=True)

        # ── Export Excel ────────────────────────────────────────────────────
        st.divider()
        # Reconstruire les DataFrames avec valeurs numériques pour l'export
        df_synthese_export = (
            df.groupby(["dsm_name", "nom_personne"], as_index=False)["montant"]
            .agg(["sum", "count"])
            .rename(columns={
                "dsm_name":    "Commercial",
                "nom_personne":"Personne suivie",
                "sum":         "Montant cumulé (FCFA)",
                "count":       "Nb entrées",
            })
        )
        df_chrono_export = df[["dsm_name","nom_personne","montant","date_heure"]].rename(columns={
            "dsm_name":    "Commercial",
            "nom_personne":"Personne suivie",
            "montant":     "Montant (FCFA)",
            "date_heure":  "Date/Heure",
        }).sort_values("Date/Heure", ascending=False)

        label_periode = (
            f"{date_deb_d.strftime('%d/%m/%Y')} — {date_fin_d.strftime('%d/%m/%Y')}"
        )
        xlsx = export_df_to_excel(
            {
                "Synthèse":    df_synthese_export,
                "Historique":  df_chrono_export,
            },
            titre=f"Suivi Personnes — {label_periode}",
            source_label="ALBARKA — Suivi Personnes",
        )
        st.download_button(
            "Exporter (Excel)",
            data=xlsx,
            file_name=f"suivi_personnes_{date_deb_d}_{date_fin_d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_suivi_p",
        )


# ===========================================================================
# ONGLET 3 — GESTION (SUPPRESSION)
# ===========================================================================
with tab_suppression:
    st.subheader("Supprimer des entrées")
    st.caption(
        "Affiche les entrées filtrables et permet la suppression individuelle. "
        "La suppression est définitive."
    )

    col_sg1, col_sg2 = st.columns(2)
    com_sup = col_sg1.selectbox(
        "Commercial",
        [None] + commerciaux_concernes,
        format_func=lambda c: "Tous" if c is None else c["dsm_name"],
        key="sel_com_sup_suivi",
    )
    date_sup_d = col_sg2.date_input("Date", value=date.today(), key="date_sup_suivi")

    entrees = db.get_suivi_personnes(
        commercial_id=com_sup["id"] if com_sup else None,
        date_debut=str(date_sup_d),
        date_fin=str(date_sup_d),
    )

    if not entrees:
        st.info("Aucune entrée pour ce filtre.")
    else:
        for e in entrees:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.markdown(f"**{e['dsm_name']}** — {e['nom_personne']}")
                c2.write(f"{e['montant']:,.0f} FCFA")
                c3.caption(e["date_heure"])
                if c4.button("Supprimer", key=f"sup_sv_{e['id']}"):
                    st.session_state[f"conf_sv_{e['id']}"] = True

                if st.session_state.get(f"conf_sv_{e['id']}"):
                    st.warning(
                        f"Supprimer l'entrée **{e['nom_personne']}** "
                        f"({e['montant']:,.0f} FCFA) ?"
                    )
                    c_y, c_n = st.columns(2)
                    if c_y.button("Confirmer", key=f"conf_y_sv_{e['id']}", type="primary"):
                        db.delete_suivi_personne(e["id"])
                        st.session_state.pop(f"conf_sv_{e['id']}", None)
                        st.success("Entrée supprimée.")
                        st.rerun()
                    if c_n.button("Annuler", key=f"conf_n_sv_{e['id']}"):
                        st.session_state.pop(f"conf_sv_{e['id']}", None)
                        st.rerun()
