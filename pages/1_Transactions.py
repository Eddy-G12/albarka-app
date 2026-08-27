"""
pages/1_Transactions.py — v2
==============================
Volet Transactions.

Droits :
  Super Admin : dépose les fichiers CSV, génère les classeurs, stocke les données
  Admin / Commercial : consultation et export uniquement

Flux Super Admin au dépôt :
  1. Nettoyage CSV → DataFrame (logique originale validée)
  2. Génération classeur Excel (3 onglets : Données, TCD - To Name, TCD - From Name)
  3. Calcul des points touchés (comptage brut de lignes par jour)
  4. Si alias configuré : extraction et stockage des clients servis
  5. Si alias configuré : extraction appro/destockage depuis les TCD
  6. Sauvegarde dans l'historique des imports
"""

import io
import zipfile
import streamlit as st
import pandas as pd
from pathlib import Path

from core import db
from core.auth import require_role, show_user_badge, get_role, get_current_user, is_commercial
from core.ui import apply_theme, show_page_header
from core.transactions import (
    clean_transactions,
    build_transactions_workbook,
    compute_points_touches,
    extract_clients_servis,
    extract_appro_from_workbook,
)
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin", "admin", "commercial")
show_user_badge()

role = get_role()
user = get_current_user()

show_page_header("Transactions", "Nettoyage, tableaux croisés, points touchés")
st.divider()

# ── Onglets selon le rôle ─────────────────────────────────────────────────────
if role == "super_admin":
    tab_import, tab_resultats, tab_clients = st.tabs([
        "Import", "Points touchés", "Clients servis"
    ])
elif role == "admin":
    tab_import    = None
    tab_resultats, tab_clients = st.tabs(["Points touchés", "Clients servis"])
else:  # commercial
    com_info = db.get_commercial_by_user_id(user["id"])
    tab_import    = None
    tab_resultats, tab_clients = st.tabs(["Mes points touchés", "Mes clients servis"])


# ===========================================================================
# ONGLET IMPORT — Super Admin uniquement
# ===========================================================================
if tab_import is not None:
    with tab_import:
        st.subheader("Importer des fichiers CSV de transactions")
        st.write(
            "Dépose un ou plusieurs fichiers CSV Mobile Money (un par commercial). "
            "Nettoyage, TCD Excel, points touchés, clients servis et appro/destockage "
            "sont calculés automatiquement."
        )

        # Pré-charger les données nécessaires
        commerciaux    = db.list_commerciaux()
        com_by_dsm     = {c["dsm_name"].upper(): c for c in commerciaux}

        # Note sur les commerciaux sans alias
        sans_alias = [c for c in commerciaux if not c.get("alias_csv")]
        if sans_alias:
            noms = ", ".join(c["dsm_name"] for c in sans_alias)
            st.info(
                f"**Sans alias** : {noms} — clients servis et appro non calculés. "
                "Configure leurs aliases dans **Administration → Aliases CSV**.",
                icon="ℹ️",
            )

        if "tx_chemins" not in st.session_state:
            st.session_state["tx_chemins"] = []

        fichiers = st.file_uploader(
            "Fichiers CSV", type=["csv"], accept_multiple_files=True, key="up_tx_v2"
        )

        if not st.button("Traiter les fichiers", key="btn_tx_v2") or not fichiers:
            # Bouton ZIP si des fichiers ont déjà été générés ce run
            chemins_ok = [p for p in st.session_state.get("tx_chemins", [])
                          if Path(p).exists()]
            if len(chemins_ok) >= 2:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for p in chemins_ok:
                        zf.write(p, arcname=Path(p).name)
                buf.seek(0)
                st.download_button(
                    f"Télécharger tous ({len(chemins_ok)}) en ZIP",
                    data=buf, file_name="transactions_export.zip",
                    mime="application/zip", key="dl_tx_zip",
                )
        else:
            # ─── Traitement ──────────────────────────────────────────────
            st.session_state["tx_chemins"] = []
            progress = st.progress(0, text="Traitement en cours…")

            for idx, f in enumerate(fichiers):
                progress.progress(idx / len(fichiers), text=f"Traitement de {f.name}…")
                cle = Path(f.name).stem

                try:
                    # ── 1. Lire les bytes UNE FOIS pour éviter les seek() partiels
                    f.seek(0)
                    raw_bytes = f.read()

                    # ── 2. Nettoyage
                    import io as _io
                    df = clean_transactions(_io.BytesIO(raw_bytes))
                    if df.empty:
                        st.warning(f"{f.name} : aucune ligne exploitable après nettoyage.")
                        continue

                    # ── 3. Classeur Excel
                    wb      = build_transactions_workbook(df, source_label=cle)
                    chemin  = db.build_output_path("transactions", cle)
                    wb.save(chemin)

                    # ── 4. Points touchés
                    pts = compute_points_touches(df)

                    # ── 5. Identification du commercial (par nom de fichier)
                    commercial_match = None
                    stem_upper = cle.upper()
                    for dsm, com in com_by_dsm.items():
                        if dsm in stem_upper:
                            commercial_match = com
                            break

                    # ── 6. Clients servis + Appro (si alias disponible)
                    appro_ok  = False
                    nb_clients_servis = 0

                    if commercial_match:
                        com_id = commercial_match["id"]
                        alias  = commercial_match.get("alias_csv")

                        if alias:
                            # Clients servis
                            try:
                                clients_list = extract_clients_servis(df, alias)
                                if clients_list:
                                    db.save_clients_servis(
                                        com_id,
                                        contreparties=clients_list,
                                        source_fichier=f.name,
                                    )
                                    nb_clients_servis = len(clients_list)
                            except Exception as e_cs:
                                st.warning(f"{f.name} — clients servis non stockés : {e_cs}")

                            # Appro / Destockage
                            try:
                                appro_rows = extract_appro_from_workbook(chemin, alias)
                                if appro_rows:
                                    conn_appro = db.get_connection()
                                    try:
                                        for row_a in appro_rows:
                                            conn_appro.execute("""
                                                INSERT INTO appro
                                                    (commercial_id, date_op, type_op,
                                                     nb_ops, montant, source_fichier)
                                                VALUES (?, ?, ?, ?, ?, ?)
                                                ON CONFLICT(commercial_id, date_op, type_op)
                                                DO UPDATE SET
                                                    nb_ops         = excluded.nb_ops,
                                                    montant        = excluded.montant,
                                                    source_fichier = excluded.source_fichier,
                                                    created_at     = datetime('now')
                                            """, (
                                                com_id,
                                                row_a["date_op"],
                                                row_a["type_op"],
                                                row_a.get("nb_ops", 0),
                                                row_a.get("montant", 0.0),
                                                f.name,
                                            ))
                                        conn_appro.commit()
                                        appro_ok = True
                                    finally:
                                        conn_appro.close()
                            except Exception as e_appro:
                                st.warning(f"{f.name} — appro non extrait : {e_appro}")

                    # ── 7. Historique
                    date_donnees = str(df["Date"].max())
                    db.save_import(
                        "transactions", cle, date_donnees,
                        chemin, nb_lignes=len(df)
                    )
                    st.session_state["tx_chemins"].append(str(chemin))

                    # ── 8. Résumé
                    com_nom   = commercial_match["dsm_name"] if commercial_match else "—"
                    alias_nom = commercial_match.get("alias_csv", "—") if commercial_match else "—"
                    msg = (
                        f"**{f.name}** — {pts['total']:,} lignes · "
                        f"{pts['moyenne_par_jour']:.1f} pts/jour · "
                        f"commercial : **{com_nom}** · alias : {alias_nom}"
                    )
                    if nb_clients_servis:
                        msg += f" · {nb_clients_servis} clients servis stockés"
                    if appro_ok:
                        msg += " · ✅ appro/destockage extrait"
                    st.success(msg)

                    # Bouton téléchargement individuel
                    with open(chemin, "rb") as fh:
                        st.download_button(
                            f"Télécharger {chemin.name}",
                            data=fh.read(), file_name=chemin.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_tx_{cle}",
                        )

                except Exception as e:
                    import traceback
                    st.error(f"**{f.name}** — erreur : {e}")
                    st.code(traceback.format_exc(), language="python")

            progress.progress(1.0, text="Terminé.")

            # Bouton ZIP
            chemins_ok = [p for p in st.session_state.get("tx_chemins", [])
                          if Path(p).exists()]
            if len(chemins_ok) >= 2:
                st.divider()
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for p in chemins_ok:
                        zf.write(p, arcname=Path(p).name)
                buf.seek(0)
                st.download_button(
                    f"Télécharger tous ({len(chemins_ok)}) en ZIP",
                    data=buf, file_name="transactions_export.zip",
                    mime="application/zip", key="dl_tx_zip_after",
                )


# ===========================================================================
# ONGLET POINTS TOUCHÉS
# ===========================================================================
with tab_resultats:
    st.subheader("Points touchés par commercial")
    st.caption("Points touchés = nb de transactions (comptage brut, par jour).")

    if is_commercial():
        if not com_info:
            st.error("Compte non lié à un profil commercial.")
            st.stop()
        commerciaux_filtre = [com_info]
    else:
        commerciaux_filtre = db.list_commerciaux()
        com_choisi_pts = st.selectbox(
            "Commercial",
            [None] + commerciaux_filtre,
            format_func=lambda c: "Tous" if c is None else c["dsm_name"],
            key="sel_com_pts",
        )
        if com_choisi_pts:
            commerciaux_filtre = [com_choisi_pts]

    rows_pts = []
    for com in commerciaux_filtre:
        servis = db.list_clients_servis(com["id"])
        if not servis:
            continue
        par_date: dict[str, int] = {}
        for s in servis:
            d = s.get("premiere_date") or "—"
            par_date[d] = par_date.get(d, 0) + s["nb_total"]
        for d_op, nb in sorted(par_date.items()):
            rows_pts.append({
                "Commercial":     com["dsm_name"],
                "Date":           d_op,
                "Points touchés": nb,
            })

    if not rows_pts:
        st.info(
            "Aucune donnée disponible. Importe des fichiers dans l'onglet Import "
            "(requiert un alias configuré)."
        )
    else:
        df_pts = pd.DataFrame(rows_pts)
        df_synthese = (
            df_pts.groupby("Commercial", as_index=False)
            .agg(Total=("Points touchés","sum"), Jours=("Date","nunique"))
        )
        df_synthese["Moyenne/jour"] = (
            df_synthese["Total"] / df_synthese["Jours"]
        ).round(1)
        df_synthese = df_synthese.sort_values("Total", ascending=False)

        col_s, col_d = st.columns([1, 2])
        with col_s:
            st.markdown("**Synthèse**")
            st.dataframe(df_synthese, hide_index=True, use_container_width=True)
        with col_d:
            st.markdown("**Détail journalier**")
            st.dataframe(
                df_pts.sort_values(["Commercial","Date"]),
                hide_index=True, use_container_width=True,
            )

        st.divider()
        xlsx = export_df_to_excel(
            {"Synthèse": df_synthese, "Détail": df_pts},
            titre="Points touchés — Transactions",
            source_label="ALBARKA — Transactions",
        )
        st.download_button(
            "Exporter (Excel)", data=xlsx,
            file_name="points_touches.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_pts",
        )


# ===========================================================================
# ONGLET CLIENTS SERVIS
# ===========================================================================
with tab_clients:
    st.subheader("Clients servis (historique contreparties)")
    st.caption(
        "Contreparties touchées par chaque commercial, jour après jour. "
        "Sert au calcul de couverture des portefeuilles."
    )

    if is_commercial():
        com_sel_cs = com_info
    else:
        commerciaux_cs = db.list_commerciaux()
        if not commerciaux_cs:
            st.info("Aucun commercial en base.")
            st.stop()
        com_sel_cs = st.selectbox(
            "Commercial", commerciaux_cs,
            format_func=lambda c: c["dsm_name"],
            key="sel_com_cs",
        )

    if com_sel_cs:
        col_d1, col_d2 = st.columns(2)
        date_debut_cs = col_d1.date_input("Du", value=None, key="date_deb_cs")
        date_fin_cs   = col_d2.date_input("Au", value=None, key="date_fin_cs")

        servis = db.list_clients_servis(
            com_sel_cs["id"],
            date_debut=str(date_debut_cs) if date_debut_cs else None,
            date_fin=str(date_fin_cs)     if date_fin_cs   else None,
        )

        if not servis:
            st.info(
                "Aucun client servis trouvé. "
                "Importe des fichiers avec alias configuré pour alimenter cet historique."
            )
        else:
            df_cs = pd.DataFrame(servis).rename(columns={
                "msisdn_contrepartie": "MSISDN",
                "nom_contrepartie":    "Nom",
                "nb_total":            "Nb transactions",
                "premiere_date":       "Première date",
                "derniere_date":       "Dernière date",
            })

            c1, c2 = st.columns(2)
            c1.metric("Clients distincts",  len(df_cs))
            c2.metric("Total transactions", f"{df_cs['Nb transactions'].sum():,}")

            st.divider()
            st.dataframe(df_cs, hide_index=True, use_container_width=True)

            xlsx_cs = export_df_to_excel(
                {"Clients servis": df_cs},
                titre=f"Clients servis — {com_sel_cs['dsm_name']}",
                source_label="ALBARKA — Transactions",
            )
            st.download_button(
                "Exporter (Excel)", data=xlsx_cs,
                file_name=f"clients_servis_{com_sel_cs['dsm_name']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_cs",
            )
