"""
pages/1_Transactions.py — v2
==============================
Volet Transactions — Super Admin uniquement pour le dépôt.
Admin et Commercial consultent et exportent (pas de dépôt).

Flux Super Admin :
  1. Déposer un ou plusieurs fichiers CSV (un par commercial)
  2. Pour chaque fichier :
       a. Nettoyage (colonnes From/To msisdn conservées)
       b. Génération du classeur Excel (3 onglets)
       c. Calcul des points touchés (comptage brut de lignes)
       d. Stockage des clients servis en base (table clients_servis)
       e. Si le commercial a un alias : extraction appro/destockage
          depuis les TCD générés → stockage dans table appro
       f. Sauvegarde dans l'historique des imports

Flux Admin / Commercial :
  - Consultation des imports existants + téléchargement
  - Tableau des points touchés par commercial et par jour
"""

import io
import zipfile
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

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

show_page_header("Transactions", "Nettoyage, tableaux croisés, points touchés, clients servis")

st.divider()

# ─── Routage selon le rôle ────────────────────────────────────────────────────
if role == "super_admin":
    _tabs = st.tabs(["Import", "Résultats & Points touchés", "Clients servis"])
    tab_import, tab_resultats, tab_clients = _tabs
elif role == "admin":
    _tabs = st.tabs(["Résultats & Points touchés", "Clients servis"])
    tab_import     = None
    tab_resultats  = _tabs[0]
    tab_clients    = _tabs[1]
else:  # commercial
    com_info = db.get_commercial_by_user_id(user["id"])
    _tabs = st.tabs(["Mes points touchés", "Mes clients servis"])
    tab_import     = None
    tab_resultats  = _tabs[0]
    tab_clients    = _tabs[1]


# ===========================================================================
# ONGLET IMPORT (Super Admin uniquement)
# ===========================================================================
if tab_import is not None:
    with tab_import:
        st.subheader("Importer des fichiers CSV de transactions")
        st.write(
            "Dépose un ou plusieurs fichiers CSV Mobile Money (un par commercial). "
            "Le nettoyage, les TCD, les points touchés et les clients servis sont "
            "calculés automatiquement. "
            "Si le commercial possède un alias, l'appro/destockage est extrait des TCD."
        )

        # Récupérer les aliases disponibles pour l'affichage
        alias_map = db.get_alias_map()  # {alias_upper: {commercial_id, dsm_name, alias}}
        commerciaux = db.list_commerciaux()
        com_by_dsm  = {c["dsm_name"].upper(): c for c in commerciaux}

        # Upload
        if "tx_chemins" not in st.session_state:
            st.session_state["tx_chemins"] = []

        fichiers = st.file_uploader(
            "Fichiers CSV", type=["csv"], accept_multiple_files=True, key="up_tx_v2"
        )

        if st.button("Traiter les fichiers", key="btn_tx_v2") and fichiers:
            st.session_state["tx_chemins"] = []
            progress = st.progress(0, text="Traitement en cours…")

            for idx, f in enumerate(fichiers):
                progress.progress(idx / len(fichiers), text=f"Traitement de {f.name}…")
                cle = Path(f.name).stem

                try:
                    f.seek(0)
                    df = clean_transactions(f)
                    if df.empty:
                        st.warning(f"{f.name} : aucune ligne exploitable.")
                        continue

                    # ── Génération classeur ─────────────────────────────────
                    wb = build_transactions_workbook(df, source_label=cle)
                    chemin = db.build_output_path("transactions", cle)
                    wb.save(chemin)

                    # ── Points touchés ──────────────────────────────────────
                    pts = compute_points_touches(df)

                    # ── Identification du commercial par nom de fichier ─────
                    # On cherche d'abord par dsm_name dans le stem du fichier
                    commercial_match = None
                    stem_upper = cle.upper()
                    for dsm, com in com_by_dsm.items():
                        if dsm in stem_upper:
                            commercial_match = com
                            break

                    # ── Clients servis + Appro (si commercial identifié) ────
                    appro_ok = False
                    if commercial_match:
                        com_id = commercial_match["id"]
                        alias  = commercial_match.get("alias_csv")

                        # Clients servis — utilise l'alias si disponible
                        if alias:
                            clients_list = extract_clients_servis(df, alias)
                        else:
                            clients_list = []

                        if clients_list:
                            db.save_clients_servis(
                                com_id,
                                contreparties=clients_list,
                                source_fichier=f.name,
                            )

                        # Appro / Destockage depuis les TCD (uniquement si alias disponible)
                        if alias:
                            try:
                                appro_rows = extract_appro_from_workbook(chemin, alias)
                                if appro_rows:
                                    conn_appro = db.get_connection()
                                    try:
                                        for row_a in appro_rows:
                                            conn_appro.execute("""
                                                INSERT INTO appro
                                                    (commercial_id, date_op, type_op, nb_ops, montant, source_fichier)
                                                VALUES (?, ?, ?, ?, ?, ?)
                                                ON CONFLICT(commercial_id, date_op, type_op) DO UPDATE SET
                                                    nb_ops         = excluded.nb_ops,
                                                    montant        = excluded.montant,
                                                    source_fichier = excluded.source_fichier,
                                                    created_at     = datetime('now')
                                            """, (com_id, row_a["date_op"], row_a["type_op"],
                                                  row_a["nb_ops"], row_a["montant"], f.name))
                                        conn_appro.commit()
                                        appro_ok = True
                                    finally:
                                        conn_appro.close()
                            except Exception as e_appro:
                                st.warning(f"{f.name} — appro non extrait : {e_appro}")

                    # ── Historique ──────────────────────────────────────────
                    date_donnees = str(df["Date"].max())
                    db.save_import("transactions", cle, date_donnees, chemin, nb_lignes=len(df))
                    st.session_state["tx_chemins"].append(str(chemin))

                    # ── Résumé ──────────────────────────────────────────────
                    com_nom = commercial_match["dsm_name"] if commercial_match else "—"
                    alias_nom = commercial_match.get("alias_csv", "—") if commercial_match else "—"
                    msg = (
                        f"**{f.name}** — {pts['total']:,} lignes · "
                        f"{pts['moyenne_par_jour']:.1f} points/jour · "
                        f"commercial : **{com_nom}** · alias : {alias_nom}"
                    )
                    if appro_ok:
                        msg += " · ✅ appro/destockage extrait"
                    st.success(msg)

                    # Bouton téléchargement individuel
                    with open(chemin, "rb") as fh:
                        st.download_button(
                            f"Télécharger {chemin.name}",
                            data=fh.read(),
                            file_name=chemin.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_tx_{cle}",
                        )

                except Exception as e:
                    st.error(f"{f.name} — erreur : {e}")

            progress.progress(1.0, text="Terminé.")

        # Bouton ZIP global
        chemins_ok = [p for p in st.session_state.get("tx_chemins", [])
                      if Path(p).exists()]
        if len(chemins_ok) >= 2:
            st.divider()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in chemins_ok:
                    zf.write(p, arcname=Path(p).name)
            buf.seek(0)
            st.download_button(
                f"Télécharger tous ({len(chemins_ok)}) en ZIP",
                data=buf,
                file_name="transactions_export.zip",
                mime="application/zip",
                key="dl_tx_zip",
            )

        # Note sur les commerciaux sans alias
        st.divider()
        sans_alias = [c for c in commerciaux if not c.get("alias_csv")]
        if sans_alias:
            noms = ", ".join(c["dsm_name"] for c in sans_alias)
            st.info(
                f"**Commerciaux sans alias** : {noms} — "
                "les clients servis et l'appro/destockage ne peuvent pas être calculés "
                "pour eux. Ajoute leurs aliases dans **Administration → Aliases**.",
                icon="ℹ️",
            )


# ===========================================================================
# ONGLET RÉSULTATS & POINTS TOUCHÉS
# ===========================================================================
with tab_resultats:
    st.subheader("Points touchés par commercial")
    st.caption(
        "Points touchés = nombre de lignes de transactions (comptage brut). "
        "Source : imports déjà traités."
    )

    # Filtre commercial pour le rôle commercial
    if is_commercial():
        if not com_info:
            st.error("Compte commercial non lié à un DSM. Contacte l'administrateur.")
            st.stop()
        commerciaux_filtre = [com_info]
    else:
        commerciaux_filtre = db.list_commerciaux()
        com_choisi_pts = st.selectbox(
            "Commercial (optionnel)",
            [None] + commerciaux_filtre,
            format_func=lambda c: "Tous" if c is None else c["dsm_name"],
            key="sel_com_pts",
        )
        if com_choisi_pts:
            commerciaux_filtre = [com_choisi_pts]

    # Récupérer les clients servis agrégés par commercial par jour
    rows_pts = []
    for com in commerciaux_filtre:
        servis = db.list_clients_servis(com["id"])
        if not servis:
            continue
        # Grouper par date
        par_date: dict[str, int] = {}
        for s in servis:
            d = s["premiere_date"] if s.get("premiere_date") else "—"
            par_date[d] = par_date.get(d, 0) + s["nb_total"]

        for d_op, nb in sorted(par_date.items()):
            rows_pts.append({
                "Commercial": com["dsm_name"],
                "Date":       d_op,
                "Points touchés": nb,
            })

    if not rows_pts:
        st.info("Aucune donnée disponible. Importe d'abord des fichiers dans l'onglet Import.")
    else:
        df_pts = pd.DataFrame(rows_pts)

        # Synthèse par commercial
        df_synthese = (
            df_pts.groupby("Commercial", as_index=False)
            .agg(
                Total_points=("Points touchés", "sum"),
                Nb_jours=("Date", "nunique"),
            )
        )
        df_synthese["Moyenne/jour"] = (
            df_synthese["Total_points"] / df_synthese["Nb_jours"]
        ).round(1)
        df_synthese.columns = ["Commercial", "Total points", "Jours actifs", "Moyenne/jour"]
        df_synthese = df_synthese.sort_values("Total points", ascending=False)

        col_s, col_d = st.columns([1, 2])
        with col_s:
            st.markdown("**Synthèse**")
            st.dataframe(df_synthese, hide_index=True, use_container_width=True)

        with col_d:
            st.markdown("**Détail journalier**")
            st.dataframe(
                df_pts.sort_values(["Commercial", "Date"]),
                hide_index=True, use_container_width=True,
            )

        # Export Excel
        st.divider()
        xlsx = export_df_to_excel(
            {"Synthèse": df_synthese, "Détail journalier": df_pts},
            titre="Points touchés — Transactions",
            source_label="ALBARKA — Transactions",
        )
        st.download_button(
            "Exporter (Excel)",
            data=xlsx,
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
        "Liste des contreparties (clients) touchées par chaque commercial, "
        "jour après jour. Sert au calcul de couverture des portefeuilles."
    )

    # Filtre commercial
    if is_commercial():
        com_sel_cs = com_info
    else:
        commerciaux_cs = db.list_commerciaux()
        if not commerciaux_cs:
            st.info("Aucun commercial en base.")
            st.stop()
        com_sel_cs = st.selectbox(
            "Commercial",
            commerciaux_cs,
            format_func=lambda c: c["dsm_name"],
            key="sel_com_cs",
        )

    if not com_sel_cs:
        st.info("Sélectionne un commercial.")
    else:
        # Filtres de période
        col_d1, col_d2 = st.columns(2)
        date_debut_cs = col_d1.date_input(
            "Du", value=None, key="date_debut_cs"
        )
        date_fin_cs = col_d2.date_input(
            "Au", value=None, key="date_fin_cs"
        )

        servis = db.list_clients_servis(
            com_sel_cs["id"],
            date_debut=str(date_debut_cs) if date_debut_cs else None,
            date_fin=str(date_fin_cs)   if date_fin_cs   else None,
        )

        if not servis:
            st.info(
                "Aucun client servis trouvé. "
                "Importe des fichiers de transactions (avec alias configuré) "
                "pour alimenter cet historique."
            )
        else:
            df_cs = pd.DataFrame(servis)
            df_cs = df_cs.rename(columns={
                "msisdn_contrepartie": "MSISDN",
                "nom_contrepartie":    "Nom",
                "nb_total":            "Nb transactions",
                "premiere_date":       "Première date",
                "derniere_date":       "Dernière date",
            })

            # Métriques
            c1, c2, c3 = st.columns(3)
            c1.metric("Clients distincts",    len(df_cs))
            c2.metric("Total transactions",   f"{df_cs['Nb transactions'].sum():,}")
            c3.metric("Commercial",           com_sel_cs["dsm_name"])

            st.divider()
            st.dataframe(df_cs, hide_index=True, use_container_width=True)

            # Export
            xlsx_cs = export_df_to_excel(
                {"Clients servis": df_cs},
                titre=f"Clients servis — {com_sel_cs['dsm_name']}",
                source_label="ALBARKA — Transactions",
            )
            st.download_button(
                "Exporter (Excel)",
                data=xlsx_cs,
                file_name=f"clients_servis_{com_sel_cs['dsm_name']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_cs",
            )
