"""
pages/4_Historique.py — v2
============================
Historique des traitements — Super Admin et Admin.

Nouveautés v2 :
  - Affichage par défaut : 5 derniers traitements
  - Bouton "Voir plus" : charge 10 traitements supplémentaires à chaque clic
  - Bouton "Supprimer" : supprime uniquement l'enregistrement en base de données
    (jamais le fichier Excel sur disque)
  - Filtres : type de fichier + recherche textuelle
"""

import streamlit as st
from pathlib import Path

from core import db
from core.auth import require_role, show_user_badge, get_role
from core.ui import apply_theme, show_page_header

apply_theme()
require_role("super_admin", "admin")
show_user_badge()

role = get_role()
is_super = role == "super_admin"

show_page_header("Historique", "Traitements passés — téléchargement et suppression des enregistrements")
st.divider()

# ── Filtres ──────────────────────────────────────────────────────────────────
col_rech, col_type = st.columns([2, 1])
recherche   = col_rech.text_input("Recherche (date ISO, nom de fichier…)", key="search_histo")
type_filtre = col_type.selectbox(
    "Type",
    ["Tous", "qr_code", "transactions", "comparatif"],
    key="filtre_type_histo",
)

type_val = None if type_filtre == "Tous" else type_filtre

# ── Pagination ────────────────────────────────────────────────────────────────
# On stocke le nombre de lignes à afficher dans la session
if "histo_nb" not in st.session_state:
    st.session_state["histo_nb"] = 5

# ── Récupération des données ──────────────────────────────────────────────────
if recherche:
    all_results = db.search_imports(recherche)
    if type_val:
        all_results = [r for r in all_results if r["type_fichier"] == type_val]
else:
    total_count = db.count_imports(type_val)
    all_results = db.list_imports(type_val)

total = len(all_results)
nb_affiche = st.session_state["histo_nb"]
resultats = all_results[:nb_affiche]

st.caption(f"Affichage de **{min(nb_affiche, total)}** résultat(s) sur **{total}** au total.")
st.divider()

# ── Affichage ─────────────────────────────────────────────────────────────────
if not all_results:
    st.info("Aucun traitement trouvé.")
else:
    for r in resultats:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 3, 1, 1])

            col1.markdown(f"**{r['type_fichier']}** — `{r['cle']}`")
            col2.write(
                f"Données du {r['date_donnees'] or '—'} · "
                f"{r['nb_lignes'] or 0:,} lignes"
            )
            col2.caption(f"Traité le {r['date_execution']}")

            chemin = Path(r["chemin_fichier"])
            if chemin.exists():
                with open(chemin, "rb") as fh:
                    col3.download_button(
                        "Télécharger",
                        data=fh.read(),
                        file_name=chemin.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_histo_{r['id']}",
                    )
            else:
                col3.caption("Fichier introuvable")

            # Suppression en base (Super Admin uniquement)
            if is_super:
                if col4.button("Supprimer", key=f"del_histo_{r['id']}"):
                    st.session_state[f"confirm_del_histo_{r['id']}"] = True

                if st.session_state.get(f"confirm_del_histo_{r['id']}"):
                    st.warning(
                        f"Supprimer l'enregistrement **{r['cle']}** de l'historique ? "
                        "Le fichier Excel généré sur le disque est conservé."
                    )
                    c_y, c_n = st.columns(2)
                    if c_y.button(
                        "Confirmer", key=f"conf_y_histo_{r['id']}", type="primary"
                    ):
                        db.delete_import(r["type_fichier"], r["cle"])
                        st.session_state.pop(f"confirm_del_histo_{r['id']}", None)
                        # Réinitialiser la pagination si on a supprimé
                        st.session_state["histo_nb"] = min(
                            st.session_state["histo_nb"], total - 1
                        )
                        st.success(f"Enregistrement **{r['cle']}** supprimé de l'historique.")
                        st.rerun()
                    if c_n.button("Annuler", key=f"conf_n_histo_{r['id']}"):
                        st.session_state.pop(f"confirm_del_histo_{r['id']}", None)
                        st.rerun()

    # ── Bouton "Voir plus" ────────────────────────────────────────────────────
    st.divider()
    col_more, col_reset = st.columns([1, 1])

    if nb_affiche < total:
        if col_more.button(
            f"Voir plus ({min(10, total - nb_affiche)} supplémentaires)",
            key="btn_voir_plus",
        ):
            st.session_state["histo_nb"] += 10
            st.rerun()

    if nb_affiche > 5:
        if col_reset.button("Replier", key="btn_replier"):
            st.session_state["histo_nb"] = 5
            st.rerun()
