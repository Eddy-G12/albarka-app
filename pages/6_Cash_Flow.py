"""
pages/6_Cash_Flow.py — v2
===========================
Volet Cash in / Cash out — source SAE MTN.

Super Admin : dépose les fichiers SAE, configure les seuils.
Admin       : consulte classements, alertes, MoM — pas d'import.

Onglets :
  1. Import SAE         (Super Admin uniquement)
  2. Classements        Top 20 / Flop 20 par mois, sur les POS
  3. Alertes seuil      POS sous le seuil configuré
  4. Comparaison MoM    2 ou 3 fichiers SAE → Top/Flop/Cumulé/Constants
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core import db
from core.auth import require_role, show_user_badge, get_role
from core.ui import apply_theme, show_page_header
from core.cashflow import (
    import_sae_file,
    list_alertes_seuil_pos,
    compute_mom_multi,
    _detect_mois_from_filename,
)
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin", "admin")
show_user_badge()

role = get_role()

show_page_header("Cash Flow", "Source : fichier SAE MTN — classements POS, alertes, MoM")
st.divider()

# Onglets selon le rôle (Super Admin voit Import, Admin non)
if role == "super_admin":
    tab_import, tab_class, tab_alertes, tab_mom = st.tabs([
        "Import SAE", "Classements", "Alertes seuil", "Comparaison MoM"
    ])
else:
    tab_import = None
    tab_class, tab_alertes, tab_mom = st.tabs([
        "Classements", "Alertes seuil", "Comparaison MoM"
    ])


# ===========================================================================
# ONGLET 1 — IMPORT SAE (Super Admin uniquement)
# ===========================================================================
if tab_import is not None:
    with tab_import:
        st.subheader("Importer un fichier SAE MTN")
        st.write(
            "Le fichier SAE contient une ligne par POS (agent terrain). "
            "Colonnes attendues : `acceptorid`, `agent_msisdn`, `agent_name`, "
            "`cash_in_com`, `cash_out_com`. Formats acceptés : `.xlsx` et `.csv`."
        )

        fichier_sae = st.file_uploader(
            "Fichier SAE (.xlsx ou .csv)",
            type=["xlsx", "csv"],
            key="up_sae",
        )

        mois_manuel = st.text_input(
            "Mois (optionnel — détecté automatiquement depuis le nom du fichier)",
            placeholder="ex. 2026-07",
            key="mois_sae",
        )

        if fichier_sae:
            mois_detecte = _detect_mois_from_filename(fichier_sae.name)
            if mois_detecte and not mois_manuel:
                st.caption(f"Mois détecté depuis le nom du fichier : **{mois_detecte}**")

        if st.button("Importer", key="btn_import_sae") and fichier_sae:
            try:
                fichier_sae.seek(0)
                mois_val = mois_manuel.strip() or None
                resultat = import_sae_file(
                    fichier_sae,
                    nom_fichier=fichier_sae.name,
                    mois=mois_val,
                )
                label_mois = pd.Timestamp(resultat["mois"] + "-01").strftime("%B %Y").capitalize()
                st.success(
                    f"Import réussi — **{label_mois}** — "
                    f"{resultat['nb_pos']:,} POS — "
                    f"Cash In total : {resultat['total_cash_in']:,.0f} FCFA — "
                    f"Cash Out total : {resultat['total_cash_out']:,.0f} FCFA"
                )
            except Exception as e:
                st.error(f"Erreur : {e}")


# ===========================================================================
# ONGLET 2 — CLASSEMENTS
# ===========================================================================
with tab_class:
    st.subheader("Classements Top 20 / Flop 20 — POS")

    mois_dispo = db.list_mois_cashflow_pos()

    if not mois_dispo:
        st.info("Aucune donnée disponible. Importe un fichier SAE dans l'onglet Import.")
    else:
        mois_sel = st.selectbox(
            "Mois",
            mois_dispo,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_class",
        )

        n_sel = st.slider("Nombre de POS à afficher", 5, 50, 20, key="n_class")
        label_mois_c = pd.Timestamp(mois_sel + "-01").strftime("%B %Y").capitalize()

        tab_ci_c, tab_co_c = st.tabs(["Cash In", "Cash Out"])

        def _df_classement(records: list, flux_col: str, label: str) -> pd.DataFrame:
            return pd.DataFrame([
                {
                    "#": i + 1,
                    "POS ID": r["acceptorid"],
                    "MSISDN": r.get("agent_msisdn", ""),
                    "Nom agent": r.get("agent_name", ""),
                    label: r[flux_col],
                }
                for i, r in enumerate(records)
            ])

        def _bar_h_pos(df: pd.DataFrame, val_col: str, title: str, color: str) -> go.Figure:
            df_s = df.sort_values(val_col, ascending=True).tail(20)
            fig = go.Figure(go.Bar(
                x=df_s[val_col], y=df_s["Nom agent"].fillna(df_s["POS ID"]),
                orientation="h", marker_color=color,
                text=df_s[val_col].apply(lambda v: f"{v:,.0f}"),
                textposition="outside",
                hovertemplate="%{y} : %{x:,.0f} FCFA<extra></extra>",
            ))
            fig.update_layout(
                title=title, height=max(300, len(df_s) * 36),
                margin=dict(l=10, r=80, t=40, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed"),
                xaxis=dict(showgrid=True, gridcolor="#EEEEEE"),
                font=dict(family="Arial"),
            )
            return fig

        with tab_ci_c:
            col_top, col_flop = st.columns(2)
            top_ci  = db.top_flop_pos(mois_sel, "cash_in", n=n_sel, ordre="top")
            flop_ci = db.top_flop_pos(mois_sel, "cash_in", n=n_sel, ordre="flop")

            with col_top:
                st.markdown(f"**Top {n_sel} Cash In — {label_mois_c}**")
                if top_ci:
                    df_tci = _df_classement(top_ci, "cash_in", "Cash In (FCFA)")
                    st.plotly_chart(_bar_h_pos(df_tci, "Cash In (FCFA)",
                                               f"Top Cash In — {label_mois_c}", "#27AE60"),
                                    use_container_width=True)
                    df_tci["Cash In (FCFA)"] = df_tci["Cash In (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_tci, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

            with col_flop:
                st.markdown(f"**Flop {n_sel} Cash In — {label_mois_c}**")
                if flop_ci:
                    df_fci = _df_classement(flop_ci, "cash_in", "Cash In (FCFA)")
                    df_fci["Cash In (FCFA)"] = df_fci["Cash In (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_fci, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

        with tab_co_c:
            col_top2, col_flop2 = st.columns(2)
            top_co  = db.top_flop_pos(mois_sel, "cash_out", n=n_sel, ordre="top")
            flop_co = db.top_flop_pos(mois_sel, "cash_out", n=n_sel, ordre="flop")

            with col_top2:
                st.markdown(f"**Top {n_sel} Cash Out — {label_mois_c}**")
                if top_co:
                    df_tco = _df_classement(top_co, "cash_out", "Cash Out (FCFA)")
                    st.plotly_chart(_bar_h_pos(df_tco, "Cash Out (FCFA)",
                                               f"Top Cash Out — {label_mois_c}", "#E67E22"),
                                    use_container_width=True)
                    df_tco["Cash Out (FCFA)"] = df_tco["Cash Out (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_tco, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

            with col_flop2:
                st.markdown(f"**Flop {n_sel} Cash Out — {label_mois_c}**")
                if flop_co:
                    df_fco = _df_classement(flop_co, "cash_out", "Cash Out (FCFA)")
                    df_fco["Cash Out (FCFA)"] = df_fco["Cash Out (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_fco, hide_index=True, use_container_width=True)
                else:
                    st.info("Pas de données.")

        # Export Excel classements
        st.divider()
        sheets_cl: dict = {}
        for lbl, records, flux in [
            (f"Top {n_sel} CI",  top_ci,  "cash_in"),
            (f"Flop {n_sel} CI", flop_ci, "cash_in"),
            (f"Top {n_sel} CO",  top_co,  "cash_out"),
            (f"Flop {n_sel} CO", flop_co, "cash_out"),
        ]:
            if records:
                col_lbl = "Cash In (FCFA)" if "CI" in lbl else "Cash Out (FCFA)"
                sheets_cl[lbl] = pd.DataFrame([
                    {"#": i+1, "POS ID": r["acceptorid"],
                     "MSISDN": r.get("agent_msisdn",""), "Nom": r.get("agent_name",""),
                     col_lbl: r[flux]}
                    for i, r in enumerate(records)
                ])
        if sheets_cl:
            xlsx_cl = export_df_to_excel(
                sheets_cl,
                titre=f"Classements Cash Flow — {label_mois_c}",
                source_label="ALBARKA — SAE",
            )
            st.download_button(
                "Exporter classements (Excel)",
                data=xlsx_cl,
                file_name=f"classements_cashflow_{mois_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_class_cf",
            )


# ===========================================================================
# ONGLET 3 — ALERTES SEUIL
# ===========================================================================
with tab_alertes:
    st.subheader("Alertes — POS sous le seuil")

    mois_dispo_al = db.list_mois_cashflow_pos()

    if not mois_dispo_al:
        st.info("Aucune donnée disponible.")
    else:
        mois_al = st.selectbox(
            "Mois",
            mois_dispo_al,
            format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize(),
            key="sel_mois_alertes",
        )

        alertes = list_alertes_seuil_pos(mois_al)
        seuil_ci = alertes["seuil_cash_in"]
        seuil_co = alertes["seuil_cash_out"]
        sous_ci  = alertes["pos_sous_seuil_cash_in"]
        sous_co  = alertes["pos_sous_seuil_cash_out"]

        label_mois_al = pd.Timestamp(mois_al + "-01").strftime("%B %Y").capitalize()

        m1, m2 = st.columns(2)
        m1.metric("Seuil cash in",  f"{seuil_ci:,.0f} FCFA" if seuil_ci else "Non défini")
        m2.metric("Seuil cash out", f"{seuil_co:,.0f} FCFA" if seuil_co else "Non défini")

        if not seuil_ci and not seuil_co:
            st.warning("Aucun seuil configuré. Configure les seuils dans **Administration**.")
        else:
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("#### Cash In sous le seuil")
                if not seuil_ci:
                    st.info("Seuil non défini.")
                elif not sous_ci:
                    st.success(f"Tous les POS sont au-dessus du seuil ({seuil_ci:,.0f} FCFA).")
                else:
                    st.error(f"**{len(sous_ci)} POS sous le seuil**")
                    df_sous_ci = pd.DataFrame([
                        {"POS ID": r["acceptorid"], "Nom": r.get("agent_name",""),
                         "Cash In (FCFA)": r["cash_in"],
                         "Écart (FCFA)": r["cash_in"] - seuil_ci}
                        for r in sous_ci
                    ])
                    df_sous_ci["Cash In (FCFA)"] = df_sous_ci["Cash In (FCFA)"].map("{:,.0f}".format)
                    df_sous_ci["Écart (FCFA)"]   = df_sous_ci["Écart (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_sous_ci, hide_index=True, use_container_width=True)

            with col_b:
                st.markdown("#### Cash Out sous le seuil")
                if not seuil_co:
                    st.info("Seuil non défini.")
                elif not sous_co:
                    st.success(f"Tous les POS sont au-dessus du seuil ({seuil_co:,.0f} FCFA).")
                else:
                    st.error(f"**{len(sous_co)} POS sous le seuil**")
                    df_sous_co = pd.DataFrame([
                        {"POS ID": r["acceptorid"], "Nom": r.get("agent_name",""),
                         "Cash Out (FCFA)": r["cash_out"],
                         "Écart (FCFA)": r["cash_out"] - seuil_co}
                        for r in sous_co
                    ])
                    df_sous_co["Cash Out (FCFA)"] = df_sous_co["Cash Out (FCFA)"].map("{:,.0f}".format)
                    df_sous_co["Écart (FCFA)"]    = df_sous_co["Écart (FCFA)"].map("{:,.0f}".format)
                    st.dataframe(df_sous_co, hide_index=True, use_container_width=True)

            # Export
            sheets_al: dict = {}
            if seuil_ci and sous_ci:
                sheets_al["Alerte Cash In"] = pd.DataFrame([
                    {"POS ID": r["acceptorid"], "Nom": r.get("agent_name",""),
                     "Cash In (FCFA)": r["cash_in"], "Seuil": seuil_ci,
                     "Écart": r["cash_in"] - seuil_ci}
                    for r in sous_ci
                ])
            if seuil_co and sous_co:
                sheets_al["Alerte Cash Out"] = pd.DataFrame([
                    {"POS ID": r["acceptorid"], "Nom": r.get("agent_name",""),
                     "Cash Out (FCFA)": r["cash_out"], "Seuil": seuil_co,
                     "Écart": r["cash_out"] - seuil_co}
                    for r in sous_co
                ])
            if sheets_al:
                st.divider()
                xlsx_al = export_df_to_excel(
                    sheets_al,
                    titre=f"Alertes Cash Flow — {label_mois_al}",
                    source_label="ALBARKA — SAE",
                )
                st.download_button(
                    "Exporter alertes (Excel)",
                    data=xlsx_al,
                    file_name=f"alertes_cashflow_{mois_al}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_alertes_cf",
                )


# ===========================================================================
# ONGLET 4 — COMPARAISON MoM MULTI-FICHIERS
# ===========================================================================
with tab_mom:
    st.subheader("Comparaison Month-over-Month — multi-fichiers SAE")
    st.write(
        "Dépose 2 ou 3 fichiers SAE de mois différents pour obtenir : "
        "Top 20 / Flop 10 de chaque mois, POS constants dans le Top/Flop, "
        "et Top 10 cumulé sur l'ensemble des mois."
    )

    fichiers_mom = st.file_uploader(
        "Fichiers SAE (2 ou 3 mois)",
        type=["xlsx", "csv"],
        accept_multiple_files=True,
        key="up_mom",
    )

    # Permettre la saisie manuelle du mois si la détection auto échoue
    mois_overrides: dict[str, str] = {}
    if fichiers_mom:
        st.markdown("**Vérification des mois détectés**")
        for f in fichiers_mom:
            detected = _detect_mois_from_filename(f.name)
            col_fn, col_mois = st.columns([2, 1])
            col_fn.markdown(f"*{f.name}*")
            override = col_mois.text_input(
                "Mois (AAAA-MM)",
                value=detected or "",
                key=f"mois_override_{f.name}",
                label_visibility="collapsed",
            )
            mois_overrides[f.name] = override.strip() or detected or ""

    if not fichiers_mom or len(fichiers_mom) < 2:
        st.info("Dépose au moins 2 fichiers SAE.")
    elif st.button("Analyser", key="btn_mom"):
        try:
            fichiers_input = []
            for f in fichiers_mom:
                f.seek(0)
                raw = f.read()
                fichiers_input.append({
                    "source":      raw,
                    "nom_fichier": f.name,
                    "mois":        mois_overrides.get(f.name) or None,
                })

            with st.spinner("Calcul en cours…"):
                resultats = compute_mom_multi(fichiers_input)

            mois_list  = resultats["mois_list"]
            labels_mois = {
                m: pd.Timestamp(m + "-01").strftime("%B %Y").capitalize()
                for m in mois_list
            }

            st.divider()
            st.markdown(f"**Mois analysés : {' · '.join(labels_mois.values())}**")

            # ── Top 20 et Flop 10 par mois ──────────────────────────────────
            st.markdown("#### Top 20 Cash In par mois")
            cols_top = st.columns(len(mois_list))
            for i, mois in enumerate(mois_list):
                with cols_top[i]:
                    st.markdown(f"**{labels_mois[mois]}**")
                    recs = resultats["top20"].get(mois, [])
                    if recs:
                        df_t = pd.DataFrame([
                            {"#": j+1, "Nom": r.get("agent_name","") or r["acceptorid"],
                             "Cash In (FCFA)": f"{r['cash_in']:,.0f}"}
                            for j, r in enumerate(recs)
                        ])
                        st.dataframe(df_t, hide_index=True, use_container_width=True)

            st.divider()
            st.markdown("#### Flop 10 Cash In par mois")
            cols_flop = st.columns(len(mois_list))
            for i, mois in enumerate(mois_list):
                with cols_flop[i]:
                    st.markdown(f"**{labels_mois[mois]}**")
                    recs = resultats["flop10"].get(mois, [])
                    if recs:
                        df_f = pd.DataFrame([
                            {"#": j+1, "Nom": r.get("agent_name","") or r["acceptorid"],
                             "Cash In (FCFA)": f"{r['cash_in']:,.0f}"}
                            for j, r in enumerate(recs)
                        ])
                        st.dataframe(df_f, hide_index=True, use_container_width=True)

            # ── Top 10 cumulé ────────────────────────────────────────────────
            st.divider()
            st.markdown("#### Top 10 cumulé (tous mois confondus)")
            if resultats["top10_cumule"]:
                df_cum = pd.DataFrame([
                    {"#": j+1,
                     "POS ID": r["acceptorid"],
                     "Nom": r.get("agent_name",""),
                     "Cash In cumulé (FCFA)": f"{r['cash_in_total']:,.0f}",
                     "Cash Out cumulé (FCFA)": f"{r['cash_out_total']:,.0f}"}
                    for j, r in enumerate(resultats["top10_cumule"])
                ])
                st.dataframe(df_cum, hide_index=True, use_container_width=True)

            # ── POS constants ────────────────────────────────────────────────
            st.divider()
            col_ct, col_cf = st.columns(2)
            with col_ct:
                st.markdown(f"#### POS constants dans le Top20 ({len(resultats['constants_top'])})")
                if resultats["constants_top"]:
                    st.dataframe(
                        pd.DataFrame(resultats["constants_top"])
                        .rename(columns={"acceptorid":"POS ID","agent_msisdn":"MSISDN","agent_name":"Nom"}),
                        hide_index=True, use_container_width=True,
                    )
                else:
                    st.info("Aucun POS présent dans le Top20 de tous les mois.")

            with col_cf:
                st.markdown(f"#### POS constants dans le Flop10 ({len(resultats['constants_flop'])})")
                if resultats["constants_flop"]:
                    st.dataframe(
                        pd.DataFrame(resultats["constants_flop"])
                        .rename(columns={"acceptorid":"POS ID","agent_msisdn":"MSISDN","agent_name":"Nom"}),
                        hide_index=True, use_container_width=True,
                    )
                else:
                    st.info("Aucun POS présent dans le Flop10 de tous les mois.")

            # ── Export Excel complet ─────────────────────────────────────────
            st.divider()
            sheets_mom: dict = {}
            for mois in mois_list:
                lbl = labels_mois[mois]
                if resultats["top20"].get(mois):
                    sheets_mom[f"Top20 {lbl}"] = pd.DataFrame([
                        {"#": j+1, "POS ID": r["acceptorid"],
                         "Nom": r.get("agent_name",""),
                         "Cash In (FCFA)": r["cash_in"]}
                        for j, r in enumerate(resultats["top20"][mois])
                    ])
                if resultats["flop10"].get(mois):
                    sheets_mom[f"Flop10 {lbl}"] = pd.DataFrame([
                        {"#": j+1, "POS ID": r["acceptorid"],
                         "Nom": r.get("agent_name",""),
                         "Cash In (FCFA)": r["cash_in"]}
                        for j, r in enumerate(resultats["flop10"][mois])
                    ])
            if resultats["top10_cumule"]:
                sheets_mom["Top10 cumulé"] = pd.DataFrame([
                    {"#": j+1, "POS ID": r["acceptorid"], "Nom": r.get("agent_name",""),
                     "CI cumulé (FCFA)": r["cash_in_total"],
                     "CO cumulé (FCFA)": r["cash_out_total"]}
                    for j, r in enumerate(resultats["top10_cumule"])
                ])
            if resultats["constants_top"]:
                sheets_mom["Constantes Top"] = pd.DataFrame(resultats["constants_top"])
            if resultats["constants_flop"]:
                sheets_mom["Constantes Flop"] = pd.DataFrame(resultats["constants_flop"])

            if sheets_mom:
                mois_range = "_".join(mois_list)
                xlsx_mom = export_df_to_excel(
                    sheets_mom,
                    titre=f"Cash Flow MoM — {' vs '.join(labels_mois.values())}",
                    source_label="ALBARKA — SAE",
                )
                st.download_button(
                    "Exporter MoM (Excel)",
                    data=xlsx_mom,
                    file_name=f"cashflow_mom_{mois_range}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_mom_cf",
                )

        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")
