"""
app.py — Point d'entrée unique de l'application ALBARKA
=========================================================

Gère :
  1. La page de connexion (affichée si non authentifié — aucune navigation visible)
  2. La construction dynamique du menu de navigation selon le rôle connecté
     via st.navigation() — chaque rôle ne voit QUE ses pages autorisées

Lancement : streamlit run app.py

Navigation par rôle :
  super_admin → toutes les pages
  admin       → dashboard global, étude comparative, historique, cash flow,
                dashboard QR, portefeuilles, appro, MoM, réactivité
  commercial  → mon dashboard, MoM (ses données)
"""

import streamlit as st
from core import db
from core.auth import get_current_user, get_role, show_login_page
from core.ui import apply_theme

st.set_page_config(
    page_title="ALBARKA",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
db.init_db()

# ── Si non authentifié : afficher uniquement la page de login ───────────────
# Aucune navigation, aucun nom de page, sidebar vide.
if not get_current_user():
    show_login_page()
    st.stop()

# ── Utilisateur connecté : construire la navigation selon le rôle ────────────
role = get_role()

# Définition de toutes les pages avec leur rôle requis
# Chaque entrée : (titre_menu, chemin_fichier, icone)
_ALL_PAGES = {
    "super_admin": [
        st.Page("pages/accueil.py",                   title="Accueil",                  icon="🏠", default=True),
        st.Page("pages/0_Dashboard_Global.py",         title="Dashboard Global",          icon="📊"),
        st.Page("pages/1_Transactions.py",             title="Transactions",              icon="💳"),
        st.Page("pages/2_Suivi_QR_Code.py",            title="Suivi QR Code",             icon="📱"),
        st.Page("pages/3_Etude_Comparative.py",        title="Étude Comparative",         icon="🔍"),
        st.Page("pages/4_Historique.py",               title="Historique",                icon="📋"),
        st.Page("pages/6_Cash_Flow.py",                title="Cash Flow",                 icon="💰"),
        st.Page("pages/7_Dashboard_QR_Admin.py",       title="Dashboard QR Code",         icon="📈"),
        st.Page("pages/9_Portefeuilles.py",            title="Portefeuilles",             icon="👥"),
        st.Page("pages/10_Appro_Destockage.py",        title="Appro / Destockage",        icon="📦"),
        st.Page("pages/11_Comparaison_MoM.py",         title="Comparaisons MoM",          icon="📅"),
        st.Page("pages/12_Reactivite_Commerciale.py",  title="Réactivité Commerciale",    icon="⚡"),
        st.Page("pages/13_MoMo_App.py",               title="MoMo App (Parrainages)",    icon="🤝"),
        st.Page("pages/14_Suivi_Personnes.py",         title="Suivi Personnes",           icon="👤"),
        st.Page("pages/5_Administration.py",           title="Administration",            icon="⚙️"),
    ],
    "admin": [
        st.Page("pages/accueil.py",                   title="Accueil",                  icon="🏠", default=True),
        st.Page("pages/0_Dashboard_Global.py",         title="Dashboard Global",          icon="📊"),
        st.Page("pages/3_Etude_Comparative.py",        title="Étude Comparative",         icon="🔍"),
        st.Page("pages/4_Historique.py",               title="Historique",                icon="📋"),
        st.Page("pages/6_Cash_Flow.py",                title="Cash Flow",                 icon="💰"),
        st.Page("pages/7_Dashboard_QR_Admin.py",       title="Dashboard QR Code",         icon="📈"),
        st.Page("pages/9_Portefeuilles.py",            title="Portefeuilles",             icon="👥"),
        st.Page("pages/10_Appro_Destockage.py",        title="Appro / Destockage",        icon="📦"),
        st.Page("pages/11_Comparaison_MoM.py",         title="Comparaisons MoM",          icon="📅"),
        st.Page("pages/12_Reactivite_Commerciale.py",  title="Réactivité Commerciale",    icon="⚡"),
    ],
    "commercial": [
        st.Page("pages/accueil.py",                   title="Accueil",                  icon="🏠", default=True),
        st.Page("pages/8_Mon_Dashboard.py",            title="Mon Dashboard",             icon="👤"),
        st.Page("pages/11_Comparaison_MoM.py",         title="Comparaisons MoM",          icon="📅"),
    ],
}

pages_du_role = _ALL_PAGES.get(role, _ALL_PAGES["commercial"])
nav = st.navigation(pages_du_role)
nav.run()
