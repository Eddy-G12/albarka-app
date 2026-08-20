"""
pages/7_Dashboard_QR_Admin.py
==============================
Dashboard QR Code réseau — Super Admin et Admin.

Affiche une vue agrégée du réseau d'agents à partir des données déjà en
cache (traitements réalisés dans le volet Suivi QR Code). Aucun upload
requis : on lit directement les fichiers CSV du cache.

Sections :
  - Sélection de la date de référence (parmi les dates déjà traitées)
  - Métriques globales (4 statuts en cartes)
  - KPIs clés (taux de déploiement, taux d'utilisation, etc.)
  - Répartition par segment (tableau + graphique barres empilées)
  - Tableau détaillé par DSM (nombre d'agents par statut)
"""

import streamlit as st
import pandas as pd

from core import db
from core.auth import require_role, show_user_badge

st.set_page_config(page_title="Dashboard QR Code — ALBARKA", layout="wide")

require_role("super_admin", "admin")
show_user_badge()

# ---------------------------------------------------------------------------
# Chemins cache
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
    dates = []
    for imp in imports:
        if (CACHE_QR_DIR / f"{imp['cle']}.csv").exists():
            dates.append(imp["cle"])
    return sorted(dates, reverse=True)


def load_cache(date_iso: str) -> pd.DataFrame:
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    return pd.read_csv(path, dtype={"pos_msisdn": str})


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
st.title("Dashboard QR Code — Vue réseau")

dates_dispo = qr_cache_dates_available()

if not dates_dispo:
    st.info(
        "Aucune donnée QR Code disponible. "
        "Traite d'abord un fichier dans le volet **Suivi QR Code**."
    )
    st.stop()

date_choisie = st.selectbox(
    "Date de référence",
    dates_dispo,
    format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
    key="sel_date_dashboard_qr",
)

df = load_cache(date_choisie)

total = len(df)
counts = {s: int((df["statut"] == s).sum()) for s in STATUTS_ORDER}

st.divider()

# ---------------------------------------------------------------------------
# Métriques globales
# ---------------------------------------------------------------------------
st.subheader("Vue globale")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total agents", total)
col2.metric("Sans QR Code",          counts["Sans QR Code"],
            delta=None, delta_color="off")
col3.metric("QR non utilisé (+30j)", counts["QR non utilisé (+30j)"],
            delta=None, delta_color="off")
col4.metric("Risque inactivité",     counts["Risque inactivité"],
            delta=None, delta_color="off")
col5.metric("Actif",                 counts["Actif"],
            delta=None, delta_color="off")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Indicateurs clés")

deployes = total - counts["Sans QR Code"]
taux_deploiement   = deployes / total if total else 0
taux_utilisation   = counts["Actif"] / deployes if deployes else 0
taux_non_utilise   = counts["QR non utilisé (+30j)"] / deployes if deployes else 0
taux_risque        = counts["Risque inactivité"] / total if total else 0
taux_sans          = counts["Sans QR Code"] / total if total else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Taux de déploiement",      f"{taux_deploiement:.1%}")
k2.metric("Taux d'utilisation",       f"{taux_utilisation:.1%}")
k3.metric("QR déployés non utilisés", f"{taux_non_utilise:.1%}")
k4.metric("Risque inactivité",        f"{taux_risque:.1%}")
k5.metric("Sans QR Code",             f"{taux_sans:.1%}")

# ---------------------------------------------------------------------------
# Répartition par segment
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Répartition par segment")

segments = sorted(df["segment_group"].dropna().unique())

rows_seg = []
for seg in segments:
    sub = df[df["segment_group"] == seg]
    row = {"Segment": seg, "Total": len(sub)}
    for s in STATUTS_ORDER:
        row[s] = int((sub["statut"] == s).sum())
    row["% Actif"] = f"{row['Actif'] / len(sub):.1%}" if len(sub) else "—"
    rows_seg.append(row)

df_seg = pd.DataFrame(rows_seg)
st.dataframe(df_seg, hide_index=True, use_container_width=True)

# Graphique barres empilées
df_chart = df_seg[["Segment"] + STATUTS_ORDER].set_index("Segment")
st.bar_chart(
    df_chart,
    color=[STATUT_COLORS[s] for s in STATUTS_ORDER],
    height=320,
)

# ---------------------------------------------------------------------------
# Répartition par DSM
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Répartition par DSM")

dsm_list = sorted(df["dsm_name"].dropna().unique())
rows_dsm = []
for dsm in dsm_list:
    sub = df[df["dsm_name"] == dsm]
    row = {"DSM": dsm, "Total": len(sub)}
    for s in STATUTS_ORDER:
        row[s] = int((sub["statut"] == s).sum())
    row["% Actif"] = f"{row['Actif'] / len(sub):.1%}" if len(sub) else "—"
    rows_dsm.append(row)

df_dsm = pd.DataFrame(rows_dsm).sort_values("Actif", ascending=False)
st.dataframe(df_dsm, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Détail agents à risque / sans QR
# ---------------------------------------------------------------------------
st.divider()
with st.expander("Agents prioritaires (Sans QR Code + Risque inactivité + QR non utilisé)"):
    prioritaires = df[df["statut"].isin(["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité"])].copy()
    prioritaires = prioritaires.sort_values(
        ["statut", "segment_group", "dsm_name", "pos_name"]
    )
    cols_affich = [c for c in
                   ["statut", "segment_group", "dsm_name", "pos_name", "pos_msisdn",
                    "days_since_last_use", "priorite"]
                   if c in prioritaires.columns]
    rename = {
        "statut": "Statut", "segment_group": "Segment", "dsm_name": "DSM",
        "pos_name": "Agent", "pos_msisdn": "Téléphone",
        "days_since_last_use": "Jours sans usage", "priorite": "Priorité",
    }
    st.dataframe(
        prioritaires[cols_affich].rename(columns=rename),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(f"{len(prioritaires)} agents nécessitant une action sur {total} au total.")

# ---------------------------------------------------------------------------
# Export Excel
# ---------------------------------------------------------------------------
st.divider()
from core.export import export_df_to_excel

label_date = pd.Timestamp(date_choisie).strftime("%d/%m/%Y")

# Résumé global KPIs
df_global_export = pd.DataFrame([
    {"Indicateur": "Total agents",              "Valeur": total},
    {"Indicateur": "Sans QR Code",              "Valeur": counts["Sans QR Code"]},
    {"Indicateur": "QR non utilisé (+30j)",     "Valeur": counts["QR non utilisé (+30j)"]},
    {"Indicateur": "Risque inactivité",          "Valeur": counts["Risque inactivité"]},
    {"Indicateur": "Actif",                      "Valeur": counts["Actif"]},
    {"Indicateur": "Taux de déploiement",        "Valeur": f"{taux_deploiement:.1%}"},
    {"Indicateur": "Taux d'utilisation",         "Valeur": f"{taux_utilisation:.1%}"},
    {"Indicateur": "QR déployés non utilisés",   "Valeur": f"{taux_non_utilise:.1%}"},
    {"Indicateur": "Risque inactivité (%)",      "Valeur": f"{taux_risque:.1%}"},
    {"Indicateur": "Sans QR Code (%)",           "Valeur": f"{taux_sans:.1%}"},
])

# Agents prioritaires (valeurs brutes)
cols_prio = [c for c in
             ["statut", "segment_group", "dsm_name", "pos_name", "pos_msisdn",
              "days_since_last_use", "priorite"]
             if c in prioritaires.columns]
rename_prio = {
    "statut": "Statut", "segment_group": "Segment", "dsm_name": "DSM",
    "pos_name": "Agent", "pos_msisdn": "Téléphone",
    "days_since_last_use": "Jours sans usage", "priorite": "Priorité",
}
df_prio_export = prioritaires[cols_prio].rename(columns=rename_prio).reset_index(drop=True)

xlsx_dashboard = export_df_to_excel(
    {
        "Résumé global":       df_global_export,
        "Par segment":         df_seg,
        "Par DSM":             df_dsm,
        "Agents prioritaires": df_prio_export,
    },
    titre=f"Dashboard QR Code — {label_date}",
    source_label="ALBARKA — QR Code Admin",
)
st.download_button(
    label="Exporter le dashboard (Excel)",
    data=xlsx_dashboard,
    file_name=f"dashboard_qr_{date_choisie}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="dl_dashboard_qr_admin",
)
