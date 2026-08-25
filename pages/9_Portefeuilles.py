"""
pages/9_Portefeuilles.py
=========================
Gestion des portefeuilles commerciaux — Super Admin et Admin.

Trois onglets :
  1. Import       : charge un fichier Excel de clients, crée un portefeuille
                    lié à un commercial
  2. Consultation : liste les portefeuilles, affiche les clients, suppression
  3. Couverture   : upload d'un ou plusieurs CSV de transactions → calcul de
                    la couverture (clients du portefeuille effectivement touchés
                    par le commercial sur la période)

Règle de rapprochement couverture :
  - On normalise les numéros de téléphone des deux côtés (suppression espaces,
    tirets, préfixe +237 / 00237).
  - Un client est "couvert" si son numéro apparaît dans les contreparties des
    transactions du commercial (colonne To name ou From name, selon la
    direction, après exclusion du compte propre).
"""

import streamlit as st
import pandas as pd
from datetime import date

from core import db
from core.auth import require_role, show_user_badge
from core.metrics import load_transactions_full, detect_self_account, _contrepartie, EXCLUDED_NAMES
from core.export import export_df_to_excel

st.set_page_config(page_title="Portefeuilles — ALBARKA", layout="wide")

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
show_user_badge()

st.title("Portefeuilles commerciaux")

tab_import, tab_consultation, tab_couverture = st.tabs([
    "Import",
    "Consultation",
    "Couverture",
])

commerciaux = db.list_commerciaux()


# ===========================================================================
# HELPERS
# ===========================================================================

def _normalise_tel(tel) -> str:
    """Normalise un numéro de téléphone pour le rapprochement."""
    if pd.isna(tel) or str(tel).strip() in ("", "nan"):
        return ""
    t = str(tel).strip().replace(" ", "").replace("-", "").replace(".", "")
    # Supprime le suffixe .0 numérique parasite
    if t.endswith(".0") and t[:-2].isdigit():
        t = t[:-2]
    for prefixe in ("+237", "00237"):
        if t.startswith(prefixe):
            t = t[len(prefixe):]
    return t


def _contreparties_from_csv(fichier, self_account: str) -> set:
    """
    Lit un fichier CSV de transactions et retourne l'ensemble des numéros de
    téléphone des contreparties du compte propre (normalisés).
    Les noms ALBARKA GN SARL / ALBARKA GN SARL 5 sont exclus.
    NOTE : les fichiers transactions contiennent des noms, pas directement
    des numéros. On retourne donc les NOMS des contreparties — le rapprochement
    avec le portefeuille se fera sur le téléphone fourni dans le portefeuille.
    """
    fichier.seek(0)
    df = load_transactions_full(fichier)
    noms = set()
    for _, row in df.iterrows():
        cp = _contrepartie(row, self_account)
        if cp and cp not in EXCLUDED_NAMES:
            noms.add(cp.strip())
    return noms


def _telephones_contreparties(fichier, self_account: str, df_clients: pd.DataFrame) -> set:
    """
    Retourne l'ensemble des téléphones clients (normalisés) effectivement
    touchés par le commercial dans ce fichier de transactions.

    Stratégie double :
      1. Rapprochement direct nom client ↔ nom contrepartie (si le client
         figure dans les transactions avec exactement le même libellé)
      2. Si le portefeuille contient des numéros de téléphone, rapprochement
         téléphone ↔ pos_msisdn / To name / From name selon ce qui est dispo
         (les CSV transactions Mobile Money ne contiennent pas de colonne
         téléphone — on se base sur les noms de contrepartie, qui correspondent
         souvent au nom enregistré dans MTN).

    Retourne les index (téléphones normalisés) des clients couverts.
    """
    fichier.seek(0)
    df_tx = load_transactions_full(fichier)

    # Noms des contreparties (nettoyés)
    noms_cp = set()
    for _, row in df_tx.iterrows():
        cp = _contrepartie(row, self_account)
        if cp and cp not in EXCLUDED_NAMES:
            noms_cp.add(cp.strip().upper())

    couverts = set()

    for _, client in df_clients.iterrows():
        nom_client = str(client.get("nom", "")).strip().upper()
        tel_client  = _normalise_tel(client.get("telephone", ""))

        # Correspondance par nom
        if nom_client and nom_client in noms_cp:
            couverts.add(tel_client or nom_client)
            continue

        # Correspondance partielle : le nom du client est contenu dans un nom de contrepartie
        for cp in noms_cp:
            if nom_client and len(nom_client) >= 4 and nom_client in cp:
                couverts.add(tel_client or nom_client)
                break

    return couverts


# ===========================================================================
# ONGLET 1 : IMPORT
# ===========================================================================
with tab_import:
    st.subheader("Importer un portefeuille clients")
    st.write(
        "Le fichier Excel doit contenir au minimum une colonne **nom** (libellé du client). "
        "Les colonnes **telephone** et **localite** sont optionnelles mais recommandées "
        "pour le calcul de couverture."
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
        nom_portefeuille = col2.text_input(
            "Nom du portefeuille",
            placeholder="ex. Zone Nord — Août 2026",
            key="nom_pf",
        )

        fichier_xl = st.file_uploader(
            "Fichier Excel (.xlsx)", type=["xlsx"], key="up_portefeuille"
        )

        if fichier_xl is not None:
            try:
                df_preview = pd.read_excel(fichier_xl)
                # Normalise les noms de colonnes
                df_preview.columns = df_preview.columns.str.strip().str.lower()
                st.caption(f"Aperçu — {len(df_preview)} lignes, colonnes : {list(df_preview.columns)}")
                st.dataframe(df_preview.head(5), hide_index=True, use_container_width=True)

                # Détection de la colonne nom
                col_nom = next(
                    (c for c in df_preview.columns if "nom" in c),
                    df_preview.columns[0] if len(df_preview.columns) > 0 else None,
                )
                col_tel = next(
                    (c for c in df_preview.columns
                     if any(k in c for k in ("tel", "phone", "msisdn", "mobile"))),
                    None,
                )
                col_loc = next(
                    (c for c in df_preview.columns
                     if any(k in c for k in ("local", "ville", "zone", "quartier", "site"))),
                    None,
                )

                if col_nom:
                    st.caption(
                        f"Colonnes détectées → nom : **{col_nom}**"
                        + (f", téléphone : **{col_tel}**" if col_tel else "")
                        + (f", localité : **{col_loc}**" if col_loc else "")
                    )
            except Exception as e:
                st.error(f"Impossible de lire le fichier : {e}")
                fichier_xl = None
                df_preview = None
                col_nom = col_tel = col_loc = None
        else:
            df_preview = None
            col_nom = col_tel = col_loc = None

        if st.button("Créer le portefeuille", key="btn_create_pf") and fichier_xl is not None:
            if not nom_portefeuille.strip():
                st.error("Le nom du portefeuille est obligatoire.")
            elif df_preview is None:
                st.error("Impossible de lire le fichier.")
            elif col_nom is None:
                st.error("Aucune colonne 'nom' détectée dans le fichier.")
            else:
                clients_liste = []
                for _, row in df_preview.iterrows():
                    nom_val = str(row[col_nom]).strip() if col_nom else ""
                    if not nom_val or nom_val.lower() in ("nan", "none", ""):
                        continue
                    clients_liste.append({
                        "nom": nom_val,
                        "telephone": str(row[col_tel]).strip() if col_tel and pd.notna(row.get(col_tel)) else None,
                        "localite": str(row[col_loc]).strip() if col_loc and pd.notna(row.get(col_loc)) else None,
                    })

                if not clients_liste:
                    st.error("Aucun client valide trouvé dans le fichier.")
                else:
                    try:
                        pf_id = db.create_portefeuille(
                            commercial_id=commercial_import["id"],
                            nom=nom_portefeuille.strip(),
                            date_import=date.today().isoformat(),
                            clients=clients_liste,
                        )
                        st.success(
                            f"Portefeuille **{nom_portefeuille}** créé pour {commercial_import['dsm_name']} "
                            f"— {len(clients_liste)} clients importés (id={pf_id})."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la création : {e}")


# ===========================================================================
# ONGLET 2 : CONSULTATION / SUPPRESSION
# ===========================================================================
with tab_consultation:
    st.subheader("Portefeuilles existants")

    if not commerciaux:
        st.info("Aucun commercial en base.")
    else:
        filtre_com = st.selectbox(
            "Filtrer par commercial (optionnel)",
            [None] + commerciaux,
            format_func=lambda c: "Tous les commerciaux" if c is None else c["dsm_name"],
            key="filtre_com_consultation",
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

                    # Bouton suppression avec confirmation
                    if c4.button("Supprimer", key=f"del_pf_{pf['id']}"):
                        st.session_state[f"confirm_del_{pf['id']}"] = True

                    if st.session_state.get(f"confirm_del_{pf['id']}"):
                        st.warning(
                            f"Confirmer la suppression de **{pf['nom']}** "
                            f"et de ses {pf['nb_clients']} clients ?"
                        )
                        conf1, conf2 = st.columns(2)
                        if conf1.button("Oui, supprimer", key=f"conf_yes_{pf['id']}", type="primary"):
                            db.delete_portefeuille(pf["id"])
                            del st.session_state[f"confirm_del_{pf['id']}"]
                            st.success(f"Portefeuille **{pf['nom']}** supprimé.")
                            st.rerun()
                        if conf2.button("Annuler", key=f"conf_no_{pf['id']}"):
                            del st.session_state[f"confirm_del_{pf['id']}"]
                            st.rerun()

                    # Détail clients (expander)
                    with st.expander(f"Voir les {pf['nb_clients']} clients"):
                        clients = db.list_clients(pf["id"])
                        if clients:
                            df_clients = pd.DataFrame(clients)[["nom", "telephone", "localite"]]
                            df_clients.columns = ["Nom", "Téléphone", "Localité"]
                            st.dataframe(df_clients, hide_index=True, use_container_width=True)
                        else:
                            st.info("Aucun client enregistré.")


# ===========================================================================
# ONGLET 3 : CALCUL DE COUVERTURE
# ===========================================================================
with tab_couverture:
    st.subheader("Calcul de couverture du portefeuille")
    st.write(
        "Sélectionne un portefeuille et dépose les fichiers CSV de transactions "
        "du commercial sur la période souhaitée. L'application identifie quels "
        "clients ont été touchés par au moins une transaction."
    )

    portefeuilles_tous = db.list_portefeuilles()

    if not portefeuilles_tous:
        st.info("Aucun portefeuille disponible. Importe d'abord un portefeuille dans l'onglet Import.")
    else:
        pf_choisi = st.selectbox(
            "Portefeuille",
            portefeuilles_tous,
            format_func=lambda p: f"{p['dsm_name']} — {p['nom']} ({p['nb_clients']} clients)",
            key="sel_pf_couverture",
        )

        fichiers_tx = st.file_uploader(
            "Fichiers CSV de transactions (un ou plusieurs)",
            type=["csv"],
            accept_multiple_files=True,
            key="up_tx_couverture",
        )

        if st.button("Calculer la couverture", key="btn_couverture") and fichiers_tx:
            clients_pf = db.list_clients(pf_choisi["id"])
            if not clients_pf:
                st.error("Ce portefeuille ne contient aucun client.")
            else:
                df_clients = pd.DataFrame(clients_pf)
                total_clients = len(df_clients)
                couverts_global: set = set()
                erreurs = []

                with st.spinner("Analyse des transactions en cours..."):
                    for f in fichiers_tx:
                        try:
                            f.seek(0)
                            df_tx = load_transactions_full(f)
                            if df_tx.empty:
                                erreurs.append(f"{f.name} : aucune transaction exploitable.")
                                continue
                            self_account = detect_self_account(df_tx)
                            couverts_fichier = _telephones_contreparties(f, self_account, df_clients)
                            couverts_global |= couverts_fichier
                        except Exception as e:
                            erreurs.append(f"{f.name} : {e}")

                if erreurs:
                    for err in erreurs:
                        st.warning(err)

                # Résultats
                nb_couverts = len(couverts_global)
                taux = nb_couverts / total_clients if total_clients else 0

                st.divider()
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Clients dans le portefeuille", total_clients)
                col_r2.metric("Clients touchés", nb_couverts)
                col_r3.metric("Taux de couverture", f"{taux:.1%}")

                # Tableau détaillé : couvert / non couvert
                st.divider()
                lignes_detail = []
                for _, client in df_clients.iterrows():
                    nom_client = str(client.get("nom", "")).strip().upper()
                    tel_client  = _normalise_tel(client.get("telephone", ""))
                    cle = tel_client or nom_client
                    couvert = cle in couverts_global
                    lignes_detail.append({
                        "Nom": client.get("nom", ""),
                        "Téléphone": client.get("telephone", ""),
                        "Localité": client.get("localite", ""),
                        "Statut": "Couvert" if couvert else "Non couvert",
                    })

                df_detail = pd.DataFrame(lignes_detail)

                col_filtre, _ = st.columns([1, 3])
                filtre_statut = col_filtre.selectbox(
                    "Afficher",
                    ["Tous", "Couverts uniquement", "Non couverts uniquement"],
                    key="filtre_couverture",
                )
                if filtre_statut == "Couverts uniquement":
                    df_detail = df_detail[df_detail["Statut"] == "Couvert"]
                elif filtre_statut == "Non couverts uniquement":
                    df_detail = df_detail[df_detail["Statut"] == "Non couvert"]

                st.dataframe(df_detail, hide_index=True, use_container_width=True)
                st.caption(
                    f"Portefeuille : **{pf_choisi['nom']}** — Commercial : **{pf_choisi['dsm_name']}** "
                    f"— {len(fichiers_tx)} fichier(s) analysé(s)."
                )

                # Export Excel résultat couverture
                st.divider()
                df_resume_couv = pd.DataFrame([
                    {"Indicateur": "Clients dans le portefeuille", "Valeur": total_clients},
                    {"Indicateur": "Clients touchés",              "Valeur": nb_couverts},
                    {"Indicateur": "Clients non couverts",         "Valeur": total_clients - nb_couverts},
                    {"Indicateur": "Taux de couverture",           "Valeur": f"{taux:.1%}"},
                    {"Indicateur": "Portefeuille",                 "Valeur": pf_choisi["nom"]},
                    {"Indicateur": "Commercial",                   "Valeur": pf_choisi["dsm_name"]},
                    {"Indicateur": "Fichiers analysés",            "Valeur": len(fichiers_tx)},
                ])
                # Export de tous les clients (sans filtre d'affichage)
                df_detail_complet = pd.DataFrame(lignes_detail)

                xlsx_couverture = export_df_to_excel(
                    {
                        "Résumé couverture": df_resume_couv,
                        "Détail clients":    df_detail_complet,
                    },
                    titre=f"Couverture — {pf_choisi['nom']}",
                    source_label=f"ALBARKA — {pf_choisi['dsm_name']}",
                )
                st.download_button(
                    label="Exporter le résultat de couverture (Excel)",
                    data=xlsx_couverture,
                    file_name=f"couverture_{pf_choisi['id']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_couverture",
                )
