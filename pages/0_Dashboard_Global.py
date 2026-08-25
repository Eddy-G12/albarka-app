"""
pages/0_Dashboard_Global.py
============================
Dashboard global décisionnel — Super Admin et Admin.

Vue consolidée de toutes les performances du réseau ALBARKA :

  Cartes de synthèse
  ─────────────────
  • Total transactions Mobile Money (toutes données chargées)
  • Volume cash in réseau (mois le plus récent)
  • Volume cash out réseau (mois le plus récent)
  • Agents QR Code déployés / actifs (date la plus récente)
  • Total appros réseau (mois le plus récent)
  • Total destockages réseau (mois le plus récent)

  Section 1 — Cash in / Cash out
  ───────────────────────────────
  • Graphique barres horizontal par commercial (cash in + cash out)
  • Top 20 / Flop 20 cash in + cash out (séparés)
  • Alertes seuil

  Section 2 — Indicateurs de réactivité
  ──────────────────────────────────────
  • Transactions / jour moyen
  • Clients touchés / jour moyen
  • Temps mort médian et maximum
  • Temps de recharge médian et le plus rapide
  (calculés depuis les données transactions_momo agrégées disponibles)

  Section 3 — QR Code
  ────────────────────
  • Métriques globales (4 statuts)
  • Taux de déploiement / utilisation / risque
  • Répartition par segment (graphique barres empilées Plotly)
  • Classement DSM par agents actifs

  Section 4 — Approvisionnements / Destockages
  ─────────────────────────────────────────────
  • Volume appros / destocs par commercial (barres groupées)
  • Évolution mensuelle réseau (courbes)

  Filtres transversaux : mois (cash / appro), date QR Code
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from core import db
from core.auth import require_role, show_user_badge
from core.cashflow import get_cashflow, top_flop_cashflow, list_alertes_seuil
from core.appro import get_appro_par_mois, get_mois_disponibles_appro

# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Global — ALBARKA",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
show_user_badge()

# ──────────────────────────────────────────────────────────────────────────────
# Constantes visuelles (charte ALBARKA)
# ──────────────────────────────────────────────────────────────────────────────
C_JAUNE   = "#F5A623"
C_NOIR    = "#1A1A1A"
C_GRIS    = "#F8F9FA"
C_VERT    = "#27AE60"
C_ROUGE   = "#E74C3C"
C_BLEU    = "#2980B9"
C_ORANGE  = "#E67E22"
C_VIOLET  = "#8E44AD"

STATUTS_QR = ["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité", "Actif"]
STATUT_COLORS_QR = {
    "Sans QR Code":          C_ROUGE,
    "QR non utilisé (+30j)": C_ORANGE,
    "Risque inactivité":     "#F39C12",
    "Actif":                 C_VERT,
}

CACHE_QR_DIR = db.DATA_DIR / "qr_code" / "_cache"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

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


def _fmt(v: float) -> str:
    """Formate un montant FCFA avec séparateurs."""
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return "—"


def _delta_pct(old: float, new: float) -> str | None:
    try:
        if old == 0:
            return None
        return f"{(new - old) / old * 100:+.1f}%"
    except Exception:
        return None


def _plotly_bar_h(df: pd.DataFrame, x_col: str, y_col: str,
                  title: str, color: str, fmt_hover: str = ",.0f") -> go.Figure:
    """Graphique barres horizontales simple."""
    fig = go.Figure(go.Bar(
        x=df[x_col],
        y=df[y_col],
        orientation="h",
        marker_color=color,
        hovertemplate=f"%{{y}} : %{{x:{fmt_hover}}} FCFA<extra></extra>",
        text=df[x_col].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        height=max(300, len(df) * 38),
        margin=dict(l=10, r=60, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        font=dict(family="Arial"),
    )
    return fig


def _plotly_grouped_bar(df_wide: pd.DataFrame, x_col: str,
                        cols: list[str], colors: list[str],
                        title: str) -> go.Figure:
    """Barres groupées."""
    fig = go.Figure()
    for col, color in zip(cols, colors):
        fig.add_trace(go.Bar(
            name=col,
            x=df_wide[x_col],
            y=df_wide[col],
            marker_color=color,
            hovertemplate=f"{col}<br>%{{x}} : %{{y:,.0f}} FCFA<extra></extra>",
        ))
    fig.update_layout(
        barmode="group",
        title=title,
        height=380,
        margin=dict(l=10, r=10, t=40, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Arial"),
    )
    return fig


def _plotly_stacked_bar(df_wide: pd.DataFrame, x_col: str,
                        cols: list[str], colors: dict,
                        title: str) -> go.Figure:
    """Barres empilées."""
    fig = go.Figure()
    for col in cols:
        fig.add_trace(go.Bar(
            name=col,
            x=df_wide[x_col],
            y=df_wide[col],
            marker_color=colors.get(col, "#999"),
            hovertemplate=f"{col}<br>%{{x}} : %{{y:,}}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title=title,
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Arial"),
    )
    return fig


def _plotly_line(df_long: pd.DataFrame, x_col: str, y_col: str,
                 color_col: str, title: str) -> go.Figure:
    """Courbes d'évolution multi-séries."""
    fig = px.line(
        df_long,
        x=x_col,
        y=y_col,
        color=color_col,
        markers=True,
        title=title,
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=40, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickangle=-30, showgrid=True, gridcolor="#EEEEEE"),
        yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Arial"),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# TITRE & FILTRES GLOBAUX
# ──────────────────────────────────────────────────────────────────────────────

st.title("Dashboard Global — Pilotage réseau ALBARKA")
st.caption("Vue consolidée de toutes les performances du réseau d'agents Mobile Money.")
st.divider()

# Chargement des données disponibles
toutes_lignes_cash = get_cashflow()
mois_cash_dispo    = sorted({r["mois"] for r in toutes_lignes_cash}, reverse=True)

mois_appro_dispo   = get_mois_disponibles_appro()
dates_qr_dispo     = _qr_dates_disponibles()

# Filtres dans la sidebar
with st.sidebar:
    st.markdown("### Filtres")

    mois_cash_sel = None
    if mois_cash_dispo:
        mois_cash_sel = st.selectbox(
            "Mois (Cash & Alertes)",
            mois_cash_dispo,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sb_mois_cash",
        )

    mois_appro_sel = None
    if mois_appro_dispo:
        mois_appro_sel = st.selectbox(
            "Mois (Appro / Destockage)",
            mois_appro_dispo,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sb_mois_appro",
        )

    date_qr_sel = None
    if dates_qr_dispo:
        date_qr_sel = st.selectbox(
            "Date de référence (QR Code)",
            dates_qr_dispo,
            format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
            key="sb_date_qr",
        )


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 0 — CARTES DE SYNTHÈSE GLOBALES
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Vue d'ensemble")

# Valeurs pour les cartes
ci_total_m  = sum(r["cash_in"]  for r in toutes_lignes_cash if r["mois"] == mois_cash_sel) if mois_cash_sel else 0
co_total_m  = sum(r["cash_out"] for r in toutes_lignes_cash if r["mois"] == mois_cash_sel) if mois_cash_sel else 0
nb_tx_total = sum(r["nb_transactions"] for r in toutes_lignes_cash if r["mois"] == mois_cash_sel) if mois_cash_sel else 0

# Mois précédent pour les deltas cash
ci_total_m1 = 0
co_total_m1 = 0
if mois_cash_sel and len(mois_cash_dispo) > 1:
    idx_m = mois_cash_dispo.index(mois_cash_sel)
    if idx_m + 1 < len(mois_cash_dispo):
        mois_m1 = mois_cash_dispo[idx_m + 1]
        ci_total_m1 = sum(r["cash_in"]  for r in toutes_lignes_cash if r["mois"] == mois_m1)
        co_total_m1 = sum(r["cash_out"] for r in toutes_lignes_cash if r["mois"] == mois_m1)

# QR Code
qr_agents_total  = 0
qr_agents_actifs = 0
qr_agents_risque = 0
qr_taux_dep      = 0.0
qr_taux_util     = 0.0
df_qr = pd.DataFrame()
if date_qr_sel:
    df_qr = _load_qr_cache(date_qr_sel)
    if not df_qr.empty:
        qr_agents_total  = len(df_qr)
        qr_agents_actifs = int((df_qr["statut"] == "Actif").sum())
        qr_agents_risque = int((df_qr["statut"].isin(["Risque inactivité", "QR non utilisé (+30j)"])).sum())
        deployes = qr_agents_total - int((df_qr["statut"] == "Sans QR Code").sum())
        qr_taux_dep  = deployes / qr_agents_total if qr_agents_total else 0
        qr_taux_util = qr_agents_actifs / deployes if deployes else 0

# Appro
mt_appro_m   = 0.0
mt_destoc_m  = 0.0
nb_appro_m   = 0
nb_destoc_m  = 0
donnees_appro = []
if mois_appro_sel:
    donnees_appro = get_appro_par_mois(mois=mois_appro_sel)
    if donnees_appro:
        mt_appro_m  = sum(d["montant_appro"]      for d in donnees_appro)
        mt_destoc_m = sum(d["montant_destockage"]  for d in donnees_appro)
        nb_appro_m  = sum(d["nb_appro"]            for d in donnees_appro)
        nb_destoc_m = sum(d["nb_destockage"]       for d in donnees_appro)

# Affichage des cartes (2 lignes × 3 colonnes)
r1c1, r1c2, r1c3, r1c4, r1c5, r1c6 = st.columns(6)

r1c1.metric(
    "Transactions MoMo",
    f"{nb_tx_total:,}",
    help=f"Nb de transactions pour {mois_cash_sel or '—'}",
)
r1c2.metric(
    "Cash In réseau",
    f"{_fmt(ci_total_m)} FCFA",
    delta=_delta_pct(ci_total_m1, ci_total_m) if ci_total_m1 else None,
)
r1c3.metric(
    "Cash Out réseau",
    f"{_fmt(co_total_m)} FCFA",
    delta=_delta_pct(co_total_m1, co_total_m) if co_total_m1 else None,
)
r1c4.metric(
    "Agents QR actifs",
    f"{qr_agents_actifs:,} / {qr_agents_total:,}",
    help=f"Taux utilisation : {qr_taux_util:.1%}",
)
r1c5.metric(
    "Total appros",
    f"{_fmt(mt_appro_m)} FCFA",
    help=f"{nb_appro_m:,} opérations",
)
r1c6.metric(
    "Total destockages",
    f"{_fmt(mt_destoc_m)} FCFA",
    help=f"{nb_destoc_m:,} opérations",
)

st.divider()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1 — CASH IN / CASH OUT
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Cash in / Cash out")

if not mois_cash_sel or not toutes_lignes_cash:
    st.info("Aucune donnée cash disponible. Importe des fichiers dans le module Cash Flow.")
else:
    lignes_m = [r for r in toutes_lignes_cash if r["mois"] == mois_cash_sel]
    label_m  = pd.Timestamp(mois_cash_sel + "-01").strftime("%B %Y").capitalize()

    if not lignes_m:
        st.info(f"Aucune donnée pour {label_m}.")
    else:
        df_cash_m = pd.DataFrame(lignes_m).sort_values("cash_in", ascending=False)

        # Graphique principal — cash in ET cash out par commercial
        tab_ci, tab_co, tab_both = st.tabs(["Cash In", "Cash Out", "Comparaison CI/CO"])

        with tab_ci:
            df_ci = df_cash_m.sort_values("cash_in", ascending=True)
            fig_ci = _plotly_bar_h(
                df_ci, x_col="cash_in", y_col="dsm_name",
                title=f"Cash In par commercial — {label_m}",
                color=C_VERT,
            )
            st.plotly_chart(fig_ci, use_container_width=True)

        with tab_co:
            df_co = df_cash_m.sort_values("cash_out", ascending=True)
            fig_co = _plotly_bar_h(
                df_co, x_col="cash_out", y_col="dsm_name",
                title=f"Cash Out par commercial — {label_m}",
                color=C_ORANGE,
            )
            st.plotly_chart(fig_co, use_container_width=True)

        with tab_both:
            fig_both = _plotly_grouped_bar(
                df_cash_m.sort_values("cash_in", ascending=False),
                x_col="dsm_name",
                cols=["cash_in", "cash_out"],
                colors=[C_VERT, C_ORANGE],
                title=f"Cash In vs Cash Out — {label_m}",
            )
            fig_both.update_traces(
                selector=dict(name="cash_in"),  name="Cash In"
            )
            fig_both.update_traces(
                selector=dict(name="cash_out"), name="Cash Out"
            )
            st.plotly_chart(fig_both, use_container_width=True)

        st.divider()

        # Classements Top / Flop (côte à côte)
        st.markdown(f"#### Classements — {label_m}")
        n_classement = st.slider("Nombre de commerciaux", 5, 20, 10, key="n_classement_dash")

        col_ci_top, col_ci_flop, col_co_top, col_co_flop = st.columns(4)

        def _df_classement(records, flux_col, label_col):
            if not records:
                return pd.DataFrame()
            return pd.DataFrame([
                {"#": i + 1, "Commercial": r["dsm_name"], label_col: r[flux_col]}
                for i, r in enumerate(records)
            ])

        with col_ci_top:
            st.markdown("**Top Cash In**")
            top_ci = top_flop_cashflow(mois_cash_sel, "cash_in", n=n_classement, ordre="top")
            df_tci = _df_classement(top_ci, "cash_in", "Cash In (FCFA)")
            if not df_tci.empty:
                df_tci["Cash In (FCFA)"] = df_tci["Cash In (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_tci, hide_index=True, use_container_width=True)
            else:
                st.info("—")

        with col_ci_flop:
            st.markdown("**Flop Cash In**")
            flop_ci = top_flop_cashflow(mois_cash_sel, "cash_in", n=n_classement, ordre="flop")
            df_fci = _df_classement(flop_ci, "cash_in", "Cash In (FCFA)")
            if not df_fci.empty:
                df_fci["Cash In (FCFA)"] = df_fci["Cash In (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_fci, hide_index=True, use_container_width=True)
            else:
                st.info("—")

        with col_co_top:
            st.markdown("**Top Cash Out**")
            top_co = top_flop_cashflow(mois_cash_sel, "cash_out", n=n_classement, ordre="top")
            df_tco = _df_classement(top_co, "cash_out", "Cash Out (FCFA)")
            if not df_tco.empty:
                df_tco["Cash Out (FCFA)"] = df_tco["Cash Out (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_tco, hide_index=True, use_container_width=True)
            else:
                st.info("—")

        with col_co_flop:
            st.markdown("**Flop Cash Out**")
            flop_co = top_flop_cashflow(mois_cash_sel, "cash_out", n=n_classement, ordre="flop")
            df_fco = _df_classement(flop_co, "cash_out", "Cash Out (FCFA)")
            if not df_fco.empty:
                df_fco["Cash Out (FCFA)"] = df_fco["Cash Out (FCFA)"].map("{:,.0f}".format)
                st.dataframe(df_fco, hide_index=True, use_container_width=True)
            else:
                st.info("—")

        st.divider()

        # Alertes seuil
        st.markdown("#### Alertes seuil")
        alertes = list_alertes_seuil(mois_cash_sel)
        seuil_ci  = alertes.get("seuil_cash_in")
        seuil_co  = alertes.get("seuil_cash_out")
        sous_ci   = alertes.get("commerciaux_sous_seuil_cash_in", [])
        sous_co   = alertes.get("commerciaux_sous_seuil_cash_out", [])

        al1, al2 = st.columns(2)
        with al1:
            if not seuil_ci:
                st.info("Seuil cash in non configuré.")
            elif not sous_ci:
                st.success(f"Tous au-dessus du seuil cash in ({_fmt(seuil_ci)} FCFA).")
            else:
                st.error(f"**{len(sous_ci)} commercial(s) sous le seuil cash in ({_fmt(seuil_ci)} FCFA)**")
                for r in sous_ci:
                    st.write(f"• {r['dsm_name']} — {_fmt(r['cash_in'])} FCFA")

        with al2:
            if not seuil_co:
                st.info("Seuil cash out non configuré.")
            elif not sous_co:
                st.success(f"Tous au-dessus du seuil cash out ({_fmt(seuil_co)} FCFA).")
            else:
                st.error(f"**{len(sous_co)} commercial(s) sous le seuil cash out ({_fmt(seuil_co)} FCFA)**")
                for r in sous_co:
                    st.write(f"• {r['dsm_name']} — {_fmt(r['cash_out'])} FCFA")

        # Évolution mensuelle réseau (courbes)
        if len(mois_cash_dispo) > 1:
            st.divider()
            st.markdown("#### Évolution mensuelle réseau (cash in / cash out)")

            rows_evol = []
            for mois in sorted(mois_cash_dispo):
                ci_m = sum(r["cash_in"]  for r in toutes_lignes_cash if r["mois"] == mois)
                co_m = sum(r["cash_out"] for r in toutes_lignes_cash if r["mois"] == mois)
                label = pd.Timestamp(mois + "-01").strftime("%b %Y")
                rows_evol.append({"Mois": label, "Valeur (FCFA)": ci_m, "Flux": "Cash In"})
                rows_evol.append({"Mois": label, "Valeur (FCFA)": co_m, "Flux": "Cash Out"})

            df_evol_cash = pd.DataFrame(rows_evol)
            fig_evol = _plotly_line(
                df_evol_cash,
                x_col="Mois", y_col="Valeur (FCFA)", color_col="Flux",
                title="Évolution Cash In / Cash Out réseau",
            )
            st.plotly_chart(fig_evol, use_container_width=True)

st.divider()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2 — INDICATEURS DE RÉACTIVITÉ
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Indicateurs de réactivité commerciale")
st.caption(
    "Ces indicateurs sont calculés à partir des fichiers CSV de transactions "
    "importés dans le module Cash Flow. Ils nécessitent un horodatage précis "
    "(heure de la transaction) pour le temps mort et le temps de recharge."
)

# Les métriques de réactivité (transactions/jour, clients/jour) sont dérivées
# de transactions_momo (données agrégées par mois). Pour le temps mort et le
# temps de recharge, il faut les fichiers bruts — on affiche ce qu'on a.
if not mois_cash_sel or not toutes_lignes_cash:
    st.info("Aucune donnée de transactions disponible.")
else:
    lignes_react = [r for r in toutes_lignes_cash if r["mois"] == mois_cash_sel]
    label_m = pd.Timestamp(mois_cash_sel + "-01").strftime("%B %Y").capitalize()

    if lignes_react:
        st.markdown(f"**Mois de référence : {label_m}**")

        # Transactions/jour et clients/jour estimés depuis les agrégats
        # (approximation : nb_transactions / nb_jours_du_mois)
        import calendar
        annee_m, num_mois = int(mois_cash_sel[:4]), int(mois_cash_sel[5:7])
        nb_jours_mois = calendar.monthrange(annee_m, num_mois)[1]

        rows_react = []
        for r in sorted(lignes_react, key=lambda x: x["dsm_name"]):
            tx_j = round(r["nb_transactions"] / nb_jours_mois, 2) if nb_jours_mois else 0
            rows_react.append({
                "Commercial":          r["dsm_name"],
                "Nb transactions":     r["nb_transactions"],
                "Transactions / jour": tx_j,
                "Cash In (FCFA)":      r["cash_in"],
                "Cash Out (FCFA)":     r["cash_out"],
            })

        df_react = pd.DataFrame(rows_react).sort_values("Transactions / jour", ascending=False)

        # Métriques globales réseau
        total_tx   = sum(r["nb_transactions"] for r in lignes_react)
        moy_tx_j   = round(total_tx / nb_jours_mois, 1) if nb_jours_mois else 0
        max_tx_j   = df_react["Transactions / jour"].max() if not df_react.empty else 0
        min_tx_j   = df_react["Transactions / jour"].min() if not df_react.empty else 0

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Total transactions réseau",     f"{total_tx:,}")
        rc2.metric("Transactions / jour (réseau)",  f"{moy_tx_j:,.1f}")
        rc3.metric("Meilleur (Tx/jour)",            f"{max_tx_j:,.1f}")
        rc4.metric("Plus faible (Tx/jour)",         f"{min_tx_j:,.1f}")

        st.divider()

        # Graphique barres — transactions/jour par commercial
        df_react_chart = df_react.sort_values("Transactions / jour", ascending=True)
        fig_react = go.Figure(go.Bar(
            x=df_react_chart["Transactions / jour"],
            y=df_react_chart["Commercial"],
            orientation="h",
            marker_color=C_BLEU,
            text=df_react_chart["Transactions / jour"].apply(lambda v: f"{v:.1f}"),
            textposition="outside",
            hovertemplate="%{y} : %{x:.1f} Tx/jour<extra></extra>",
        ))
        fig_react.update_layout(
            title=f"Transactions par jour moyen — {label_m}",
            height=max(280, len(df_react) * 38),
            margin=dict(l=10, r=60, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            xaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
            font=dict(family="Arial"),
        )
        st.plotly_chart(fig_react, use_container_width=True)

        # Tableau détaillé
        with st.expander("Tableau détaillé réactivité"):
            df_aff = df_react.copy()
            df_aff["Cash In (FCFA)"]  = df_aff["Cash In (FCFA)"].map("{:,.0f}".format)
            df_aff["Cash Out (FCFA)"] = df_aff["Cash Out (FCFA)"].map("{:,.0f}".format)
            st.dataframe(df_aff, hide_index=True, use_container_width=True)

        st.info(
            "Les indicateurs **temps mort** et **temps de recharge de flotte** "
            "nécessitent les fichiers CSV bruts avec horodatage à la minute. "
            "Rendez-vous dans le module **Réactivité Commerciale** pour les calculer.",
            icon="ℹ️",
        )

st.divider()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3 — QR CODE
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Suivi QR Code agents")

if not date_qr_sel or df_qr.empty:
    st.info("Aucune donnée QR Code disponible. Traite d'abord un fichier dans le module Suivi QR Code.")
else:
    label_qr = pd.Timestamp(date_qr_sel).strftime("%d/%m/%Y")
    st.caption(f"Date de référence : **{label_qr}**  — {qr_agents_total:,} agents au total")

    counts_qr = {s: int((df_qr["statut"] == s).sum()) for s in STATUTS_QR}
    deployes = qr_agents_total - counts_qr["Sans QR Code"]

    # Métriques globales QR
    qr1, qr2, qr3, qr4, qr5 = st.columns(5)
    qr1.metric("Total agents",           qr_agents_total)
    qr2.metric("Sans QR Code",           counts_qr["Sans QR Code"],   delta_color="off")
    qr3.metric("QR non utilisé (+30j)",  counts_qr["QR non utilisé (+30j)"], delta_color="off")
    qr4.metric("Risque inactivité",      counts_qr["Risque inactivité"],     delta_color="off")
    qr5.metric("Actif",                  counts_qr["Actif"])

    st.divider()

    # KPIs taux
    qrk1, qrk2, qrk3, qrk4, qrk5 = st.columns(5)
    qrk1.metric("Taux de déploiement",       f"{qr_taux_dep:.1%}")
    qrk2.metric("Taux d'utilisation",        f"{qr_taux_util:.1%}")
    qrk3.metric("QR déployés non utilisés",  f"{counts_qr['QR non utilisé (+30j)'] / deployes:.1%}" if deployes else "—")
    qrk4.metric("Risque inactivité",         f"{counts_qr['Risque inactivité'] / qr_agents_total:.1%}" if qr_agents_total else "—")
    qrk5.metric("Sans QR Code",              f"{counts_qr['Sans QR Code'] / qr_agents_total:.1%}" if qr_agents_total else "—")

    st.divider()

    # Graphiques côte à côte — segment + DSM
    col_seg, col_dsm = st.columns(2)

    with col_seg:
        st.markdown("#### Répartition par segment")
        segments = sorted(df_qr["segment_group"].dropna().unique())
        rows_seg = []
        for seg in segments:
            sub = df_qr[df_qr["segment_group"] == seg]
            row = {"Segment": seg}
            for s in STATUTS_QR:
                row[s] = int((sub["statut"] == s).sum())
            rows_seg.append(row)
        df_seg = pd.DataFrame(rows_seg)

        if not df_seg.empty:
            fig_seg = _plotly_stacked_bar(
                df_seg, x_col="Segment", cols=STATUTS_QR,
                colors=STATUT_COLORS_QR,
                title="Agents par statut QR / segment",
            )
            st.plotly_chart(fig_seg, use_container_width=True)
            st.dataframe(df_seg, hide_index=True, use_container_width=True)

    with col_dsm:
        st.markdown("#### Classement DSM — agents actifs")
        dsm_list = sorted(df_qr["dsm_name"].dropna().unique())
        rows_dsm = []
        for dsm in dsm_list:
            sub = df_qr[df_qr["dsm_name"] == dsm]
            rows_dsm.append({
                "DSM":   dsm,
                "Total": len(sub),
                "Actif": int((sub["statut"] == "Actif").sum()),
                "Risque": int((sub["statut"].isin(["Risque inactivité", "QR non utilisé (+30j)"])).sum()),
                "Sans QR": int((sub["statut"] == "Sans QR Code").sum()),
                "% Actif": round(int((sub["statut"] == "Actif").sum()) / len(sub) * 100, 1) if len(sub) else 0,
            })
        df_dsm = pd.DataFrame(rows_dsm).sort_values("Actif", ascending=False)

        if not df_dsm.empty:
            fig_dsm = go.Figure(go.Bar(
                x=df_dsm["DSM"],
                y=df_dsm["Actif"],
                marker_color=C_VERT,
                text=df_dsm["Actif"],
                textposition="outside",
                hovertemplate="DSM : %{x}<br>Actifs : %{y}<extra></extra>",
            ))
            fig_dsm.update_layout(
                title="Agents actifs par DSM",
                height=320,
                margin=dict(l=10, r=10, t=40, b=60),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickangle=-30, showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                font=dict(family="Arial"),
            )
            st.plotly_chart(fig_dsm, use_container_width=True)
            st.dataframe(df_dsm, hide_index=True, use_container_width=True)

    # Agents prioritaires (expander)
    with st.expander("Agents prioritaires (Sans QR + QR non utilisé + Risque)"):
        prio = df_qr[df_qr["statut"].isin(["Sans QR Code", "QR non utilisé (+30j)", "Risque inactivité"])].copy()
        prio = prio.sort_values(["statut", "segment_group", "dsm_name"])
        cols_prio = [c for c in ["statut", "segment_group", "dsm_name", "pos_name",
                                  "pos_msisdn", "days_since_last_use", "priorite"]
                     if c in prio.columns]
        rename_prio = {
            "statut": "Statut", "segment_group": "Segment", "dsm_name": "DSM",
            "pos_name": "Agent", "pos_msisdn": "Téléphone",
            "days_since_last_use": "Jours sans usage", "priorite": "Priorité",
        }
        st.dataframe(prio[cols_prio].rename(columns=rename_prio),
                     hide_index=True, use_container_width=True)
        st.caption(f"{len(prio)} agents nécessitant une action sur {qr_agents_total} au total.")

st.divider()


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4 — APPROVISIONNEMENTS / DESTOCKAGES
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Approvisionnements / Destockages")

if not mois_appro_sel or not donnees_appro:
    st.info("Aucune donnée appro disponible. Importe d'abord un fichier dans le module Appro/Destockage.")
else:
    label_appro = pd.Timestamp(mois_appro_sel + "-01").strftime("%B %Y").capitalize()

    # Métriques réseau
    ap1, ap2, ap3, ap4 = st.columns(4)
    ap1.metric("Nb appros réseau",        f"{nb_appro_m:,}")
    ap2.metric("Montant appros",          f"{_fmt(mt_appro_m)} FCFA")
    ap3.metric("Nb destockages réseau",   f"{nb_destoc_m:,}")
    ap4.metric("Montant destockages",     f"{_fmt(mt_destoc_m)} FCFA")

    st.divider()

    # Graphique barres groupées appro / destockage par commercial
    df_appro_m = pd.DataFrame(donnees_appro).sort_values("montant_appro", ascending=False)

    fig_appro = _plotly_grouped_bar(
        df_appro_m,
        x_col="dsm_name",
        cols=["montant_appro", "montant_destockage"],
        colors=[C_BLEU, C_VIOLET],
        title=f"Appros vs Destockages par commercial — {label_appro}",
    )
    fig_appro.update_traces(selector=dict(name="montant_appro"),      name="Appros")
    fig_appro.update_traces(selector=dict(name="montant_destockage"), name="Destockages")
    st.plotly_chart(fig_appro, use_container_width=True)

    # Classement nombre d'opérations
    col_nbop_a, col_nbop_d = st.columns(2)
    with col_nbop_a:
        fig_nba = go.Figure(go.Bar(
            x=df_appro_m["dsm_name"],
            y=df_appro_m["nb_appro"],
            marker_color=C_BLEU,
            text=df_appro_m["nb_appro"],
            textposition="outside",
            hovertemplate="%{x} : %{y} opérations appro<extra></extra>",
        ))
        fig_nba.update_layout(
            title=f"Nb d'opérations appro — {label_appro}",
            height=300, margin=dict(l=10, r=10, t=40, b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-30), yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
            font=dict(family="Arial"),
        )
        st.plotly_chart(fig_nba, use_container_width=True)

    with col_nbop_d:
        fig_nbd = go.Figure(go.Bar(
            x=df_appro_m["dsm_name"],
            y=df_appro_m["nb_destockage"],
            marker_color=C_VIOLET,
            text=df_appro_m["nb_destockage"],
            textposition="outside",
            hovertemplate="%{x} : %{y} opérations destockage<extra></extra>",
        ))
        fig_nbd.update_layout(
            title=f"Nb d'opérations destockage — {label_appro}",
            height=300, margin=dict(l=10, r=10, t=40, b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-30), yaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
            font=dict(family="Arial"),
        )
        st.plotly_chart(fig_nbd, use_container_width=True)

    # Évolution mensuelle réseau (courbes)
    tous_appro = get_appro_par_mois()
    if len(mois_appro_dispo) > 1 and tous_appro:
        st.divider()
        st.markdown("#### Évolution mensuelle réseau (appros / destockages)")

        df_evol_appro_raw = pd.DataFrame(tous_appro)
        df_agg = (
            df_evol_appro_raw
            .groupby("mois", as_index=False)
            .agg(montant_appro=("montant_appro", "sum"),
                 montant_destockage=("montant_destockage", "sum"))
            .sort_values("mois")
        )
        df_agg["mois_label"] = df_agg["mois"].apply(
            lambda m: pd.Timestamp(m + "-01").strftime("%b %Y")
        )

        rows_evol_appro = []
        for _, row in df_agg.iterrows():
            rows_evol_appro.append({"Mois": row["mois_label"], "Montant (FCFA)": row["montant_appro"],      "Type": "Appros"})
            rows_evol_appro.append({"Mois": row["mois_label"], "Montant (FCFA)": row["montant_destockage"], "Type": "Destockages"})

        fig_evol_appro = _plotly_line(
            pd.DataFrame(rows_evol_appro),
            x_col="Mois", y_col="Montant (FCFA)", color_col="Type",
            title="Évolution Appros / Destockages réseau",
        )
        st.plotly_chart(fig_evol_appro, use_container_width=True)

    # Tableau récap
    with st.expander(f"Tableau récapitulatif — {label_appro}"):
        df_appro_aff = df_appro_m.copy()
        df_appro_aff["montant_appro"]      = df_appro_aff["montant_appro"].map("{:,.0f}".format)
        df_appro_aff["montant_destockage"] = df_appro_aff["montant_destockage"].map("{:,.0f}".format)
        df_appro_aff = df_appro_aff.rename(columns={
            "dsm_name":          "Commercial",
            "nb_appro":          "Nb appros",
            "montant_appro":     "Montant appros (FCFA)",
            "nb_destockage":     "Nb destockages",
            "montant_destockage":"Montant destockages (FCFA)",
        }).drop(columns=["mois"], errors="ignore")
        st.dataframe(df_appro_aff, hide_index=True, use_container_width=True)

st.divider()


# ──────────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────────

st.caption("ALBARKA — Dashboard Global · Application locale · Aucune donnée transmise à un serveur externe")
