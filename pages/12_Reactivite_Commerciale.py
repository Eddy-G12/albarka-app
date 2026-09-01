"""
pages/12_Reactivite_Commerciale.py — v2
=========================================
Indicateurs de réactivité commerciale — Super Admin et Admin.

Source : fichiers CSV bruts MTN (ex. STEPHANE(7).csv, PARF-1-14.csv)
  - Format : Id, Date, Status, Type, From, From name, To, To name, Amount, Balance, ...
  - Horodatage complet → temps mort calculable
  - Colonne Balance → temps de recharge calculable
  - Compte propre identifié via l'alias configuré en base

Indicateurs calculés :
  - Nb transactions / jour moyen
  - Clients distincts touchés / jour moyen
  - Temps mort médian et maximum (écart entre transactions consécutives, en min)
  - Temps de recharge médian et le plus rapide (via colonne Balance)
"""

import io
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from core import db
from core.auth import require_role, show_user_badge
from core.export import export_df_to_excel
from core.ui import apply_theme, show_page_header

apply_theme()
require_role("super_admin", "admin")
show_user_badge()

# ── Constantes visuelles ──────────────────────────────────────────────────────
C_BLEU   = "#2980B9"
C_VERT   = "#27AE60"
C_ORANGE = "#E67E22"
C_ROUGE  = "#E74C3C"
C_VIOLET = "#8E44AD"
C_JAUNE  = "#F5A623"
C_GRIS   = "#95A5A6"

EXCLUDED = {"ALBARKA GN SARL", "ALBARKA GN SARL 5"}

# Seuil de flotte basse pour le temps de recharge (en FCFA)
LOW_BALANCE_THRESHOLD = 100_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_raw_csv(source) -> pd.DataFrame:
    """
    Lit un CSV brut MTN.
    Filtre Status=Successful et Type=Transfer.
    Conserve : Date (avec heure), From name, To name, Amount, Balance (si présent).
    """
    if isinstance(source, bytes):
        df = pd.read_csv(io.BytesIO(source), dtype=str)
    else:
        df = pd.read_csv(source, dtype=str)

    df.columns = df.columns.str.strip()

    # Filtres
    if "Status" in df.columns:
        df = df[df["Status"].str.strip() == "Successful"]
    if "Type" in df.columns:
        df = df[df["Type"].str.strip() == "Transfer"]

    # Exclusions ALBARKA internes
    if "From name" in df.columns:
        df = df[~df["From name"].isin(EXCLUDED)]
    if "To name" in df.columns:
        df = df[~df["To name"].isin(EXCLUDED)]

    # Convertir Date avec horodatage
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

    # Convertir Amount
    if "Amount" in df.columns:
        df["Amount"] = (
            df["Amount"].astype(str)
            .str.replace(r"[\s,]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0.0)
        )

    # Convertir Balance si présent
    if "Balance" in df.columns:
        df["Balance"] = (
            df["Balance"].astype(str)
            .str.replace(r"[\s,]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
        )

    return df.reset_index(drop=True)


def _detect_alias_in_df(df: pd.DataFrame, alias_map: dict) -> str | None:
    """
    Détecte l'alias du commercial dans le DataFrame.
    alias_map = {alias_upper: {commercial_id, dsm_name, alias}}
    """
    if "From name" not in df.columns:
        return None
    names = set(df["From name"].str.strip().str.upper().dropna()) | \
            set(df["To name"].str.strip().str.upper().dropna()) if "To name" in df.columns else set()
    for alias_upper in alias_map:
        if alias_upper in names:
            return alias_map[alias_upper]["alias"]
    return None


def _compute_reactivity_raw(df: pd.DataFrame, alias: str) -> dict:
    """
    Calcule tous les indicateurs de réactivité depuis un DataFrame brut MTN.

    alias : nom du compte propre du commercial (ex. 'ALBARKA 85')

    Retourne :
    {
      nb_transactions_total, nb_jours_actifs,
      transactions_par_jour, clients_par_jour,
      temps_mort_median_min, temps_mort_max_min,
      temps_recharge_median_min, temps_recharge_min_min,
    }
    """
    alias_upper = alias.strip().upper()

    # Filtrer les lignes qui concernent le commercial
    mask = (
        df["From name"].str.strip().str.upper() == alias_upper
    ) | (
        df["To name"].str.strip().str.upper() == alias_upper
    )
    df_own = df[mask].copy().sort_values("Date")

    if df_own.empty:
        return {
            "nb_transactions_total": 0,
            "nb_jours_actifs": 0,
            "transactions_par_jour": 0.0,
            "clients_par_jour": 0.0,
            "temps_mort_median_min": None,
            "temps_mort_max_min": None,
            "temps_recharge_median_min": None,
            "temps_recharge_min_min": None,
        }

    # Contrepartie pour chaque ligne
    def _contrepartie(row):
        if str(row["From name"]).strip().upper() == alias_upper:
            return str(row["To name"]).strip()
        return str(row["From name"]).strip()

    df_own["_cp"] = df_own.apply(_contrepartie, axis=1)
    df_own["_date"] = df_own["Date"].dt.date

    # Métriques de volume
    nb_total   = len(df_own)
    jours      = df_own["_date"].nunique()
    tx_par_j   = round(nb_total / jours, 2) if jours else 0.0
    cl_par_j   = round(
        df_own.groupby("_date")["_cp"].nunique().mean(), 2
    )

    # ── Temps mort ────────────────────────────────────────────────────────────
    # Écart en minutes entre deux transactions consécutives le même jour
    ecarts = []
    for jour, grp in df_own.groupby("_date"):
        if len(grp) < 2:
            continue
        ts = grp["Date"].sort_values()
        diffs = ts.diff().dropna().dt.total_seconds() / 60
        ecarts.extend(diffs.tolist())

    temps_mort_med = round(float(np.median(ecarts)), 1) if ecarts else None
    temps_mort_max = round(float(max(ecarts)),        1) if ecarts else None

    # ── Temps de recharge ─────────────────────────────────────────────────────
    temps_recharge_med = None
    temps_recharge_min = None

    if "Balance" in df_own.columns:
        bal = df_own["Balance"].dropna()
        if not bal.empty:
            try:
                recharges = []
                i = 0
                idx = df_own.dropna(subset=["Balance"]).index.tolist()
                df_bal = df_own.loc[idx].reset_index(drop=True)

                j = 0
                while j < len(df_bal) - 1:
                    if df_bal.iloc[j]["Balance"] < LOW_BALANCE_THRESHOLD:
                        k = j + 1
                        while k < len(df_bal) and df_bal.iloc[k]["Balance"] < LOW_BALANCE_THRESHOLD:
                            k += 1
                        if k < len(df_bal):
                            t0 = df_bal.iloc[j]["Date"]
                            t1 = df_bal.iloc[k]["Date"]
                            dur = (t1 - t0).total_seconds() / 60
                            if dur > 0:
                                recharges.append(dur)
                        j = k + 1
                    else:
                        j += 1

                if recharges:
                    temps_recharge_med = round(float(np.median(recharges)), 1)
                    temps_recharge_min = round(float(min(recharges)),       1)
            except Exception:
                pass

    return {
        "nb_transactions_total":   nb_total,
        "nb_jours_actifs":         jours,
        "transactions_par_jour":   tx_par_j,
        "clients_par_jour":        cl_par_j,
        "temps_mort_median_min":   temps_mort_med,
        "temps_mort_max_min":      temps_mort_max,
        "temps_recharge_median_min": temps_recharge_med,
        "temps_recharge_min_min":    temps_recharge_min,
    }


def _bar_h(names, values, color, title, unit="", fmt=".2f"):
    pairs       = sorted(zip(values, names), key=lambda x: (x[0] is None, x[0] or 0))
    vals_sorted = [p[0] for p in pairs]
    names_sorted = [p[1] for p in pairs]
    labels      = [f"{v:{fmt}}{' ' + unit if unit else ''}" if v is not None else "N/A"
                   for v in vals_sorted]
    colors      = [color if v is not None else C_GRIS for v in vals_sorted]
    display     = [v if v is not None else 0 for v in vals_sorted]

    fig = go.Figure(go.Bar(
        x=display, y=names_sorted, orientation="h",
        marker_color=colors, text=labels, textposition="outside",
        hovertemplate="%{y} : %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        height=max(280, len(names) * 42),
        margin=dict(l=10, r=80, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        font=dict(family="Arial"),
    )
    return fig


def _fmt(v, fmt=".2f"):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    try:
        return f"{v:{fmt}}"
    except Exception:
        return str(v)


# ── Interface ─────────────────────────────────────────────────────────────────

show_page_header("Réactivité Commerciale", "Indicateurs depuis les fichiers CSV bruts MTN")
st.divider()

st.info(
    "Dépose les **fichiers CSV bruts MTN** (ex. `STEPHANE(7).csv`, `PARF-1-14.csv`). "
    "Le compte propre du commercial est détecté automatiquement depuis les aliases configurés. "
    "L'horodatage complet et la colonne Balance permettent de calculer le temps mort "
    "et le temps de recharge.",
    icon="ℹ️",
)

# ── Chargement ────────────────────────────────────────────────────────────────
st.subheader("1 — Charger les fichiers")

fichiers = st.file_uploader(
    "Fichiers CSV bruts MTN (un ou plusieurs)",
    type=["csv"],
    accept_multiple_files=True,
    key="up_react_v2",
)

commerciaux_db = db.list_commerciaux()
alias_map      = db.get_alias_map()   # {alias_upper: {commercial_id, dsm_name, alias}}
com_by_dsm     = {c["dsm_name"].upper(): c for c in commerciaux_db}

if not fichiers:
    st.info("Dépose au moins un fichier CSV pour commencer.")
    st.stop()

# ── Association fichier → commercial ─────────────────────────────────────────
st.subheader("2 — Vérifier les associations")
st.caption(
    "L'alias est détecté automatiquement dans le fichier. "
    "Si le fichier ne contient pas d'alias reconnu, sélectionne le commercial manuellement."
)

associations: dict[str, str | None] = {}  # fichier_name → dsm_name ou None

for f in fichiers:
    col_fn, col_info, col_sel = st.columns([2, 2, 2])
    col_fn.markdown(f"**{f.name}**")

    # Pré-lire les 20 premières lignes pour détecter l'alias
    f.seek(0)
    raw_preview = f.read()
    f.seek(0)

    detected_alias = None
    detected_dsm   = None
    try:
        df_preview = pd.read_csv(io.BytesIO(raw_preview), nrows=20, dtype=str)
        df_preview.columns = df_preview.columns.str.strip()
        if "Status" in df_preview.columns:
            df_preview = df_preview[df_preview["Status"].str.strip() == "Successful"]
        if "From name" in df_preview.columns and "To name" in df_preview.columns:
            names_seen = set(df_preview["From name"].str.strip().str.upper().dropna()) | \
                         set(df_preview["To name"].str.strip().str.upper().dropna())
            for alias_up, info in alias_map.items():
                if alias_up in names_seen:
                    detected_alias = info["alias"]
                    detected_dsm   = info["dsm_name"]
                    break
    except Exception:
        pass

    noms_dispo = [c["dsm_name"] for c in commerciaux_db]

    if detected_dsm:
        col_info.caption(f"Alias détecté : **{detected_alias}**")
        idx_def = noms_dispo.index(detected_dsm) if detected_dsm in noms_dispo else 0
    else:
        col_info.caption("Alias non détecté — sélectionne manuellement")
        idx_def = 0

    choix = col_sel.selectbox(
        "Commercial",
        noms_dispo,
        index=idx_def,
        key=f"sel_com_react_{f.name}",
        label_visibility="collapsed",
    )
    associations[f.name] = choix

st.divider()

# ── Calcul ────────────────────────────────────────────────────────────────────
col_btn, col_reset = st.columns([2, 1])
calcul_demande = col_btn.button("Calculer les indicateurs", key="btn_calc_react", type="primary")
if col_reset.button("Effacer les résultats", key="btn_reset_react"):
    st.session_state.pop("react_resultats", None)
    st.rerun()

if calcul_demande:
    resultats_new = []
    erreurs_new   = []
    progress      = st.progress(0, text="Calcul en cours…")

    for i, f in enumerate(fichiers):
        progress.progress(i / len(fichiers), text=f"Traitement de {f.name}…")
        dsm_name = associations.get(f.name)

        try:
            f.seek(0)
            raw = f.read()
            df  = _load_raw_csv(raw)

            if df.empty:
                erreurs_new.append((f.name, "Aucune transaction Transfer/Successful trouvée."))
                continue

            com   = com_by_dsm.get(dsm_name.upper()) if dsm_name else None
            alias = db.get_alias(com["id"]) if com else None

            if not alias:
                alias = _detect_alias_in_df(df, alias_map)

            if not alias:
                erreurs_new.append((
                    f.name,
                    f"Alias introuvable pour **{dsm_name}**. "
                    "Configure l'alias dans Administration → Aliases CSV."
                ))
                continue

            ind = _compute_reactivity_raw(df, alias)

            resultats_new.append({
                "commercial":              dsm_name or alias,
                "alias":                   alias,
                "fichier":                 f.name,
                "nb_transactions":         ind["nb_transactions_total"],
                "nb_jours_actifs":         ind["nb_jours_actifs"],
                "transactions_par_jour":   ind["transactions_par_jour"],
                "clients_par_jour":        ind["clients_par_jour"],
                "temps_mort_median_min":   ind["temps_mort_median_min"],
                "temps_mort_max_min":      ind["temps_mort_max_min"],
                "temps_recharge_med_min":  ind["temps_recharge_median_min"],
                "temps_recharge_min_min":  ind["temps_recharge_min_min"],
            })

        except Exception as e:
            erreurs_new.append((f.name, f"{e}"))

    progress.progress(1.0, text="Terminé.")

    for fname, msg in erreurs_new:
        st.warning(f"**{fname}** — {msg}")

    if resultats_new:
        # Stocker en session → persistant lors des changements de page
        st.session_state["react_resultats"] = resultats_new
    elif not erreurs_new:
        st.error("Aucun fichier traité.")

# ── Affichage des résultats (depuis session_state) ────────────────────────────
if "react_resultats" not in st.session_state:
    st.stop()

st.subheader("3 — Résultats")
st.caption("Les résultats sont conservés même si vous changez de page.")

df_res = pd.DataFrame(st.session_state["react_resultats"])

# ── Tableau récapitulatif ─────────────────────────────────────────────────────
st.markdown("#### Tableau récapitulatif")

df_affich = pd.DataFrame({
    "Commercial":              df_res["commercial"],
    "Alias":                   df_res["alias"],
    "Nb transactions":         df_res["nb_transactions"].apply(lambda v: f"{v:,}"),
    "Jours actifs":            df_res["nb_jours_actifs"],
    "Tx / jour":               df_res["transactions_par_jour"].apply(lambda v: f"{v:.2f}"),
    "Clients / jour":          df_res["clients_par_jour"].apply(lambda v: f"{v:.2f}"),
    "Tps mort médian (min)":   df_res["temps_mort_median_min"].apply(_fmt),
    "Tps mort max (min)":      df_res["temps_mort_max_min"].apply(_fmt),
    "Tps recharge méd. (min)": df_res["temps_recharge_med_min"].apply(_fmt),
    "Tps recharge min (min)":  df_res["temps_recharge_min_min"].apply(_fmt),
})
st.dataframe(df_affich, hide_index=True, use_container_width=True)

# ── Synthèse réseau ───────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Synthèse réseau")

nb_com   = len(df_res)
tot_tx   = int(df_res["nb_transactions"].sum())
moy_tx_j = round(df_res["transactions_par_jour"].mean(), 2)
max_tx_j = df_res["transactions_par_jour"].max()
min_tx_j = df_res["transactions_par_jour"].min()
com_max  = df_res.loc[df_res["transactions_par_jour"].idxmax(), "commercial"]
com_min  = df_res.loc[df_res["transactions_par_jour"].idxmin(), "commercial"]

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Commerciaux analysés", nb_com)
s2.metric("Total transactions",   f"{tot_tx:,}")
s3.metric("Tx/jour moyen",        f"{moy_tx_j:.2f}")
s4.metric(f"Meilleur ({com_max})", f"{max_tx_j:.2f} Tx/j")
s5.metric(f"Plus faible ({com_min})", f"{min_tx_j:.2f} Tx/j", delta_color="off")

tps_mort_vals = df_res["temps_mort_median_min"].dropna()
tps_rech_vals = df_res["temps_recharge_med_min"].dropna()

if not tps_mort_vals.empty or not tps_rech_vals.empty:
    st.divider()
    tm1, tm2, tm3, tm4 = st.columns(4)

    if not tps_mort_vals.empty:
        tm1.metric("Tps mort médian réseau",  f"{tps_mort_vals.mean():.1f} min")
        tm2.metric("Tps mort max observé",    f"{df_res['temps_mort_max_min'].dropna().max():.1f} min")
        com_react = df_res.loc[df_res["temps_mort_median_min"].dropna().idxmin(), "commercial"]
        tm3.metric("Plus réactif",            com_react)
    else:
        tm1.metric("Tps mort médian", "N/A")
        tm2.metric("Tps mort max",    "N/A")
        tm3.metric("Plus réactif",    "N/A")

    if not tps_rech_vals.empty:
        tm4.metric("Tps recharge médian", f"{tps_rech_vals.mean():.1f} min")
    else:
        tm4.metric("Tps recharge médian", "N/A")

# ── Graphiques ────────────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Classements")

tab_tx, tab_cl, tab_tm, tab_tr = st.tabs([
    "Transactions / jour", "Clients / jour", "Temps mort", "Temps de recharge"
])

with tab_tx:
    st.plotly_chart(_bar_h(
        df_res["commercial"].tolist(), df_res["transactions_par_jour"].tolist(),
        C_BLEU, "Transactions par jour moyen", "Tx/j",
    ), use_container_width=True)
    with st.expander("Détail"):
        d = df_res[["commercial","nb_transactions","nb_jours_actifs","transactions_par_jour"]].copy()
        d.columns = ["Commercial","Nb transactions","Jours actifs","Tx/jour"]
        d = d.sort_values("Tx/jour", ascending=False).reset_index(drop=True)
        d.insert(0, "#", range(1, len(d)+1))
        st.dataframe(d, hide_index=True, use_container_width=True)

with tab_cl:
    st.plotly_chart(_bar_h(
        df_res["commercial"].tolist(), df_res["clients_par_jour"].tolist(),
        C_VERT, "Clients touchés par jour moyen", "clients/j",
    ), use_container_width=True)

with tab_tm:
    has_tm = df_res["temps_mort_median_min"].notna().any()
    if not has_tm:
        st.warning("Temps mort non calculable — horodatage à la minute requis.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            fig = _bar_h(df_res["commercial"].tolist(), df_res["temps_mort_median_min"].tolist(),
                         C_ORANGE, "Temps mort médian (min)", "min", ".1f")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = _bar_h(df_res["commercial"].tolist(), df_res["temps_mort_max_min"].tolist(),
                          C_ROUGE, "Temps mort max (min)", "min", ".1f")
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)

with tab_tr:
    has_tr = df_res["temps_recharge_med_min"].notna().any()
    if not has_tr:
        st.warning(
            "Temps de recharge non calculable.\n"
            "Causes possibles : colonne **Balance** absente ou horodatage insuffisant."
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(_bar_h(
                df_res["commercial"].tolist(), df_res["temps_recharge_med_min"].tolist(),
                C_VIOLET, "Temps de recharge médian (min)", "min", ".1f",
            ), use_container_width=True)
        with c2:
            st.plotly_chart(_bar_h(
                df_res["commercial"].tolist(), df_res["temps_recharge_min_min"].tolist(),
                C_JAUNE, "Temps de recharge le plus rapide (min)", "min", ".1f",
            ), use_container_width=True)

# ── Fiche individuelle ────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Fiche individuelle")

com_sel = st.selectbox("Commercial", df_res["commercial"].tolist(), key="sel_fiche_react")
row = df_res[df_res["commercial"] == com_sel].iloc[0]

f1, f2, f3, f4 = st.columns(4)
f1.metric("Nb transactions",      f"{row['nb_transactions']:,}")
f2.metric("Jours actifs",         row["nb_jours_actifs"])
f3.metric("Transactions / jour",  f"{row['transactions_par_jour']:.2f}")
f4.metric("Clients / jour",       f"{row['clients_par_jour']:.2f}")

f5, f6, f7, f8 = st.columns(4)
f5.metric("Tps mort médian",
          _fmt(row["temps_mort_median_min"], ".1f") + (" min" if row["temps_mort_median_min"] else ""))
f6.metric("Tps mort max",
          _fmt(row["temps_mort_max_min"],    ".1f") + (" min" if row["temps_mort_max_min"] else ""))
f7.metric("Tps recharge médian",
          _fmt(row["temps_recharge_med_min"], ".1f") + (" min" if row["temps_recharge_med_min"] else ""))
f8.metric("Tps recharge min",
          _fmt(row["temps_recharge_min_min"], ".1f") + (" min" if row["temps_recharge_min_min"] else ""))

st.caption(f"Alias : **{row['alias']}** · Fichier : *{row['fichier']}*")

# ── Export Excel ──────────────────────────────────────────────────────────────
st.divider()

df_export = pd.DataFrame({
    "Commercial":                df_res["commercial"],
    "Alias":                     df_res["alias"],
    "Fichier source":            df_res["fichier"],
    "Nb transactions":           df_res["nb_transactions"],
    "Jours actifs":              df_res["nb_jours_actifs"],
    "Transactions / jour":       df_res["transactions_par_jour"],
    "Clients touchés / jour":    df_res["clients_par_jour"],
    "Tps mort médian (min)":     df_res["temps_mort_median_min"],
    "Tps mort max (min)":        df_res["temps_mort_max_min"],
    "Tps recharge médian (min)": df_res["temps_recharge_med_min"],
    "Tps recharge min (min)":    df_res["temps_recharge_min_min"],
})

df_synthese = pd.DataFrame([
    {"Indicateur": "Commerciaux analysés",       "Valeur": nb_com},
    {"Indicateur": "Total transactions",          "Valeur": tot_tx},
    {"Indicateur": "Tx/jour moyen réseau",        "Valeur": round(moy_tx_j, 2)},
    {"Indicateur": "Tx/jour max",                 "Valeur": round(float(max_tx_j), 2)},
    {"Indicateur": "Tx/jour min",                 "Valeur": round(float(min_tx_j), 2)},
    {"Indicateur": "Avec données temps mort",     "Valeur": int(tps_mort_vals.notna().sum()) if len(tps_mort_vals) else 0},
    {"Indicateur": "Avec données recharge",       "Valeur": int(tps_rech_vals.notna().sum()) if len(tps_rech_vals) else 0},
])

xlsx = export_df_to_excel(
    {"Synthèse réseau": df_synthese, "Indicateurs par commercial": df_export},
    titre="Réactivité Commerciale — ALBARKA",
    source_label="ALBARKA — Réactivité",
)
st.download_button(
    "Télécharger le rapport (Excel)", data=xlsx,
    file_name="reactivite_commerciale.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="dl_react",
)
