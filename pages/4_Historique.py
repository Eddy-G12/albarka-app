"""
pages/4_Historique.py
======================
Volet Historique — Super Admin et Admin.
Consultation des traitements passés avec re-téléchargement.
"""

import streamlit as st
from pathlib import Path

from core import db
from core.auth import require_role, show_user_badge

st.set_page_config(page_title="Historique — ALBARKA", layout="wide")

from core.ui import apply_theme, show_page_header
apply_theme()

require_role("super_admin", "admin")
show_user_badge()

st.title("Historique des traitements")
st.write("Retrouve un traitement déjà effectué, par date ou par mot-clé.")

recherche = st.text_input("Recherche (ex. une date au format 2026-08-11, ou un nom)", key="search_histo")
type_filtre = st.selectbox(
    "Type", ["Tous", "qr_code", "transactions", "comparatif"], key="filtre_type_histo"
)

if recherche:
    resultats = db.search_imports(recherche)
else:
    resultats = db.list_imports(None if type_filtre == "Tous" else type_filtre)

if type_filtre != "Tous" and recherche:
    resultats = [r for r in resultats if r["type_fichier"] == type_filtre]

if not resultats:
    st.info("Aucun traitement trouvé.")
else:
    for r in resultats:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.markdown(f"**{r['type_fichier']}** — {r['cle']}")
            col2.write(f"Données du {r['date_donnees']} · {r['nb_lignes']} lignes")
            col2.caption(f"Traité le {r['date_execution']}")
            chemin = Path(r["chemin_fichier"])
            if chemin.exists():
                with open(chemin, "rb") as fh:
                    col3.download_button(
                        "Télécharger", data=fh.read(), file_name=chemin.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_histo_{r['id']}"
                    )
            else:
                col3.caption("Fichier introuvable")
