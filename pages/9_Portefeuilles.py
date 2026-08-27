"""
pages/9_Portefeuilles.py — v3
================================
Gestion des portefeuilles clients par commercial.

Droits :
  Super Admin : Import + Consultation + Suppression + Couverture
  Admin       : Consultation + Couverture (pas d'import ni suppression)

Format attendu pour les fichiers portefeuille ALBARKA :
  - Plusieurs lignes vides/titre en début
  - Ligne d'en-tête avec : Nom du client | numéro_ccial | nom_puce cciale | pos_profile
  - Données à partir de la ligne suivante
  - La colonne clé est numéro_ccial (MSISDN du client)

Point 4 : import adapté au format réel des fichiers ALBARKA.
Point 5 : couverture calculée depuis un CSV brut déposé (MSISDN From/To).
"""

import re
import io
import streamlit as st
import pandas as pd
from datetime import date, datetime

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

if is_super:
    tab_import, tab_consultation, tab_couverture = st.tabs([
        "Import", "Consultation", "Couverture"
    ])
else:
    tab_import = None
    tab_consultation, tab_couverture = st.tabs(["Consultation", "Couverture"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_msisdn(val) -> str:
    """Normalise un MSISDN : garde uniquement les chiffres, supprime préfixe +237/00237."""
    if val is None:
        return ""
    s = re.sub(r"[^0-9]", "", str(val))
    if not s:
        return ""
    # Garder le format 237XXXXXXXXX (9 chiffres après 237)
    return s


def _parse_portefeuille_file(fichier) -> list[dict]:
    """
    Parse un fichier portefeuille au format ALBARKA.

    Le fichier a des lignes vides en haut, puis une ligne d'en-tête contenant
    'numéro_ccial' (MSISDN), 'pos_profile' et 'Nom du client'.
    Les MSISDN sont au format 237XXXXXXXXX.

    Retourne [{msisdn, nom, pos_profile}]
    """
    df_raw = pd.read_excel(fichier, header=None, dtype=str)

    # 1. Trouver la ligne d'en-tête (contient 'ccial' ou 'msisdn')
    header_row = None
    for i, row in df_raw.iterrows():
        vals = [
            str(v).strip().lower()
            for v in row
            if pd.notna(v) and str(v).strip() not in ("", "nan")
        ]
        if any("ccial" in v or "msisdn" in v for v in vals):
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            "Ligne d'en-tête non trouvée. Vérifiez que le fichier contient "
            "une colonne 'numéro_ccial' ou 'msisdn'."
        )

    headers = [
        str(v).strip().lower() if pd.notna(v) and str(v).strip() not in ("", "nan") else ""
        for v in df_raw.iloc[header_row]
    ]

    # 2. Trouver la colonne MSISDN dans les données réelles
    # (peut différer de l'en-tête si les colonnes sont décalées)
    col_msisdn_data = None
    for i in range(header_row + 1, min(header_row + 10, len(df_raw))):
        row = df_raw.iloc[i]
        for j, val in enumerate(row):
            v = re.sub(r"[^0-9]", "", str(val))
            if re.match(r"^237[0-9]{8,9}$", v):
                col_msisdn_data = j
                break
        if col_msisdn_data is not None:
            break

    if col_msisdn_data is None:
        raise ValueError(
            "Colonne MSISDN introuvable dans les données. "
            "Les numéros doivent être au format 237XXXXXXXXX."
        )

    # 3. Colonne nom (colonne d'en-tête 'nom du client', hors 'nom_puce')
    col_nom_h = next(
        (i for i, h in enumerate(headers) if "nom" in h and "puce" not in h and "pos" not in h),
        None,
    )

    # 4. Colonne profil POS (détectée dans les données : contient 'MTNC')
    col_profil_data = None
    for i in range(header_row + 1, min(header_row + 5, len(df_raw))):
        row = df_raw.iloc[i]
        for j, val in enumerate(row):
            if "MTNC" in str(val):
                col_profil_data = j
                break
        if col_profil_data is not None:
            break

    # Fallback : chercher dans les en-têtes
    if col_profil_data is None:
        col_profil_data = next(
            (i for i, h in enumerate(headers) if "profil" in h or "profile" in h or "puce" in h),
            None,
        )

    # 5. Parcourir les lignes de données
    clients = []
    for i in range(header_row + 1, len(df_raw)):
        row = df_raw.iloc[i]

        msisdn_raw = (
            str(row.iloc[col_msisdn_data]).strip()
            if col_msisdn_data < len(row) else ""
        )
        nom = (
            str(row.iloc[col_nom_h]).strip()
            if col_nom_h is not None and col_nom_h < len(row) else ""
        )
        profil = (
            str(row.iloc[col_profil_data]).strip()
            if col_profil_data is not None and col_profil_data < len(row) else ""
        )

        # Nettoyer les nan/None
        for bad in ("nan", "None", "NaN"):
            if msisdn_raw == bad:
                msisdn_raw = ""
            if nom == bad:
                nom = ""
            if profil == bad:
                profil = ""

        msisdn_clean = re.sub(r"[^0-9]", "", msisdn_raw)

        # Skip si pas de MSISDN valide
        if not msisdn_clean or len(msisdn_clean) < 9:
            continue

        # Si le 'nom' ressemble à un MSISDN (même valeur), le vider
        if re.sub(r"[^0-9]", "", nom) == msisdn_clean:
            nom = ""

        clients.append({
            "msisdn":      msisdn_clean,
            "nom":         nom,
            "pos_profile": profil,
        })

    return clients


# ===========================================================================
# ONGLET 1 — IMPORT (Super Admin uniquement)
# ===========================================================================
if tab_import is not None:
    with tab_import:
        st.subheader("Importer un portefeuille clients")
        st.info(
            "Format attendu : fichier Excel ALBARKA avec colonnes "
            "**numéro_ccial** (MSISDN), **pos_profile** et optionnellement **Nom du client**. "
            "Les lignes vides en début de fichier sont gérées automatiquement.",
            icon="ℹ️",
        )

        if not commerciaux:
            st.warning("Aucun commercial trouvé. Crée d'abord les comptes dans Administration.")
        else:
            col1, col2 = st.columns(2)
            commercial_import = col1.selectbox(
                "Commercial",
                commerciaux,
                format_func=lambda c: c["dsm_name"],
                key="sel_com_import_pf",
            )
            nom_pf = col2.text_input(
                "Nom du portefeuille (ex. Portefeuille Août 2026)",
                key="nom_pf",
            )

            fichier_xl = st.file_uploader(
                "Fichier Excel (.xlsx)", type=["xlsx"], key="up_portefeuille"
            )

            clients_preview = None
            parse_error = None

            if fichier_xl is not None:
                try:
                    fichier_xl.seek(0)
                    clients_preview = _parse_portefeuille_file(fichier_xl)

                    if clients_preview:
                        st.caption(
                            f"✅ **{len(clients_preview)} clients** détectés · "
                            f"Commercial sélectionné : **{commercial_import['dsm_name']}**"
                        )
                        # Aperçu tableau
                        df_prev = pd.DataFrame(clients_preview).rename(columns={
                            "msisdn":      "MSISDN",
                            "nom":         "Nom du client",
                            "pos_profile": "Profil POS",
                        })
                        st.dataframe(df_prev.head(10), hide_index=True, use_container_width=True)
                        if len(clients_preview) > 10:
                            st.caption(f"… et {len(clients_preview) - 10} autres clients.")
                    else:
                        st.warning("Aucun client valide trouvé dans le fichier.")

                except Exception as e:
                    parse_error = str(e)
                    st.error(f"Impossible de lire le fichier : {e}")

            if st.button("Créer le portefeuille", key="btn_create_pf", type="primary"):
                if not nom_pf.strip():
                    st.error("Le nom du portefeuille est obligatoire.")
                elif parse_error:
                    st.error(f"Corrige l'erreur de lecture : {parse_error}")
                elif not clients_preview:
                    st.error("Importe un fichier valide avec au moins un client.")
                else:
                    # Convertir au format attendu par db.create_portefeuille
                    clients_db = [
                        {
                            "nom":       c["nom"] or c["msisdn"],  # nom ou MSISDN si nom vide
                            "telephone": c["msisdn"],              # MSISDN = clé de rapprochement
                            "localite":  c["pos_profile"],
                        }
                        for c in clients_preview
                    ]
                    try:
                        pf_id = db.create_portefeuille(
                            commercial_id=commercial_import["id"],
                            nom=nom_pf.strip(),
                            date_import=date.today().isoformat(),
                            clients=clients_db,
                        )
                        st.success(
                            f"Portefeuille **{nom_pf}** créé pour **{commercial_import['dsm_name']}** "
                            f"— {len(clients_preview)} clients (id={pf_id})."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la création : {e}")


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

                if is_super:
                    if c4.button("Supprimer", key=f"del_pf_{pf['id']}"):
                        st.session_state[f"confirm_del_{pf['id']}"] = True

                    if st.session_state.get(f"confirm_del_{pf['id']}"):
                        st.warning(
                            f"Supprimer **{pf['nom']}** et ses {pf['nb_clients']} clients ?"
                        )
                        cy, cn = st.columns(2)
                        if cy.button("Confirmer", key=f"conf_y_{pf['id']}", type="primary"):
                            db.delete_portefeuille(pf["id"])
                            st.session_state.pop(f"confirm_del_{pf['id']}", None)
                            st.success(f"Portefeuille **{pf['nom']}** supprimé.")
                            st.rerun()
                        if cn.button("Annuler", key=f"conf_n_{pf['id']}"):
                            st.session_state.pop(f"confirm_del_{pf['id']}", None)
                            st.rerun()

                with st.expander(f"Voir les {pf['nb_clients']} clients"):
                    clients = db.list_clients(pf["id"])
                    if clients:
                        df_c = pd.DataFrame(clients)[["nom", "telephone", "localite"]]
                        df_c.columns = ["Nom / MSISDN", "MSISDN", "Profil POS"]
                        st.dataframe(df_c, hide_index=True, use_container_width=True)
                    else:
                        st.info("Aucun client enregistré.")


# ===========================================================================
# ONGLET 3 — COUVERTURE (point 5)
# ===========================================================================
with tab_couverture:
    st.subheader("Calcul de couverture du portefeuille")
    st.write(
        "Dépose le fichier CSV brut MTN (ex. `PARF-1-14.csv`) du commercial "
        "sur la période souhaitée. L'app identifie dans ce fichier quels clients "
        "du portefeuille ont été touchés, combien de fois et à quelle date."
    )
    st.info(
        "Le rapprochement se fait par **MSISDN** : les colonnes `From` et `To` "
        "du CSV brut (format `FRI:237XXXXXXXXX/MSISDN`) sont comparées aux MSISDN "
        "du portefeuille.",
        icon="ℹ️",
    )

    portefeuilles_tous = db.list_portefeuilles()

    if not portefeuilles_tous:
        st.info("Aucun portefeuille disponible. Importe d'abord un portefeuille dans l'onglet Import.")
    else:
        pf_choisi = st.selectbox(
            "Portefeuille",
            portefeuilles_tous,
            format_func=lambda p: f"{p['dsm_name']} — {p['nom']} ({p['nb_clients']} clients)",
            key="sel_pf_couv",
        )

        fichiers_csv = st.file_uploader(
            "Fichier(s) CSV brut MTN (un ou plusieurs)",
            type=["csv"],
            accept_multiple_files=True,
            key="up_csv_couv",
        )

        if st.button("Calculer la couverture", key="btn_couv", type="primary") and fichiers_csv:

            # Récupérer les MSISDN du portefeuille
            clients_pf = db.list_clients(pf_choisi["id"])
            if not clients_pf:
                st.error("Ce portefeuille ne contient aucun client.")
                st.stop()

            # Index MSISDN → client
            msisdn_index: dict[str, dict] = {}
            for c in clients_pf:
                tel = re.sub(r"[^0-9]", "", str(c.get("telephone") or ""))
                if tel:
                    msisdn_index[tel] = c

            total_clients = len(clients_pf)
            total_msisdn_pf = len(msisdn_index)

            # Identifier l'alias du commercial depuis le portefeuille
            com_id_pf = pf_choisi["commercial_id"]
            alias_pf = db.get_alias(com_id_pf)

            # Comptage des contacts : {msisdn: {nb, dates, nom_mtm}}
            contacts: dict[str, dict] = {}
            erreurs = []

            with st.spinner("Analyse des fichiers CSV en cours…"):
                for f in fichiers_csv:
                    try:
                        f.seek(0)
                        df_csv = pd.read_csv(f, dtype=str)
                        df_csv.columns = df_csv.columns.str.strip()

                        # Vérifier les colonnes nécessaires
                        if "From" not in df_csv.columns or "To" not in df_csv.columns:
                            erreurs.append(
                                f"{f.name} : colonnes 'From' et 'To' absentes — "
                                "utilise le fichier CSV brut MTN (pas le nettoyé)."
                            )
                            continue

                        # Filtrer Transfer uniquement
                        if "Type" in df_csv.columns:
                            df_csv = df_csv[df_csv["Type"].str.strip() == "Transfer"]

                        for _, row in df_csv.iterrows():
                            # Extraire les MSISDN depuis From et To
                            # Format : FRI:237672153381/MSISDN
                            def _extract_msisdn(val: str) -> str:
                                m = re.search(r"(\d{9,12})/MSISDN", str(val))
                                return m.group(1) if m else ""

                            msisdn_from = _extract_msisdn(str(row.get("From", "")))
                            msisdn_to   = _extract_msisdn(str(row.get("To",   "")))
                            name_from   = str(row.get("From name", "")).strip()
                            name_to     = str(row.get("To name",   "")).strip()
                            date_tx     = str(row.get("Date", "")).strip()[:10]  # AAAA-MM-JJ

                            # Identifier le commercial (celui qui correspond à l'alias)
                            is_from_commercial = (
                                alias_pf and name_from.upper() == alias_pf.upper()
                            )
                            is_to_commercial = (
                                alias_pf and name_to.upper() == alias_pf.upper()
                            )

                            # La contrepartie est l'autre côté
                            if is_from_commercial:
                                cp_msisdn = msisdn_to
                                cp_nom    = name_to
                            elif is_to_commercial:
                                cp_msisdn = msisdn_from
                                cp_nom    = name_from
                            else:
                                # Pas d'alias → on prend les deux MSISDN
                                # et on vérifie lequel est dans le portefeuille
                                for msisdn_c, nom_c in [
                                    (msisdn_from, name_from),
                                    (msisdn_to,   name_to),
                                ]:
                                    if msisdn_c in msisdn_index:
                                        if msisdn_c not in contacts:
                                            contacts[msisdn_c] = {
                                                "nb": 0, "dates": set(), "nom_mtm": nom_c
                                            }
                                        contacts[msisdn_c]["nb"] += 1
                                        contacts[msisdn_c]["dates"].add(date_tx)
                                continue

                            # Vérifier si la contrepartie est dans le portefeuille
                            if cp_msisdn and cp_msisdn in msisdn_index:
                                if cp_msisdn not in contacts:
                                    contacts[cp_msisdn] = {
                                        "nb": 0, "dates": set(), "nom_mtm": cp_nom
                                    }
                                contacts[cp_msisdn]["nb"] += 1
                                contacts[cp_msisdn]["dates"].add(date_tx)

                    except Exception as e:
                        erreurs.append(f"{f.name} : {e}")

            for err in erreurs:
                st.warning(err)

            # Construire le tableau résultat
            lignes = []
            for c in clients_pf:
                tel = re.sub(r"[^0-9]", "", str(c.get("telephone") or ""))
                contact_data = contacts.get(tel, {})
                nb = contact_data.get("nb", 0)
                dates_set = sorted(contact_data.get("dates", set()))
                premiere = min(dates_set) if dates_set else "—"
                derniere = max(dates_set) if dates_set else "—"

                lignes.append({
                    "MSISDN":               tel or c.get("nom", ""),
                    "Nom associé":          contact_data.get("nom_mtm") or c.get("nom", ""),
                    "Profil POS":           c.get("localite", ""),
                    "Nombre de contacts":   nb,
                    "Première transaction": premiere,
                    "Dernière transaction": derniere,
                })

            df_result = pd.DataFrame(lignes).sort_values(
                "Nombre de contacts", ascending=False
            ).reset_index(drop=True)

            # Métriques
            st.divider()
            nb_touches = int((df_result["Nombre de contacts"] > 0).sum())
            nb_non_touches = total_clients - nb_touches
            total_contacts = int(df_result["Nombre de contacts"].sum())
            taux = nb_touches / total_clients if total_clients else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clients dans le portefeuille", total_clients)
            m2.metric("Clients touchés",              nb_touches)
            m3.metric("Jamais touchés",               nb_non_touches)
            m4.metric("Taux de couverture",           f"{taux:.1%}")
            st.metric("Total de contacts (transactions)", f"{total_contacts:,}")

            st.divider()

            # Filtre affichage
            filtre_aff = st.selectbox(
                "Afficher",
                ["Tous", "Touchés uniquement", "Non touchés uniquement"],
                key="filtre_couv_aff",
            )
            df_aff = df_result.copy()
            if filtre_aff == "Touchés uniquement":
                df_aff = df_aff[df_aff["Nombre de contacts"] > 0]
            elif filtre_aff == "Non touchés uniquement":
                df_aff = df_aff[df_aff["Nombre de contacts"] == 0]

            st.dataframe(df_aff, hide_index=True, use_container_width=True)
            st.caption(
                f"Portefeuille : **{pf_choisi['nom']}** · "
                f"Commercial : **{pf_choisi['dsm_name']}** · "
                f"Alias : {alias_pf or '—'} · "
                f"{len(fichiers_csv)} fichier(s) analysé(s)"
            )

            # Export Excel — identique au format Suivi-contacts-portefeuille-EWANE.xlsx
            st.divider()
            df_export = df_result.copy()
            df_synthese = pd.DataFrame([
                {"Indicateur": "Total clients dans le portefeuille", "Valeur": total_clients},
                {"Indicateur": "Clients jamais touchés (0 transaction)", "Valeur": nb_non_touches},
                {"Indicateur": "Total de contacts (transactions) sur la période", "Valeur": total_contacts},
                {"Indicateur": "Taux de couverture", "Valeur": f"{taux:.1%}"},
            ])

            xlsx = export_df_to_excel(
                {
                    "Suivi contacts":  df_export,
                    "Synthèse":        df_synthese,
                },
                titre=f"Suivi contacts portefeuille — {pf_choisi['dsm_name']}",
                source_label="ALBARKA — Portefeuilles",
            )
            st.download_button(
                "Exporter (Excel)",
                data=xlsx,
                file_name=f"suivi_contacts_{pf_choisi['dsm_name']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_couv",
            )
