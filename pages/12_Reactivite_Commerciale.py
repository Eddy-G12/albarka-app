"""
pages/12_Reactivite_Commerciale.py
====================================
Indicateurs de réactivité commerciale — Super Admin et Admin.

Ce module expose tous les indicateurs calculés par core/metrics.compute_reactivity()
à partir des fichiers CSV bruts (listings Mobile Money avec horodatage à la minute).

Indicateurs affichés (CDC §Module 3) :
  - Transactions / jour moyen
  - Clients touchés / jour moyen (contreparties distinctes)
  - Temps mort médian et maximum (écart entre deux transactions consécutives, en min)
  - Temps de recharge de flotte médian et le plus rapide (si colonne Balance présente)

Flux :
  1. Upload d'un ou plusieurs fichiers CSV (un par commercial)
  2. Calcul automatique pour chaque fichier (compte propre détecté automatiquement)
  3. Affichage côte à côte dans des tableaux et graphiques Plotly comparatifs
  4. Export Excel des résultats

Note : les temps mort / recharge nécessitent un horodatage à la minute dans la
colonne Date. Si la date a déjà été réduite au jour (par un import précédent),
ces indicateurs ne peuvent pas être calculés et sont affichés comme "N/A".
"""

import io
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core import db
from core.auth import require_role, show_user_badge
from core.metrics import load_transactions_full, detect_self_account, compute_reactivity
from core.cashflow import match_commercial_by_filename
from core.export import export_df_to_excel

# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Réactivité Commerciale — ALBARKA",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
show_user_badge()

# ──────────────────────────────────────────────────────────────────────────────
# Constantes visuelles
# ──────────────────────────────────────────────────────────────────────────────
C_BLEU   = "#2980B9"
C_VERT   = "#27AE60"
C_ORANGE = "#E67E22"
C_ROUGE  = "#E74C3C"
C_VIOLET = "#8E44AD"
C_JAUNE  = "#F5A623"
C_GRIS   = "#95A5A6"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers graphiques
# ──────────────────────────────────────────────────────────────────────────────

def _bar_h(names: list, values: list, color: str, title: str,
           unit: str = "", fmt: str = ".2f") -> go.Figure:
    """Barres horizontales simples, triées croissantes (meilleur en bas)."""
    pairs = sorted(zip(values, names), key=lambda x: x[0])
    vals_sorted = [p[0] for p in pairs]
    names_sorted = [p[1] for p in pairs]

    text_labels = []
    for v in vals_sorted:
        if v is None:
            text_labels.append("N/A")
        else:
            text_labels.append(f"{v:{fmt}}{' ' + unit if unit else ''}")

    bar_colors = [color if v is not None else C_GRIS for v in vals_sorted]
    display_vals = [v if v is not None else 0 for v in vals_sorted]

    fig = go.Figure(go.Bar(
        x=display_vals,
        y=names_sorted,
        orientation="h",
        marker_color=bar_colors,
        text=text_labels,
        textposition="outside",
        hovertemplate="%{y} : %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        height=max(280, len(names) * 42),
        margin=dict(l=10, r=80, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        font=dict(family="Arial"),
    )
    return fig


def _gauge_card(label: str, value, unit: str = "", color: str = C_BLEU,
                help_txt: str = "") -> None:
    """Affiche une petite carte métrique avec gestion des None."""
    if value is None:
        st.metric(label, "N/A", help=help_txt or "Données insuffisantes (horodatage requis)")
    else:
        try:
            st.metric(label, f"{value:,.2f} {unit}".strip(), help=help_txt)
        except (ValueError, TypeError):
            st.metric(label, f"{value} {unit}".strip(), help=help_txt)


def _na_or(v, fmt=".2f"):
    if v is None:
        return "N/A"
    try:
        return f"{v:{fmt}}"
    except Exception:
        return str(v)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE
# ──────────────────────────────────────────────────────────────────────────────

st.title("Réactivité Commerciale")
st.write(
    "Calcule et compare les indicateurs de réactivité de chaque commercial "
    "à partir de leurs listings Mobile Money CSV. "
    "Dépose **un fichier par commercial** — le compte propre est détecté automatiquement."
)

st.info(
    "**Horodatage requis** : le fichier CSV doit contenir les heures dans la "
    "colonne Date (ex. *2026-07-15 09:42:00*) pour calculer le temps mort "
    "et le temps de recharge. Sans horodatage précis ces deux indicateurs "
    "s'affichent comme **N/A**.",
    icon="ℹ️",
)

# ──────────────────────────────────────────────────────────────────────────────
# Upload des fichiers
# ──────────────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("1 — Charger les fichiers")

fichiers = st.file_uploader(
    "Fichiers CSV de transactions (un par commercial)",
    type=["csv"],
    accept_multiple_files=True,
    key="up_reactivite",
)

commerciaux_db = db.list_commerciaux()

# ──────────────────────────────────────────────────────────────────────────────
# Calcul
# ──────────────────────────────────────────────────────────────────────────────

if not fichiers:
    st.info("Dépose au moins un fichier CSV pour commencer.")
    st.stop()

# Résoudre le label commercial pour chaque fichier
st.subheader("2 — Associer chaque fichier à un commercial")
st.caption("Le nom est détecté automatiquement depuis le nom du fichier. Corrige si besoin.")

associations = {}  # fichier_name → label_commercial (str)

for f in fichiers:
    match = match_commercial_by_filename(f.name, commerciaux_db)
    noms_dispo = [c["dsm_name"] for c in commerciaux_db]

    col_fname, col_sel = st.columns([2, 2])
    col_fname.markdown(f"**{f.name}**")

    if match and match["dsm_name"] in noms_dispo:
        idx_def = noms_dispo.index(match["dsm_name"])
    else:
        idx_def = 0

    if noms_dispo:
        choix = col_sel.selectbox(
            "Commercial associé",
            noms_dispo,
            index=idx_def,
            key=f"sel_com_{f.name}",
            label_visibility="collapsed",
        )
        associations[f.name] = choix
    else:
        # Aucun commercial en base — on utilise le nom du fichier
        associations[f.name] = f.name

st.divider()

# Bouton de calcul
if not st.button("Calculer les indicateurs de réactivité", key="btn_calc_react", type="primary"):
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Boucle de calcul
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("3 — Résultats")

resultats = []   # liste de dicts {commercial, compte_propre, nb_tx, ...indicateurs}
erreurs   = []   # liste de (filename, message)

progress = st.progress(0, text="Calcul en cours…")

for i, f in enumerate(fichiers):
    progress.progress((i) / len(fichiers), text=f"Traitement de {f.name}…")
    label = associations.get(f.name, f.name)
    try:
        f.seek(0)
        raw = f.read()
        df  = load_transactions_full(io.BytesIO(raw))

        if df.empty:
            erreurs.append((f.name, "Aucune transaction exploitable après nettoyage."))
            continue

        compte = detect_self_account(df)
        ind    = compute_reactivity(df, compte)

        resultats.append({
            "commercial":             label,
            "fichier":                f.name,
            "compte_propre":          compte,
            "nb_transactions":        ind["nb_transactions_total"],
            "nb_jours_actifs":        ind["nb_jours_actifs"],
            "transactions_par_jour":  ind["transactions_par_jour"],
            "clients_par_jour":       ind["clients_par_jour"],
            "temps_mort_median_min":  ind["temps_mort_median_min"],
            "temps_mort_max_min":     ind["temps_mort_max_min"],
            "temps_recharge_med_min": ind["temps_recharge_median_min"],
            "temps_recharge_min_min": ind["temps_recharge_min_min"],
        })
    except Exception as e:
        erreurs.append((f.name, str(e)))

progress.progress(1.0, text="Terminé.")

# Affiche les erreurs s'il y en a
for fname, msg in erreurs:
    st.warning(f"**{fname}** — ignoré : {msg}")

if not resultats:
    st.error("Aucun fichier n'a pu être traité. Vérifie le format des fichiers CSV.")
    st.stop()

df_res = pd.DataFrame(resultats)

# ──────────────────────────────────────────────────────────────────────────────
# 3A — Tableau récapitulatif complet
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("#### Tableau récapitulatif")
st.caption(
    "N/A = indicateur non calculable (horodatage à la minute requis ou "
    "colonne Balance absente pour le temps de recharge)."
)

df_recap = df_res[[
    "commercial", "nb_transactions", "nb_jours_actifs",
    "transactions_par_jour", "clients_par_jour",
    "temps_mort_median_min", "temps_mort_max_min",
    "temps_recharge_med_min", "temps_recharge_min_min",
]].copy()

df_recap = df_recap.rename(columns={
    "commercial":             "Commercial",
    "nb_transactions":        "Nb transactions",
    "nb_jours_actifs":        "Jours actifs",
    "transactions_par_jour":  "Tx / jour",
    "clients_par_jour":       "Clients / jour",
    "temps_mort_median_min":  "Tps mort médian (min)",
    "temps_mort_max_min":     "Tps mort max (min)",
    "temps_recharge_med_min": "Tps recharge méd. (min)",
    "temps_recharge_min_min": "Tps recharge min (min)",
})

# Formater les colonnes numériques
def _fmt_col(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    return f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"

for col in ["Tps mort médian (min)", "Tps mort max (min)",
            "Tps recharge méd. (min)", "Tps recharge min (min)"]:
    df_recap[col] = df_res[df_recap.columns.get_loc(col) - 4 + list(df_res.columns).index("temps_mort_median_min")
                           if False else col.lower().replace(" ", "_").replace(".", "").replace("(min)", "min")
                           .replace("tps_mort_médian_min", "temps_mort_median_min")
                           .replace("tps_mort_max_min", "temps_mort_max_min")
                           .replace("tps_recharge_méd__min", "temps_recharge_med_min")
                           .replace("tps_recharge_min_min", "temps_recharge_min_min")
                           ].apply(_fmt_col)

# Reconstruire proprement pour éviter les erreurs de mapping
df_recap_affich = pd.DataFrame({
    "Commercial":               df_res["commercial"],
    "Nb transactions":          df_res["nb_transactions"].apply(lambda v: f"{v:,}"),
    "Jours actifs":             df_res["nb_jours_actifs"],
    "Tx / jour":                df_res["transactions_par_jour"].apply(lambda v: f"{v:.2f}"),
    "Clients / jour":           df_res["clients_par_jour"].apply(lambda v: f"{v:.2f}"),
    "Tps mort médian (min)":    df_res["temps_mort_median_min"].apply(_fmt_col),
    "Tps mort max (min)":       df_res["temps_mort_max_min"].apply(_fmt_col),
    "Tps recharge méd. (min)":  df_res["temps_recharge_med_min"].apply(_fmt_col),
    "Tps recharge min (min)":   df_res["temps_recharge_min_min"].apply(_fmt_col),
})
st.dataframe(df_recap_affich, hide_index=True, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 3B — Métriques réseau globales
# ──────────────────────────────────────────────────────────────────────────────

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
s1.metric("Commerciaux analysés",       f"{nb_com}")
s2.metric("Total transactions",         f"{tot_tx:,}")
s3.metric("Tx/jour moyen réseau",       f"{moy_tx_j:.2f}")
s4.metric(f"Meilleur ({com_max})",      f"{max_tx_j:.2f} Tx/j",  delta="+")
s5.metric(f"Plus faible ({com_min})",   f"{min_tx_j:.2f} Tx/j",  delta_color="off")

# Temps mort réseau (si disponibles)
tps_mort_vals = df_res["temps_mort_median_min"].dropna()
tps_rech_vals = df_res["temps_recharge_med_min"].dropna()

if not tps_mort_vals.empty or not tps_rech_vals.empty:
    st.divider()
    tm1, tm2, tm3, tm4 = st.columns(4)

    if not tps_mort_vals.empty:
        med_tm  = round(tps_mort_vals.mean(), 1)
        max_tm  = round(df_res["temps_mort_max_min"].dropna().max(), 1)
        com_tm  = df_res.loc[df_res["temps_mort_median_min"].dropna().idxmin(), "commercial"]
        tm1.metric("Tps mort médian réseau",   f"{med_tm:.1f} min")
        tm2.metric("Tps mort max observé",     f"{max_tm:.1f} min")
        tm3.metric("Plus réactif (tps mort)",  com_tm)
    else:
        tm1.metric("Tps mort médian réseau",   "N/A")
        tm2.metric("Tps mort max observé",     "N/A")
        tm3.metric("Plus réactif (tps mort)",  "N/A")

    if not tps_rech_vals.empty:
        med_tr  = round(tps_rech_vals.mean(), 1)
        min_tr  = round(df_res["temps_recharge_min_min"].dropna().min(), 1)
        com_tr  = df_res.loc[df_res["temps_recharge_med_min"].dropna().idxmin(), "commercial"]
        tm4.metric("Tps recharge médian réseau", f"{med_tr:.1f} min",
                   help="Temps moyen pour recharger la flotte une fois épuisée")
    else:
        tm4.metric("Tps recharge médian réseau", "N/A")

# ──────────────────────────────────────────────────────────────────────────────
# 3C — Graphiques comparatifs
# ──────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("#### Classements visuels")

tab_tx, tab_cl, tab_tm, tab_tr = st.tabs([
    "Transactions / jour",
    "Clients / jour",
    "Temps mort",
    "Temps de recharge",
])

with tab_tx:
    st.caption("Nombre moyen de transactions effectuées par jour actif.")
    fig_tx = _bar_h(
        names=df_res["commercial"].tolist(),
        values=df_res["transactions_par_jour"].tolist(),
        color=C_BLEU,
        title="Transactions par jour moyen",
        unit="Tx/j",
        fmt=".2f",
    )
    st.plotly_chart(fig_tx, use_container_width=True)

    with st.expander("Détail — Transactions"):
        df_det_tx = df_res[["commercial", "nb_transactions", "nb_jours_actifs", "transactions_par_jour"]].copy()
        df_det_tx.columns = ["Commercial", "Nb transactions", "Jours actifs", "Tx / jour"]
        df_det_tx = df_det_tx.sort_values("Tx / jour", ascending=False).reset_index(drop=True)
        df_det_tx.insert(0, "#", range(1, len(df_det_tx) + 1))
        st.dataframe(df_det_tx, hide_index=True, use_container_width=True)

with tab_cl:
    st.caption("Nombre moyen de contreparties (clients) distinctes touchées par jour actif.")
    fig_cl = _bar_h(
        names=df_res["commercial"].tolist(),
        values=df_res["clients_par_jour"].tolist(),
        color=C_VERT,
        title="Clients touchés par jour moyen",
        unit="clients/j",
        fmt=".2f",
    )
    st.plotly_chart(fig_cl, use_container_width=True)

    with st.expander("Détail — Clients / jour"):
        df_det_cl = df_res[["commercial", "clients_par_jour", "nb_jours_actifs"]].copy()
        df_det_cl.columns = ["Commercial", "Clients / jour", "Jours actifs"]
        df_det_cl = df_det_cl.sort_values("Clients / jour", ascending=False).reset_index(drop=True)
        df_det_cl.insert(0, "#", range(1, len(df_det_cl) + 1))
        st.dataframe(df_det_cl, hide_index=True, use_container_width=True)

with tab_tm:
    st.caption(
        "Écart en minutes entre deux transactions consécutives du même jour. "
        "**Médian** = valeur typique. **Max** = pire écart observé."
    )
    has_tm = df_res["temps_mort_median_min"].notna().any()

    if not has_tm:
        st.warning(
            "Le temps mort n'a pas pu être calculé pour ces fichiers. "
            "Vérifie que la colonne Date contient bien l'heure (format AAAA-MM-JJ HH:MM:SS)."
        )
    else:
        col_tm_med, col_tm_max = st.columns(2)

        with col_tm_med:
            fig_tm_med = _bar_h(
                names=df_res["commercial"].tolist(),
                values=df_res["temps_mort_median_min"].tolist(),
                color=C_ORANGE,
                title="Temps mort médian (min)",
                unit="min",
                fmt=".1f",
            )
            # Pour le temps mort : MOINS c'est bon → barres inversées (croissant = pire)
            fig_tm_med.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_tm_med, use_container_width=True)

        with col_tm_max:
            fig_tm_max = _bar_h(
                names=df_res["commercial"].tolist(),
                values=df_res["temps_mort_max_min"].tolist(),
                color=C_ROUGE,
                title="Temps mort maximum observé (min)",
                unit="min",
                fmt=".1f",
            )
            fig_tm_max.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_tm_max, use_container_width=True)

        with st.expander("Détail — Temps mort"):
            df_det_tm = df_res[["commercial", "temps_mort_median_min", "temps_mort_max_min"]].copy()
            df_det_tm.columns = ["Commercial", "Tps mort médian (min)", "Tps mort max (min)"]
            df_det_tm["Tps mort médian (min)"] = df_det_tm["Tps mort médian (min)"].apply(_fmt_col)
            df_det_tm["Tps mort max (min)"]    = df_det_tm["Tps mort max (min)"].apply(_fmt_col)
            st.dataframe(df_det_tm, hide_index=True, use_container_width=True)

with tab_tr:
    st.caption(
        "Temps (en minutes) pour recharger la flotte une fois le solde passé sous le seuil. "
        "Nécessite la colonne **Balance** dans le fichier CSV."
    )
    has_tr = df_res["temps_recharge_med_min"].notna().any()

    if not has_tr:
        st.warning(
            "Le temps de recharge n'a pas pu être calculé. "
            "Deux causes possibles :\n"
            "- La colonne **Balance** est absente du fichier CSV\n"
            "- L'horodatage à la minute n'est pas disponible"
        )
    else:
        col_tr_med, col_tr_min = st.columns(2)

        with col_tr_med:
            fig_tr_med = _bar_h(
                names=df_res["commercial"].tolist(),
                values=df_res["temps_recharge_med_min"].tolist(),
                color=C_VIOLET,
                title="Temps de recharge médian (min)",
                unit="min",
                fmt=".1f",
            )
            st.plotly_chart(fig_tr_med, use_container_width=True)

        with col_tr_min:
            fig_tr_min = _bar_h(
                names=df_res["commercial"].tolist(),
                values=df_res["temps_recharge_min_min"].tolist(),
                color=C_JAUNE,
                title="Temps de recharge le plus rapide (min)",
                unit="min",
                fmt=".1f",
            )
            st.plotly_chart(fig_tr_min, use_container_width=True)

        with st.expander("Détail — Temps de recharge"):
            df_det_tr = df_res[["commercial", "temps_recharge_med_min", "temps_recharge_min_min"]].copy()
            df_det_tr.columns = ["Commercial", "Tps recharge médian (min)", "Tps recharge min (min)"]
            df_det_tr["Tps recharge médian (min)"] = df_det_tr["Tps recharge médian (min)"].apply(_fmt_col)
            df_det_tr["Tps recharge min (min)"]    = df_det_tr["Tps recharge min (min)"].apply(_fmt_col)
            st.dataframe(df_det_tr, hide_index=True, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 3D — Vue détaillée par commercial
# ──────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("#### Fiche individuelle")
st.caption("Sélectionne un commercial pour voir toutes ses métriques en détail.")

com_choisi = st.selectbox(
    "Commercial",
    df_res["commercial"].tolist(),
    key="sel_com_fiche",
)

row_com = df_res[df_res["commercial"] == com_choisi].iloc[0]

fi1, fi2, fi3, fi4 = st.columns(4)
fi1.metric("Nb transactions total",   f"{row_com['nb_transactions']:,}")
fi2.metric("Jours actifs",            f"{row_com['nb_jours_actifs']}")
fi3.metric("Transactions / jour",     f"{row_com['transactions_par_jour']:.2f}")
fi4.metric("Clients touchés / jour",  f"{row_com['clients_par_jour']:.2f}")

fi5, fi6, fi7, fi8 = st.columns(4)
fi5.metric(
    "Tps mort médian",
    _na_or(row_com["temps_mort_median_min"], ".1f") + (" min" if row_com["temps_mort_median_min"] is not None else ""),
    help="Écart médian entre deux transactions consécutives le même jour",
)
fi6.metric(
    "Tps mort maximum",
    _na_or(row_com["temps_mort_max_min"], ".1f") + (" min" if row_com["temps_mort_max_min"] is not None else ""),
    help="Plus long écart observé entre deux transactions le même jour",
)
fi7.metric(
    "Tps recharge médian",
    _na_or(row_com["temps_recharge_med_min"], ".1f") + (" min" if row_com["temps_recharge_med_min"] is not None else ""),
    help="Temps médian pour recharger la flotte (colonne Balance requise)",
)
fi8.metric(
    "Tps recharge le plus rapide",
    _na_or(row_com["temps_recharge_min_min"], ".1f") + (" min" if row_com["temps_recharge_min_min"] is not None else ""),
    help="Recharge de flotte la plus rapide observée",
)

st.caption(f"Compte propre détecté : **{row_com['compte_propre']}**  ·  Fichier source : *{row_com['fichier']}*")

# ──────────────────────────────────────────────────────────────────────────────
# Export Excel
# ──────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("#### Export Excel")

# DataFrame export (valeurs numériques sauf les N/A → remplacés par chaîne)
df_export = pd.DataFrame({
    "Commercial":                df_res["commercial"],
    "Fichier source":            df_res["fichier"],
    "Compte propre détecté":     df_res["compte_propre"],
    "Nb transactions":           df_res["nb_transactions"],
    "Jours actifs":              df_res["nb_jours_actifs"],
    "Transactions / jour":       df_res["transactions_par_jour"],
    "Clients touchés / jour":    df_res["clients_par_jour"],
    "Tps mort médian (min)":     df_res["temps_mort_median_min"],
    "Tps mort max (min)":        df_res["temps_mort_max_min"],
    "Tps recharge médian (min)": df_res["temps_recharge_med_min"],
    "Tps recharge min (min)":    df_res["temps_recharge_min_min"],
})

# Résumé réseau
n_avec_tm = int(df_res["temps_mort_median_min"].notna().sum())
n_avec_tr = int(df_res["temps_recharge_med_min"].notna().sum())
df_synthese = pd.DataFrame([
    {"Indicateur": "Commerciaux analysés",                  "Valeur": nb_com},
    {"Indicateur": "Total transactions",                     "Valeur": tot_tx},
    {"Indicateur": "Tx/jour moyen réseau",                   "Valeur": round(moy_tx_j, 2)},
    {"Indicateur": "Tx/jour maximum (meilleur)",             "Valeur": round(float(max_tx_j), 2)},
    {"Indicateur": "Tx/jour minimum (plus faible)",          "Valeur": round(float(min_tx_j), 2)},
    {"Indicateur": "Commerciaux avec données temps mort",    "Valeur": n_avec_tm},
    {"Indicateur": "Commerciaux avec données recharge",      "Valeur": n_avec_tr},
])

if not tps_mort_vals.empty:
    df_synthese = pd.concat([df_synthese, pd.DataFrame([
        {"Indicateur": "Tps mort médian réseau (min)",      "Valeur": round(float(tps_mort_vals.mean()), 1)},
        {"Indicateur": "Tps mort max observé réseau (min)", "Valeur": round(float(df_res["temps_mort_max_min"].dropna().max()), 1)},
    ])], ignore_index=True)

if not tps_rech_vals.empty:
    df_synthese = pd.concat([df_synthese, pd.DataFrame([
        {"Indicateur": "Tps recharge médian réseau (min)",  "Valeur": round(float(tps_rech_vals.mean()), 1)},
        {"Indicateur": "Tps recharge min réseau (min)",     "Valeur": round(float(df_res["temps_recharge_min_min"].dropna().min()), 1)},
    ])], ignore_index=True)

xlsx_react = export_df_to_excel(
    {
        "Synthèse réseau":          df_synthese,
        "Indicateurs par commercial": df_export,
    },
    titre="Réactivité Commerciale — ALBARKA",
    source_label="ALBARKA — Réactivité",
)

st.download_button(
    label="Télécharger le rapport (Excel)",
    data=xlsx_react,
    file_name="reactivite_commerciale.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="dl_reactivite",
)
