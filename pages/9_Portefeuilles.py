"""
pages/9_Portefeuilles.py — v2
================================
Gestion des portefeuilles commerciaux.

Droits :
  Super Admin : Import + Consultation + Couverture
  Admin       : Consultation + Couverture uniquement (pas d'import ni suppression)

Nouveautés v2 :
  - Rapprochement couverture par MSISDN en priorité (From/To msisdn disponibles
    depuis les clients_servis stockés en base) — fallback par nom si MSISDN absent
  - L'onglet Import est masqué pour l'Admin
  - Le bouton Supprimer est masqué pour l'Admin
  - Couverture depuis la base (clients_servis) — pas besoin de re-déposer des CSV
"""

import streamlit as st
import pandas as pd
from datetime import date

from core import db
from core.auth import require_role, show_user_badge, get_role
from core.ui import apply_theme, show_page_header
from core.export import export_df_to_excel

apply_theme()
require_role("super_admin", "admin")
show_user_badge()

role = get_role()
is_super = role == "super_admin"

show_page_header("Portefeuilles", "Gestion des portefeuilles clients par commercial")
st.divider()

commerciaux = db.list_commerciaux()

# Onglets selon le rôle
if is_super:
    tab_import, tab_consultation, tab_couverture = st.tabs([
        "Import", "Consultation", "Couverture"
    ])
else:
    tab_import = None
    tab_consultation, tab_couverture = st.tabs(["Consultation", "Couverture"])


# ---------------------------------------------------------------------------
# Helper normalisation MSISDN
# ---------------------------------------------------------------------------
def _normalise_msisdn(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip().replace(" ", "").replace("-", "").replace(".", "")
    if s.lower() in ("", "nan", "none"):
        return ""
    if s.endswith("0") and len(s) > 8:
        raw = str(val).strip()
        if raw.endswith(".0"):
            s = raw[:-2].replace(" ", "").replace("-", "")
    for prefixe in ("+237", "00237"):
        if s.startswith(prefixe):
            s = s[len(prefixe):]
    return s


# ===========================================================================
# ONGLET 1 — IMPORT (Super Admin uniquement)
# ===========================================================================
if tab_import is not None:
    with tab_import:
        st.subheader("Importer un portefeuille clients")
        st.write(
            "Le fichier Excel doit contenir au minimum une colonne **nom**. "
            "Les colonnes **telephone** (ou msisdn, numéro_ccial) et **localite** "
            "sont recommandées pour le calcul de couverture."
        )

        if not commerciaux:
            st.warning("Aucun commercial trouvé. Crée d'abord les comptes dans Administration.")
        else:
            col1, col2 = st.columns(2)
            commercial_import = col1.selectbox(
                "Commercial", commerciaux,
                format_func=lambda c: c["dsm_name"],
                key="sel_com_import_pf",
            )
            nom_pf = col2.text_input(
                "Nom du portefeuille",
                key="nom_pf",
            )

            fichier_xl = st.file_uploader(
                "Fichier Excel (.xlsx)", type=["xlsx"], key="up_portefeuille"
            )

            df_preview = None
            col_nom = col_tel = col_loc = None

            if fichier_xl is not None:
                try:
                    fichier_xl.seek(0)
                    df_preview = pd.read_excel(fichier_xl)
                    df_preview.columns = df_preview.columns.str.strip().str.lower()
                    st.caption(
                        f"Aperçu — {len(df_preview)} lignes, "
                        f"colonnes : {list(df_preview.columns)}"
                    )
                    st.dataframe(df_preview.head(5), hide_index=True, use_container_width=True)

                    col_nom = next(
                        (c for c in df_preview.columns if "nom" in c),
                        df_preview.columns[0] if len(df_preview.columns) else None
                    )
                    col_tel = next(
                        (c for c in df_preview.columns
                         if any(k in c for k in ("tel","phone","msisdn","mobile","ccial","numero"))),
                        None,
                    )
                    col_loc = next(
                        (c for c in df_preview.columns
                         if any(k in c for k in ("local","ville","zone","quartier","site","profile","pos_profile"))),
                        None,
                    )
                    st.caption(
                        f"Colonnes détectées → nom : **{col_nom}**"
                        + (f", téléphone : **{col_tel}**" if col_tel else "")
                        + (f", localité : **{col_loc}**" if col_loc else "")
                    )
                except Exception as e:
                    st.error(f"Impossible de lire le fichier : {e}")

            if st.button("Créer le portefeuille", key="btn_create_pf"):
                if not nom_pf.strip():
                    st.error("Le nom du portefeuille est obligatoire.")
                elif df_preview is None or col_nom is None:
                    st.error("Importe un fichier valide avec une colonne nom.")
                else:
                    clients_liste = []
                    for _, row in df_preview.iterrows():
                        nom_val = str(row[col_nom]).strip()
                        if not nom_val or nom_val.lower() in ("nan","none",""):
                            continue
                        tel_val = (
                            _normalise_msisdn(row.get(col_tel))
                            if col_tel and pd.notna(row.get(col_tel)) else None
                        )
                        loc_val = (
                            str(row[col_loc]).strip()
                            if col_loc and pd.notna(row.get(col_loc)) else None
                        )
                        clients_liste.append({
                            "nom": nom_val,
                            "telephone": tel_val or None,
                            "localite": loc_val,
                        })

                    if not clients_liste:
                        st.error("Aucun client valide dans le fichier.")
                    else:
                        try:
                            pf_id = db.create_portefeuille(
                                commercial_id=commercial_import["id"],
                                nom=nom_pf.strip(),
                                date_import=date.today().isoformat(),
                                clients=clients_liste,
                            )
                            st.success(
                                f"Portefeuille **{nom_pf}** créé — "
                                f"{len(clients_liste)} clients (id={pf_id})."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")


# ===========================================================================
# ONGLET 2 — CONSULTATION
# ===========================================================================
with tab_consultation:
    st.subheader("Portefeuilles existants")

    filtre_com = st.selectbox(
        "Filtrer par commercial",
        [None] + commerciaux,
        format_func=lambda c: "Tous" if c is None else c["dsm_name"],
        key="filtre_com_consult",
    )

    portefeuilles = db.list_portefeuilles(
        commercial_id=filtre_com["id"] if filtre_com else None
    )

    if not portefeuilles:
        st.info("Aucun portefeuille trouvé.")
    else:
        for pf in portefeuilles:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                c1.markdown(f"**{pf['nom']}**")
                c2.write(f"{pf['dsm_name']} · importé le {pf['date_import']}")
                c3.write(f"{pf['nb_clients']} clients")

                # Suppression : Super Admin uniquement
                if is_super:
                    if c4.button("Supprimer", key=f"del_pf_{pf['id']}"):
                        st.session_state[f"confirm_del_{pf['id']}"] = True

                    if st.session_state.get(f"confirm_del_{pf['id']}"):
                        st.warning(
                            f"Supprimer **{pf['nom']}** "
                            f"et ses {pf['nb_clients']} clients ?"
                        )
                        col_y, col_n = st.columns(2)
                        if col_y.button("Confirmer", key=f"conf_y_{pf['id']}", type="primary"):
                            db.delete_portefeuille(pf["id"])
                            st.session_state.pop(f"confirm_del_{pf['id']}", None)
                            st.success(f"Portefeuille **{pf['nom']}** supprimé.")
                            st.rerun()
                        if col_n.button("Annuler", key=f"conf_n_{pf['id']}"):
                            st.session_state.pop(f"confirm_del_{pf['id']}", None)
                            st.rerun()

                with st.expander(f"Voir les {pf['nb_clients']} clients"):
                    clients = db.list_clients(pf["id"])
                    if clients:
                        df_c = pd.DataFrame(clients)[["nom","telephone","localite"]]
                        df_c.columns = ["Nom","Téléphone","Localité"]
                        st.dataframe(df_c, hide_index=True, use_container_width=True)
                    else:
                        st.info("Aucun client enregistré.")


# ===========================================================================
# ONGLET 3 — COUVERTURE
# ===========================================================================
with tab_couverture:
    st.subheader("Calcul de couverture du portefeuille")
    st.write(
        "Sélectionne un portefeuille et une période. L'application rapproche "
        "les clients du portefeuille avec l'historique des clients servis "
        "(alimenté automatiquement lors des imports Transactions). "
        "Le rapprochement se fait **par MSISDN** (numéro de téléphone normalisé), "
        "avec fallback par nom si le MSISDN est absent."
    )

    portefeuilles_tous = db.list_portefeuilles()

    if not portefeuilles_tous:
        st.info("Aucun portefeuille disponible.")
    else:
        pf_choisi = st.selectbox(
            "Portefeuille",
            portefeuilles_tous,
            format_func=lambda p: f"{p['dsm_name']} — {p['nom']} ({p['nb_clients']} clients)",
            key="sel_pf_couv",
        )

        col_d1, col_d2 = st.columns(2)
        date_deb = col_d1.date_input("Période du", value=None, key="deb_couv")
        date_fin = col_d2.date_input("au",         value=None, key="fin_couv")

        if st.button("Calculer la couverture", key="btn_couv"):
            clients_pf = db.list_clients(pf_choisi["id"])
            if not clients_pf:
                st.error("Ce portefeuille ne contient aucun client.")
            else:
                df_clients = pd.DataFrame(clients_pf)
                total = len(df_clients)

                # Récupérer les MSISDN servis depuis la base
                com_id = pf_choisi["commercial_id"]
                msisdns_servis = db.get_msisdns_servis(
                    com_id,
                    date_debut=str(date_deb) if date_deb else None,
                    date_fin=str(date_fin)   if date_fin   else None,
                )

                # Noms des contreparties servis (pour le fallback nom)
                servis_detail = db.list_clients_servis(
                    com_id,
                    date_debut=str(date_deb) if date_deb else None,
                    date_fin=str(date_fin)   if date_fin   else None,
                )
                noms_servis = {
                    str(s.get("nom_contrepartie","")).strip().upper()
                    for s in servis_detail
                    if s.get("nom_contrepartie")
                }

                lignes = []
                couverts = 0

                for _, client in df_clients.iterrows():
                    tel_norm = _normalise_msisdn(client.get("telephone",""))
                    nom_client = str(client.get("nom","")).strip().upper()

                    # Priorité 1 : rapprochement MSISDN
                    couvert = bool(tel_norm and tel_norm in msisdns_servis)

                    # Priorité 2 : fallback nom si MSISDN absent ou non trouvé
                    if not couvert and nom_client and len(nom_client) >= 3:
                        couvert = nom_client in noms_servis or any(
                            nom_client in n for n in noms_servis
                        )

                    if couvert:
                        couverts += 1

                    lignes.append({
                        "Nom":       client.get("nom",""),
                        "Téléphone": client.get("telephone",""),
                        "Localité":  client.get("localite",""),
                        "Statut":    "Couvert" if couvert else "Non couvert",
                    })

                taux = couverts / total if total else 0

                # Métriques
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("Clients dans le portefeuille", total)
                m2.metric("Clients couverts", couverts)
                m3.metric("Taux de couverture", f"{taux:.1%}")

                # Tableau
                st.divider()
                df_detail = pd.DataFrame(lignes)
                filtre = st.selectbox(
                    "Afficher",
                    ["Tous", "Couverts", "Non couverts"],
                    key="filtre_couv",
                )
                if filtre == "Couverts":
                    df_detail = df_detail[df_detail["Statut"] == "Couvert"]
                elif filtre == "Non couverts":
                    df_detail = df_detail[df_detail["Statut"] == "Non couvert"]

                st.dataframe(df_detail, hide_index=True, use_container_width=True)

                # Export
                df_synthese = pd.DataFrame([
                    {"Indicateur": "Clients total",       "Valeur": total},
                    {"Indicateur": "Clients couverts",    "Valeur": couverts},
                    {"Indicateur": "Taux de couverture",  "Valeur": f"{taux:.1%}"},
                    {"Indicateur": "Commercial",          "Valeur": pf_choisi["dsm_name"]},
                    {"Indicateur": "Portefeuille",        "Valeur": pf_choisi["nom"]},
                ])
                xlsx_couv = export_df_to_excel(
                    {
                        "Résumé couverture": df_synthese,
                        "Détail clients":    df_detail,
                    },
                    titre=f"Couverture — {pf_choisi['dsm_name']} — {pf_choisi['nom']}",
                    source_label="ALBARKA — Portefeuilles",
                )
                st.download_button(
                    "Exporter (Excel)",
                    data=xlsx_couv,
                    file_name=f"couverture_{pf_choisi['dsm_name']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_couv",
                )

                st.caption(
                    f"Source : historique clients servis en base "
                    f"({len(msisdns_servis)} MSISDN distincts sur la période)."
                )
