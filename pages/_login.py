"""
pages/_login.py
================
Page de connexion — utilisée par st.navigation() quand l'utilisateur
n'est pas authentifié. Le préfixe _ l'exclut de l'auto-découverte Streamlit.

N'affiche que le formulaire de login : aucune navigation, aucun onglet,
sidebar vide (logo uniquement).
"""

from core.auth import show_login_page

show_login_page()
