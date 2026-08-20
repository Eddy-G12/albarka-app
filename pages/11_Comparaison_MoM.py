"""
pages/11_Comparaison_MoM.py
============================
Comparaisons Month-over-Month (MoM) — Super Admin, Admin et Commercial.

Trois onglets :
  1. Cash in / Cash out  — évolution entre deux mois (valeur + %)
  2. Appro / Destockage  — évolution des montants et volumes
  3. QR Code             — évolution des statuts entre deux dates

Droits :
  - Super Admin / Admin : vue de tous les commerciaux
  - Commercial          : uniquement ses propres données (dsm_name filtré)
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from core import db
from core.auth import require_role, show_user_badge, get_current_user, get_role, is_commercial
from core.cashflow import get_cashflow
from core.appro import get_appro_par_mois, get_mois_disponibles_appro
from core.export import export_df_to_excel

st.set_page_config(page_title="Comparaisons MoM — ALBARKA", layout="wide")

require_role("super_admin", "admin", "commercial")
show_user_badge()

# ---------------------------------------------------------------------------
# Contexte utilisateur
# ---------------------------------------------------------------------------
user       = get_current_user()
role       = get_role()
vue_perso  = is_commercial()  # True → afficher uniquement ses données

commercial_connecte = None
if vue_perso:
    commercial_connecte = db.get_commercial_by_user_id(user["id"])
    if not commercial_connecte:
        st.error("Ton compte n'est pas lié à un profil commercial. Contacte l'administrateur.")
        st.stop()

st.title("Comparaisons Month-over-Month")
if vue_perso:
    st.caption(f"Vue personnelle — **{commercial_connecte['dsm_name']}**")
else:
    st.caption("Vue globale — tous les commerciaux")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATUTS_QR = ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]
CACHE_QR_DIR = db.DATA_DIR / "qr_code" / "_cache"


def _mois_precedent(mois_iso: str) -> str:
    """Retourne le mois précédent au format AAAA-MM."""
    dt = datetime.strptime(mois_iso + "-01", "%Y-%m-%d")
    if dt.month == 1:
        return f"{dt.year - 1}-12"
    return f"{dt.year}-{dt.month - 1:02d}"


def _fmt_montant(v) -> str:
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return "—"


def _fmt_evol(v, is_pct=False) -> str:
    """Formate une évolution avec signe + / -."""
    try:
        f = float(v)
        if is_pct:
            return f"{f:+.1f}%"
        return f"{f:+,.0f}"
    except Exception:
        return "—"


def _evol_pct(a, b) -> float | None:
    """Calcule l'évolution en % de a vers b."""
    try:
        a, b = float(a), float(b)
        if a == 0:
            return None
        return (b - a) / a * 100
    except Exception:
        return None


def _color_evol(val) -> str:
    """Retourne une couleur HTML selon le signe de l'évolution."""
    try:
        if float(str(val).replace(",", "").replace("+", "")) > 0:
            return "color: #2ca02c"
        if float(str(val).replace(",", "").replace("+", "")) < 0:
            return "color: #d62728"
    except Exception:
        pass
    return ""


def _load_qr_cache(date_iso: str) -> pd.DataFrame:
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"pos_msisdn": str})


def _qr_dates_disponibles() -> list[str]:
    imports = db.list_imports("qr_code")
    return sorted(
        [imp["cle"] for imp in imports if (CACHE_QR_DIR / f"{imp['cle']}.csv").exists()],
        reverse=True,
    )


# ===========================================================================
# ONGLETS
# ===========================================================================
tab_cash, tab_appro, tab_qr = st.tabs([
    "Cash in / Cash out",
    "Appro / Destockage",
    "QR Code",
])


# ===========================================================================
# ONGLET 1 : CASH IN / CASH OUT MoM
# ===========================================================================
with tab_cash:
    st.subheader("Cash in / Cash out — évolution mensuelle")

    # Récupère toutes les lignes disponibles
    if vue_perso:
        toutes_lignes = get_cashflow(commercial_id=commercial_connecte["id"])
    else:
        toutes_lignes = get_cashflow()

    mois_cash = sorted({r["mois"] for r in toutes_lignes}, reverse=True)

    if len(mois_cash) < 1:
        st.info("Aucune donnée cash in / cash out disponible.")
    else:
        mois_m = st.selectbox(
            "Mois de référence (M)",
            mois_cash,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_cash_mom",
        )
        mois_m1 = _mois_precedent(mois_m)

        lignes_m  = {r["dsm_name"]: r for r in toutes_lignes if r["mois"] == mois_m}
        lignes_m1 = {r["dsm_name"]: r for r in toutes_lignes if r["mois"] == mois_m1}

        label_m  = pd.Timestamp(mois_m  + "-01").strftime("%B %Y").capitalize()
        label_m1 = pd.Timestamp(mois_m1 + "-01").strftime("%B %Y").capitalize()

        if not lignes_m1:
            st.info(f"Aucune donnée pour {label_m1} (mois précédent) — impossible de calculer l'évolution.")
        else:
            # Construire le tableau comparatif
            noms = sorted(set(lignes_m.keys()) | set(lignes_m1.keys()))
            rows = []
            for nom in noms:
                r_m  = lignes_m.get(nom, {})
                r_m1 = lignes_m1.get(nom, {})

                ci_m  = float(r_m.get("cash_in",  0))
                ci_m1 = float(r_m1.get("cash_in", 0))
                co_m  = float(r_m.get("cash_out",  0))
                co_m1 = float(r_m1.get("cash_out", 0))

                evol_ci     = ci_m - ci_m1
                evol_ci_pct = _evol_pct(ci_m1, ci_m)
                evol_co     = co_m - co_m1
                evol_co_pct = _evol_pct(co_m1, co_m)

                rows.append({
                    "Commercial":          nom,
                    f"Cash in {label_m1}": _fmt_montant(ci_m1),
                    f"Cash in {label_m}":  _fmt_montant(ci_m),
                    "Évol. CI (FCFA)":     _fmt_evol(evol_ci),
                    "Évol. CI (%)":        _fmt_evol(evol_ci_pct, is_pct=True) if evol_ci_pct is not None else "—",
                    f"Cash out {label_m1}":_fmt_montant(co_m1),
                    f"Cash out {label_m}": _fmt_montant(co_m),
                    "Évol. CO (FCFA)":     _fmt_evol(evol_co),
                    "Évol. CO (%)":        _fmt_evol(evol_co_pct, is_pct=True) if evol_co_pct is not None else "—",
                })

            df_cash = pd.DataFrame(rows)
            st.dataframe(df_cash, hide_index=True, use_container_width=True)

            # Métriques synthèse
            st.divider()
            st.markdown(f"**Synthèse réseau — {label_m1} → {label_m}**")
            total_ci_m  = sum(float(lignes_m.get(n,  {}).get("cash_in",  0)) for n in noms)
            total_ci_m1 = sum(float(lignes_m1.get(n, {}).get("cash_in",  0)) for n in noms)
            total_co_m  = sum(float(lignes_m.get(n,  {}).get("cash_out", 0)) for n in noms)
            total_co_m1 = sum(float(lignes_m1.get(n, {}).get("cash_out", 0)) for n in noms)

            s1, s2, s3, s4 = st.columns(4)
            s1.metric(f"Cash in {label_m}",  f"{total_ci_m:,.0f} FCFA",
                      delta=f"{total_ci_m - total_ci_m1:+,.0f}")
            s2.metric(f"Cash in {label_m1}", f"{total_ci_m1:,.0f} FCFA")
            s3.metric(f"Cash out {label_m}",  f"{total_co_m:,.0f} FCFA",
                      delta=f"{total_co_m - total_co_m1:+,.0f}")
            s4.metric(f"Cash out {label_m1}", f"{total_co_m1:,.0f} FCFA")

            # Export Excel Cash MoM
            st.divider()
            # Reconstruire df avec valeurs numériques pour l'export
            rows_export_cash = []
            for nom in noms:
                r_m  = lignes_m.get(nom, {})
                r_m1 = lignes_m1.get(nom, {})
                ci_m_  = float(r_m.get("cash_in",  0))
                ci_m1_ = float(r_m1.get("cash_in", 0))
                co_m_  = float(r_m.get("cash_out",  0))
                co_m1_ = float(r_m1.get("cash_out", 0))
                rows_export_cash.append({
                    "Commercial":              nom,
                    f"Cash in {label_m1}":     ci_m1_,
                    f"Cash in {label_m}":      ci_m_,
                    "Évol. CI (FCFA)":         ci_m_ - ci_m1_,
                    f"Cash out {label_m1}":    co_m1_,
                    f"Cash out {label_m}":     co_m_,
                    "Évol. CO (FCFA)":         co_m_ - co_m1_,
                })
            df_cash_export = pd.DataFrame(rows_export_cash)
            df_synthese_cash = pd.DataFrame([
                {"Indicateur": f"Cash in {label_m}",   "Valeur (FCFA)": total_ci_m},
                {"Indicateur": f"Cash in {label_m1}",  "Valeur (FCFA)": total_ci_m1},
                {"Indicateur": "Évol. Cash in (FCFA)", "Valeur (FCFA)": total_ci_m - total_ci_m1},
                {"Indicateur": f"Cash out {label_m}",  "Valeur (FCFA)": total_co_m},
                {"Indicateur": f"Cash out {label_m1}", "Valeur (FCFA)": total_co_m1},
                {"Indicateur": "Évol. Cash out (FCFA)","Valeur (FCFA)": total_co_m - total_co_m1},
            ])
            xlsx_cash_mom = export_df_to_excel(
                {
                    f"Comparaison {label_m1} vs {label_m}": df_cash_export,
                    "Synthèse réseau":                       df_synthese_cash,
                },
                titre=f"Cash MoM — {label_m1} → {label_m}",
                source_label="ALBARKA — Comparaison MoM",
            )
            st.download_button(
                label="Exporter Cash MoM (Excel)",
                data=xlsx_cash_mom,
                file_name=f"cash_mom_{mois_m1}_vs_{mois_m}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_cash_mom",
            )


# ===========================================================================
# ONGLET 2 : APPRO / DESTOCKAGE MoM
# ===========================================================================
with tab_appro:
    st.subheader("Appro / Destockage — évolution mensuelle")

    mois_appro = get_mois_disponibles_appro()

    if len(mois_appro) < 1:
        st.info("Aucune donnée appro / destockage disponible.")
    else:
        mois_a = st.selectbox(
            "Mois de référence (M)",
            mois_appro,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_appro_mom",
        )
        mois_a1 = _mois_precedent(mois_a)

        label_a  = pd.Timestamp(mois_a  + "-01").strftime("%B %Y").capitalize()
        label_a1 = pd.Timestamp(mois_a1 + "-01").strftime("%B %Y").capitalize()

        donnees_m  = get_appro_par_mois(mois=mois_a)
        donnees_m1 = get_appro_par_mois(mois=mois_a1)

        # Filtrage si vue commerciale
        if vue_perso:
            dsm = commercial_connecte["dsm_name"]
            donnees_m  = [d for d in donnees_m  if d["dsm_name"] == dsm]
            donnees_m1 = [d for d in donnees_m1 if d["dsm_name"] == dsm]

        idx_m  = {d["dsm_name"]: d for d in donnees_m}
        idx_m1 = {d["dsm_name"]: d for d in donnees_m1}

        if not idx_m1:
            st.info(f"Aucune donnée pour {label_a1} — impossible de calculer l'évolution.")
        else:
            noms = sorted(set(idx_m.keys()) | set(idx_m1.keys()))
            rows_a = []
            for nom in noms:
                d_m  = idx_m.get(nom,  {})
                d_m1 = idx_m1.get(nom, {})

                mt_a_m  = float(d_m.get("montant_appro",      0))
                mt_a_m1 = float(d_m1.get("montant_appro",     0))
                mt_d_m  = float(d_m.get("montant_destockage",  0))
                mt_d_m1 = float(d_m1.get("montant_destockage", 0))

                rows_a.append({
                    "Commercial":           nom,
                    f"Appro {label_a1}":    _fmt_montant(mt_a_m1),
                    f"Appro {label_a}":     _fmt_montant(mt_a_m),
                    "Évol. Appro (FCFA)":   _fmt_evol(mt_a_m - mt_a_m1),
                    "Évol. Appro (%)":      _fmt_evol(_evol_pct(mt_a_m1, mt_a_m), is_pct=True)
                                            if _evol_pct(mt_a_m1, mt_a_m) is not None else "—",
                    f"Destoc {label_a1}":   _fmt_montant(mt_d_m1),
                    f"Destoc {label_a}":    _fmt_montant(mt_d_m),
                    "Évol. Destoc (FCFA)":  _fmt_evol(mt_d_m - mt_d_m1),
                    "Évol. Destoc (%)":     _fmt_evol(_evol_pct(mt_d_m1, mt_d_m), is_pct=True)
                                            if _evol_pct(mt_d_m1, mt_d_m) is not None else "—",
                })

            df_appro_mom = pd.DataFrame(rows_a)
            st.dataframe(df_appro_mom, hide_index=True, use_container_width=True)

            # Synthèse réseau
            if not vue_perso:
                st.divider()
                st.markdown(f"**Synthèse réseau — {label_a1} → {label_a}**")
                ta_m  = sum(float(idx_m.get(n,  {}).get("montant_appro",      0)) for n in noms)
                ta_m1 = sum(float(idx_m1.get(n, {}).get("montant_appro",      0)) for n in noms)
                td_m  = sum(float(idx_m.get(n,  {}).get("montant_destockage",  0)) for n in noms)
                td_m1 = sum(float(idx_m1.get(n, {}).get("montant_destockage",  0)) for n in noms)

                s1, s2, s3, s4 = st.columns(4)
                s1.metric(f"Appros {label_a}",   f"{ta_m:,.0f} FCFA",  delta=f"{ta_m - ta_m1:+,.0f}")
                s2.metric(f"Appros {label_a1}",  f"{ta_m1:,.0f} FCFA")
                s3.metric(f"Destocs {label_a}",  f"{td_m:,.0f} FCFA",  delta=f"{td_m - td_m1:+,.0f}")
                s4.metric(f"Destocs {label_a1}", f"{td_m1:,.0f} FCFA")

        # Export Excel Appro MoM (toujours disponible dès qu'on a les données)
        if idx_m1:
            st.divider()
            rows_export_appro = []
            for nom in noms:
                d_m_  = idx_m.get(nom,  {})
                d_m1_ = idx_m1.get(nom, {})
                mt_a_m_  = float(d_m_.get("montant_appro",      0))
                mt_a_m1_ = float(d_m1_.get("montant_appro",     0))
                mt_d_m_  = float(d_m_.get("montant_destockage",  0))
                mt_d_m1_ = float(d_m1_.get("montant_destockage", 0))
                rows_export_appro.append({
                    "Commercial":           nom,
                    f"Appro {label_a1}":    mt_a_m1_,
                    f"Appro {label_a}":     mt_a_m_,
                    "Évol. Appro (FCFA)":   mt_a_m_ - mt_a_m1_,
                    f"Destoc {label_a1}":   mt_d_m1_,
                    f"Destoc {label_a}":    mt_d_m_,
                    "Évol. Destoc (FCFA)":  mt_d_m_ - mt_d_m1_,
                })
            df_appro_export = pd.DataFrame(rows_export_appro)
            xlsx_appro_mom = export_df_to_excel(
                {f"Comparaison {label_a1} vs {label_a}": df_appro_export},
                titre=f"Appro/Destoc MoM — {label_a1} → {label_a}",
                source_label="ALBARKA — Comparaison MoM",
            )
            st.download_button(
                label="Exporter Appro/Destoc MoM (Excel)",
                data=xlsx_appro_mom,
                file_name=f"appro_mom_{mois_a1}_vs_{mois_a}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_appro_mom",
            )


# ===========================================================================
# ONGLET 3 : QR CODE MoM
# ===========================================================================
with tab_qr:
    st.subheader("QR Code — évolution entre deux dates")

    dates_qr = _qr_dates_disponibles()

    if len(dates_qr) < 2:
        st.info(
            "Il faut au moins deux dates traitées dans le volet Suivi QR Code "
            "pour afficher une évolution."
        )
    else:
        col_q1, col_q2 = st.columns(2)
        date_m1_qr = col_q1.selectbox(
            "Date antérieure (M-1)",
            dates_qr,
            index=min(1, len(dates_qr) - 1),
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key="sel_date_m1_qr_mom",
        )
        date_m_qr = col_q2.selectbox(
            "Date récente (M)",
            dates_qr,
            index=0,
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key="sel_date_m_qr_mom",
        )

        if date_m1_qr == date_m_qr:
            st.warning("Sélectionne deux dates différentes.")
        else:
            df_m1 = _load_qr_cache(date_m1_qr)
            df_m  = _load_qr_cache(date_m_qr)

            label_qr_m1 = pd.Timestamp(date_m1_qr).strftime("%d/%m/%Y")
            label_qr_m  = pd.Timestamp(date_m_qr).strftime("%d/%m/%Y")

            # Filtrage si vue commerciale
            if vue_perso and not df_m.empty:
                dsm = commercial_connecte["dsm_name"]
                df_m1 = df_m1[df_m1["dsm_name"] == dsm] if not df_m1.empty else df_m1
                df_m  = df_m[df_m["dsm_name"] == dsm]

            if df_m.empty and df_m1.empty:
                st.info("Aucune donnée QR Code pour les dates sélectionnées.")
            else:
                # --- Tableau global des statuts ---
                st.markdown(f"#### Répartition globale — {label_qr_m1} → {label_qr_m}")

                rows_qr = []
                tot_m1 = len(df_m1)
                tot_m  = len(df_m)
                for statut in STATUTS_QR:
                    n_m1 = int((df_m1["statut"] == statut).sum()) if not df_m1.empty else 0
                    n_m  = int((df_m["statut"]  == statut).sum()) if not df_m.empty  else 0
                    evol = n_m - n_m1
                    pct_m1 = f"{n_m1 / tot_m1:.1%}" if tot_m1 else "—"
                    pct_m  = f"{n_m  / tot_m:.1%}"  if tot_m  else "—"
                    rows_qr.append({
                        "Statut":           statut,
                        f"{label_qr_m1}":   n_m1,
                        f"% {label_qr_m1}": pct_m1,
                        f"{label_qr_m}":    n_m,
                        f"% {label_qr_m}":  pct_m,
                        "Évolution":        f"{evol:+d}",
                    })
                # Ligne Total
                rows_qr.append({
                    "Statut":           "TOTAL",
                    f"{label_qr_m1}":   tot_m1,
                    f"% {label_qr_m1}": "100%",
                    f"{label_qr_m}":    tot_m,
                    f"% {label_qr_m}":  "100%",
                    "Évolution":        f"{tot_m - tot_m1:+d}",
                })

                st.dataframe(pd.DataFrame(rows_qr), hide_index=True, use_container_width=True)

                # --- Tableau par DSM ---
                if not vue_perso:
                    st.divider()
                    st.markdown("#### Évolution par DSM")

                    dsm_list = sorted(
                        set(df_m1["dsm_name"].dropna()) | set(df_m["dsm_name"].dropna())
                    )
                    rows_dsm = []
                    for dsm in dsm_list:
                        sub_m1 = df_m1[df_m1["dsm_name"] == dsm] if not df_m1.empty else pd.DataFrame()
                        sub_m  = df_m[df_m["dsm_name"]   == dsm] if not df_m.empty  else pd.DataFrame()
                        row = {"DSM": dsm, f"Total {label_qr_m1}": len(sub_m1), f"Total {label_qr_m}": len(sub_m)}
                        for statut in STATUTS_QR:
                            n1 = int((sub_m1["statut"] == statut).sum()) if not sub_m1.empty else 0
                            n2 = int((sub_m["statut"]  == statut).sum()) if not sub_m.empty  else 0
                            row[f"{statut[:12]} M-1"] = n1
                            row[f"{statut[:12]} M"]   = n2
                            row[f"Δ {statut[:10]}"]   = f"{n2 - n1:+d}"
                        rows_dsm.append(row)

                    st.dataframe(pd.DataFrame(rows_dsm), hide_index=True, use_container_width=True)

                # --- KPIs MoM ---
                st.divider()
                st.markdown("#### KPIs MoM")

                def _kpi(label, n_m1, n_m, tot_m1, tot_m):
                    pct_m1 = n_m1 / tot_m1 if tot_m1 else 0
                    pct_m  = n_m  / tot_m  if tot_m  else 0
                    delta  = pct_m - pct_m1
                    st.metric(
                        label,
                        f"{pct_m:.1%}",
                        delta=f"{delta:+.1f}%",
                        delta_color="normal" if "Actif" in label else "inverse",
                    )

                k1, k2, k3, k4 = st.columns(4)
                dep_m1  = tot_m1 - int((df_m1["statut"] == "Sans QR Code").sum()) if not df_m1.empty else 0
                dep_m   = tot_m  - int((df_m["statut"]  == "Sans QR Code").sum()) if not df_m.empty  else 0
                actif_m1 = int((df_m1["statut"] == "Actif").sum()) if not df_m1.empty else 0
                actif_m  = int((df_m["statut"]  == "Actif").sum()) if not df_m.empty  else 0
                risque_m1 = int((df_m1["statut"] == "Risque inactivité").sum()) if not df_m1.empty else 0
                risque_m  = int((df_m["statut"]  == "Risque inactivité").sum()) if not df_m.empty  else 0
                nonutil_m1 = int((df_m1["statut"] == "QR non utilisé (+30j)").sum()) if not df_m1.empty else 0
                nonutil_m  = int((df_m["statut"]  == "QR non utilisé (+30j)").sum()) if not df_m.empty  else 0

                with k1:
                    _kpi("Taux déploiement", dep_m1, dep_m, tot_m1, tot_m)
                with k2:
                    _kpi("Taux Actif", actif_m1, actif_m, tot_m1, tot_m)
                with k3:
                    _kpi("Taux Risque inactivité", risque_m1, risque_m, tot_m1, tot_m)
                with k4:
                    _kpi("QR non utilisé (+30j)", nonutil_m1, nonutil_m, tot_m1, tot_m)

                # Export Excel QR MoM
                st.divider()
                df_statuts_qr_export = pd.DataFrame(rows_qr)

                sheets_qr_mom: dict = {
                    f"Statuts {label_qr_m1} vs {label_qr_m}": df_statuts_qr_export,
                }

                if not vue_perso:
                    sheets_qr_mom["Par DSM"] = pd.DataFrame(rows_dsm)

                xlsx_qr_mom = export_df_to_excel(
                    sheets_qr_mom,
                    titre=f"QR Code MoM — {label_qr_m1} → {label_qr_m}",
                    source_label="ALBARKA — Comparaison MoM",
                )
                st.download_button(
                    label="Exporter QR Code MoM (Excel)",
                    data=xlsx_qr_mom,
                    file_name=f"qr_mom_{date_m1_qr}_vs_{date_m_qr}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_qr_mom",
                )
