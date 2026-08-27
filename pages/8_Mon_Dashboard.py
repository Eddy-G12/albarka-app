"""
pages/8_Mon_Dashboard.py
=========================
Dashboard personnel — réservé au rôle Commercial.

Affiche uniquement les données du commercial connecté, filtrées par son
dsm_name (colonne présente dans le cache QR Code et dans transactions_momo).

Sections :
  1. QR Code — statuts de ses agents à la dernière date traitée
  2. QR Code — évolution entre deux dates (son périmètre uniquement)
  3. Cash in / Cash out — ses chiffres + son rang anonymisé dans le classement
"""

import streamlit as st
import pandas as pd

from core import db
from core.auth import require_role, show_user_badge, get_current_user
from core.cashflow import get_cashflow, top_flop_cashflow
from core.export import export_df_to_excel

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("commercial")
show_user_badge()

# ---------------------------------------------------------------------------
# Récupération du commercial connecté
# ---------------------------------------------------------------------------
user = get_current_user()
commercial = db.get_commercial_by_user_id(user["id"])

if not commercial:
    st.error(
        "Ton compte n'est pas encore lié à un profil commercial. "
        "Contacte l'administrateur."
    )
    st.stop()

dsm_name = commercial["dsm_name"]

st.title(f"Mon Dashboard — {user['nom']}")
st.caption(f"DSM : **{dsm_name}**")

# ---------------------------------------------------------------------------
# Helpers cache QR
# ---------------------------------------------------------------------------
CACHE_QR_DIR = db.DATA_DIR / "qr_code" / "_cache"
STATUTS_ORDER = ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]
STATUT_COLORS = {
    "Sans QR Code":          "#d62728",
    "QR non utilisé (+30j)": "#ff7f0e",
    "Risque inactivité":     "#ffbb78",
    "Actif":                 "#2ca02c",
}


def qr_cache_dates_available() -> list[str]:
    imports = db.list_imports("qr_code")
    return sorted(
        [imp["cle"] for imp in imports if (CACHE_QR_DIR / f"{imp['cle']}.csv").exists()],
        reverse=True,
    )


def load_cache_for_dsm(date_iso: str) -> pd.DataFrame:
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    df = pd.read_csv(path, dtype={"pos_msisdn": str})
    return df[df["dsm_name"] == dsm_name].copy()


# ===========================================================================
# SECTION 1 : QR Code — vue à la dernière date
# ===========================================================================
st.divider()
st.subheader("Mes agents — Statuts QR Code")

dates_dispo = qr_cache_dates_available()

if not dates_dispo:
    st.info("Aucune donnée QR Code disponible pour le moment.")
else:
    date_choisie = st.selectbox(
        "Date de référence",
        dates_dispo,
        format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
        key="sel_date_mon_dashboard",
    )

    df_moi = load_cache_for_dsm(date_choisie)

    if df_moi.empty:
        st.info(f"Aucun agent trouvé pour le DSM **{dsm_name}** à cette date.")
    else:
        total_moi = len(df_moi)
        counts = {s: int((df_moi["statut"] == s).sum()) for s in STATUTS_ORDER}

        # Métriques
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Mes agents", total_moi)
        c2.metric("Sans QR Code",          counts["Sans QR Code"])
        c3.metric("QR non utilisé (+30j)", counts["QR non utilisé (+30j)"])
        c4.metric("Risque inactivité",     counts["Risque inactivité"])
        c5.metric("Actif",                 counts["Actif"])

        # KPIs
        deployes = total_moi - counts["Sans QR Code"]
        taux_dep  = deployes / total_moi if total_moi else 0
        taux_util = counts["Actif"] / deployes if deployes else 0

        k1, k2 = st.columns(2)
        k1.metric("Taux de déploiement QR", f"{taux_dep:.1%}")
        k2.metric("Taux d'utilisation",     f"{taux_util:.1%}")

        # Tableau des agents prioritaires
        with st.expander("Agents à traiter en priorité"):
            prioritaires = df_moi[
                df_moi["statut"].isin(["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité"])
            ].copy()

            if prioritaires.empty:
                st.success("Tous tes agents sont actifs.")
            else:
                prioritaires = prioritaires.sort_values(
                    ["statut", "segment_group", "pos_name"]
                )
                cols_affich = [c for c in
                               ["statut", "segment_group", "pos_name", "pos_msisdn",
                                "days_since_last_use"]
                               if c in prioritaires.columns]
                rename = {
                    "statut": "Statut", "segment_group": "Segment",
                    "pos_name": "Agent", "pos_msisdn": "Téléphone",
                    "days_since_last_use": "Jours sans usage",
                }
                st.dataframe(
                    prioritaires[cols_affich].rename(columns=rename),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(f"{len(prioritaires)} agent(s) nécessitant une action.")

        # Export QR Code personnel
        label_date_qr = pd.Timestamp(date_choisie).strftime("%d/%m/%Y")
        df_statuts_export = pd.DataFrame([
            {"Statut": s, "Nb agents": counts[s]} for s in STATUTS_ORDER
        ])
        df_statuts_export["% du total"] = df_statuts_export["Nb agents"].apply(
            lambda n: f"{n / total_moi:.1%}" if total_moi else "—"
        )

        cols_all = [c for c in
                    ["statut", "segment_group", "pos_name", "pos_msisdn", "days_since_last_use"]
                    if c in df_moi.columns]
        rename_all = {
            "statut": "Statut", "segment_group": "Segment",
            "pos_name": "Agent", "pos_msisdn": "Téléphone",
            "days_since_last_use": "Jours sans usage",
        }
        df_tous_agents = df_moi[cols_all].rename(columns=rename_all).reset_index(drop=True)

        xlsx_qr_perso = export_df_to_excel(
            {
                "Résumé statuts":  df_statuts_export,
                "Tous mes agents": df_tous_agents,
            },
            titre=f"Mes agents QR Code — {label_date_qr}",
            source_label=f"ALBARKA — {dsm_name}",
        )
        st.download_button(
            label="Exporter mes agents QR Code (Excel)",
            data=xlsx_qr_perso,
            file_name=f"qr_perso_{date_choisie}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_qr_perso",
        )

    # ===========================================================================
    # SECTION 2 : QR Code — évolution entre deux dates
    # ===========================================================================
    st.divider()
    st.subheader("Mon évolution QR Code")

    if len(dates_dispo) < 2:
        st.info("Il faut au moins deux dates traitées pour afficher une évolution.")
    else:
        col_a, col_b = st.columns(2)
        date_a = col_a.selectbox(
            "Date A (plus ancienne)", dates_dispo,
            index=min(1, len(dates_dispo) - 1),
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key="evol_date_a",
        )
        date_b = col_b.selectbox(
            "Date B (plus récente)", dates_dispo,
            index=0,
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key="evol_date_b",
        )

        if date_a == date_b:
            st.warning("Sélectionne deux dates différentes.")
        else:
            df_a = load_cache_for_dsm(date_a)
            df_b = load_cache_for_dsm(date_b)

            if df_a.empty and df_b.empty:
                st.info(f"Aucune donnée pour le DSM **{dsm_name}** sur ces deux dates.")
            else:
                label_a = pd.Timestamp(date_a).strftime("%d/%m/%Y")
                label_b = pd.Timestamp(date_b).strftime("%d/%m/%Y")

                evol_rows = []
                for s in STATUTS_ORDER:
                    va = int((df_a["statut"] == s).sum()) if not df_a.empty else 0
                    vb = int((df_b["statut"] == s).sum()) if not df_b.empty else 0
                    evol_rows.append({
                        "Statut": s,
                        label_a: va,
                        label_b: vb,
                        "Évolution": vb - va,
                    })

                df_evol = pd.DataFrame(evol_rows)
                st.dataframe(df_evol, hide_index=True, use_container_width=True)

                # Ligne totale
                ta = len(df_a)
                tb = len(df_b)
                st.caption(
                    f"Périmètre : **{ta}** agents le {label_a} → **{tb}** agents le {label_b} "
                    f"({'+'  if tb >= ta else ''}{tb - ta})"
                )


# ===========================================================================
# SECTION 3 : Cash in / Cash out
# ===========================================================================
st.divider()
st.subheader("Mon Cash in / Cash out")

toutes_lignes = get_cashflow(commercial_id=commercial["id"])
mois_dispo = sorted({r["mois"] for r in toutes_lignes}, reverse=True)

if not mois_dispo:
    st.info(
        "Aucune donnée cash in / cash out disponible pour ton compte. "
        "Demande à l'administrateur d'importer tes fichiers de transactions."
    )
else:
    mois_choisi = st.selectbox(
        "Mois",
        mois_dispo,
        format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
        key="sel_mois_mon_dashboard",
    )

    mes_lignes = [r for r in toutes_lignes if r["mois"] == mois_choisi]

    if mes_lignes:
        ma_ligne = mes_lignes[0]

        m1, m2, m3 = st.columns(3)
        m1.metric("Cash in",        f"{ma_ligne['cash_in']:,.0f} FCFA")
        m2.metric("Cash out",       f"{ma_ligne['cash_out']:,.0f} FCFA")
        m3.metric("Nb transactions", ma_ligne["nb_transactions"])

        # Rang anonymisé dans les classements
        st.markdown("#### Mon rang")

        def _rang_anonymise(type_flux: str, label: str):
            classement = top_flop_cashflow(mois_choisi, type_flux, n=200, ordre="top")
            if not classement:
                return

            total_cls = len(classement)
            rang = next(
                (i + 1 for i, r in enumerate(classement) if r["commercial_id"] == commercial["id"]),
                None,
            )

            if rang is None:
                st.caption(f"{label} : non classé ce mois-ci.")
                return

            # Affiche le rang + les voisins anonymisés (±1)
            r_col1, r_col2 = st.columns([1, 3])
            r_col1.metric(f"Rang {label}", f"{rang} / {total_cls}")

            voisins = []
            for i, r in enumerate(classement):
                pos = i + 1
                if abs(pos - rang) <= 2:
                    if r["commercial_id"] == commercial["id"]:
                        voisins.append({
                            "Rang": pos,
                            "Commercial": f"**{user['nom']} (moi)**",
                            label: f"{r[type_flux]:,.0f} FCFA",
                        })
                    else:
                        voisins.append({
                            "Rang": pos,
                            "Commercial": f"Commercial #{pos}",
                            label: f"{r[type_flux]:,.0f} FCFA",
                        })

            if voisins:
                df_voisins = pd.DataFrame(voisins)
                r_col2.dataframe(df_voisins, hide_index=True, use_container_width=True)

        col_ci, col_co = st.columns(2)
        with col_ci:
            _rang_anonymise("cash_in", "Cash in")
        with col_co:
            _rang_anonymise("cash_out", "Cash out")

    # Historique mensuel personnel
    with st.expander("Historique mensuel"):
        df_histo = pd.DataFrame([
            {
                "Mois": pd.Timestamp(r["mois"] + "-01").strftime("%B %Y").capitalize(),
                "Cash in (FCFA)": f"{r['cash_in']:,.0f}",
                "Cash out (FCFA)": f"{r['cash_out']:,.0f}",
                "Nb transactions": r["nb_transactions"],
            }
            for r in toutes_lignes
        ])
        st.dataframe(df_histo, hide_index=True, use_container_width=True)

    # Export cash flow personnel
    label_mois_cf = pd.Timestamp(mois_choisi + "-01").strftime("%B %Y").capitalize()
    df_histo_export = pd.DataFrame([
        {
            "Mois": pd.Timestamp(r["mois"] + "-01").strftime("%B %Y").capitalize(),
            "Cash in (FCFA)": r["cash_in"],
            "Cash out (FCFA)": r["cash_out"],
            "Nb transactions": r["nb_transactions"],
        }
        for r in toutes_lignes
    ])

    xlsx_cashflow_perso = export_df_to_excel(
        {"Historique mensuel": df_histo_export},
        titre=f"Mon Cash Flow — {user['nom']}",
        source_label=f"ALBARKA — {dsm_name}",
    )
    st.download_button(
        label="Exporter mon historique cash flow (Excel)",
        data=xlsx_cashflow_perso,
        file_name=f"cashflow_perso_{user['nom'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_cashflow_perso",
    )
