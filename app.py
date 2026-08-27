"""
app.py — Point d'entrée unique de l'application ALBARKA
=========================================================

Stratégie de navigation sécurisée :

  - Non authentifié → st.navigation([page_login]) uniquement
    La sidebar ne montre QUE le logo, aucun nom de page, aucune navigation.
    Streamlit ne découvre pas les autres pages car st.navigation() est
    toujours appelé (ce qui désactive l'auto-découverte du dossier pages/).

  - Authentifié → st.navigation(pages_du_role)
    Chaque rôle ne voit QUE ses pages autorisées.

Lancement : streamlit run app.py
"""

import streamlit as st
from core import db
from core.auth import get_current_user, get_role
from core.ui import apply_theme

st.set_page_config(
    page_title="ALBARKA",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
db.init_db()

user = get_current_user()
role = get_role()

# ── Page de login (aucune navigation visible) ────────────────────────────────
if not user:
    nav = st.navigation(
        [st.Page("pages/_login.py", title="Connexion", default=True)],
        position="hidden",   # cache complètement la sidebar de navigation
    )
    nav.run()
    st.stop()

# ── Navigation par rôle ──────────────────────────────────────────────────────
_PAGES = {
    "super_admin": [
        st.Page("pages/accueil.py",                  title="Accueil",               icon="🏠", default=True),
        st.Page("pages/0_Dashboard_Global.py",        title="Dashboard Global",       icon="📊"),
        st.Page("pages/1_Transactions.py",            title="Transactions",           icon="💳"),
        st.Page("pages/2_Suivi_QR_Code.py",           title="Suivi QR Code",          icon="📱"),
        st.Page("pages/3_Etude_Comparative.py",       title="Étude Comparative",      icon="🔍"),
        st.Page("pages/4_Historique.py",              title="Historique",             icon="📋"),
        st.Page("pages/6_Cash_Flow.py",               title="Cash Flow",              icon="💰"),
        st.Page("pages/7_Dashboard_QR_Admin.py",      title="Dashboard QR Code",      icon="📈"),
        st.Page("pages/9_Portefeuilles.py",           title="Portefeuilles",          icon="👥"),
        st.Page("pages/10_Appro_Destockage.py",       title="Appro / Destockage",     icon="📦"),
        st.Page("pages/11_Comparaison_MoM.py",        title="Comparaisons MoM",       icon="📅"),
        st.Page("pages/12_Reactivite_Commerciale.py", title="Réactivité",             icon="⚡"),
        st.Page("pages/13_MoMo_App.py",              title="MoMo App",               icon="🤝"),
        st.Page("pages/14_Suivi_Personnes.py",        title="Suivi Personnes",        icon="👤"),
        st.Page("pages/5_Administration.py",          title="Administration",         icon="⚙️"),
    ],
    "admin": [
        st.Page("pages/accueil.py",                  title="Accueil",               icon="🏠", default=True),
        st.Page("pages/0_Dashboard_Global.py",        title="Dashboard Global",       icon="📊"),
        st.Page("pages/3_Etude_Comparative.py",       title="Étude Comparative",      icon="🔍"),
        st.Page("pages/4_Historique.py",              title="Historique",             icon="📋"),
        st.Page("pages/6_Cash_Flow.py",               title="Cash Flow",              icon="💰"),
        st.Page("pages/7_Dashboard_QR_Admin.py",      title="Dashboard QR Code",      icon="📈"),
        st.Page("pages/9_Portefeuilles.py",           title="Portefeuilles",          icon="👥"),
        st.Page("pages/10_Appro_Destockage.py",       title="Appro / Destockage",     icon="📦"),
        st.Page("pages/11_Comparaison_MoM.py",        title="Comparaisons MoM",       icon="📅"),
        st.Page("pages/12_Reactivite_Commerciale.py", title="Réactivité",             icon="⚡"),
    ],
    "commercial": [
        st.Page("pages/accueil.py",                  title="Accueil",               icon="🏠", default=True),
        st.Page("pages/8_Mon_Dashboard.py",           title="Mon Dashboard",          icon="👤"),
        st.Page("pages/11_Comparaison_MoM.py",        title="Comparaisons MoM",       icon="📅"),
    ],
}

pages = _PAGES.get(role, _PAGES["commercial"])
nav = st.navigation(pages)
nav.run()
