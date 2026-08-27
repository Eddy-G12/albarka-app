"""
core/auth.py
============

Gestion de la session d'authentification dans Streamlit.

Utilise st.session_state pour conserver l'utilisateur connecté entre les reruns.
L'authentification repose sur la table `utilisateurs` de db.py (hash SHA-256).

Règle de sécurité :
  - Tant que l'utilisateur n'est PAS authentifié :
      * Seul le formulaire de connexion est affiché
      * Aucune navigation, aucun nom de page, aucun intitulé de module visible
      * Aucun placeholder pré-rempli sur le formulaire (pas d'exemple de login)
      * La sidebar ne montre que le logo — pas d'éléments de navigation
  - Chaque page appelle require_role() qui vérifie le rôle en session ;
    avec st.navigation() ce garde-fou reste mais n'est plus la première ligne de défense.

Usage dans une page :
    from core.auth import require_role, get_current_user, show_user_badge

    require_role("super_admin")          # stoppe si rôle non autorisé
    user = get_current_user()
"""

import streamlit as st
from core import db

SESSION_KEY = "albarka_user"


# ---------------------------------------------------------------------------
# Accesseurs de session
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    """Retourne l'utilisateur connecté (dict) ou None."""
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return get_current_user() is not None


def get_role() -> str | None:
    user = get_current_user()
    return user["role"] if user else None


def is_super_admin() -> bool:
    return get_role() == "super_admin"


def is_admin() -> bool:
    return get_role() in ("admin", "super_admin")


def is_commercial() -> bool:
    return get_role() == "commercial"


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

def login(username: str, password: str) -> bool:
    """Tente une connexion. Retourne True si succès."""
    user = db.authenticate_user(username, password)
    if user:
        st.session_state[SESSION_KEY] = user
        return True
    return False


def logout():
    """Déconnecte l'utilisateur courant et force un rerun."""
    st.session_state.pop(SESSION_KEY, None)
    st.rerun()


# ---------------------------------------------------------------------------
# Page de connexion complète (appelée par app.py quand non authentifié)
# ---------------------------------------------------------------------------

def show_login_page():
    """
    Affiche la page de connexion en pleine page.
    Règles de sécurité appliquées :
      - Aucun placeholder de nom d'utilisateur (pas d'exemple visible)
      - Sidebar vide (logo ALBARKA uniquement, pas de navigation)
      - Aucun intitulé de module ou de page visible
    """
    from core.ui import apply_theme, show_login_logo, show_sidebar_logo

    # Sidebar : logo uniquement, aucune navigation
    with st.sidebar:
        show_sidebar_logo()

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        show_login_logo()

        st.markdown(
            '<div class="login-container">',
            unsafe_allow_html=True,
        )
        st.markdown("### Connexion")
        st.markdown(
            '<p style="color:#6C757D;font-size:0.9rem;margin-bottom:1.2rem;">'
            "Entrez vos identifiants pour accéder à l'application."
            "</p>",
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            # Pas de placeholder — aucun exemple pré-rempli visible
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button(
                "Se connecter",
                use_container_width=True,
                type="primary",
            )
            if submitted:
                if not username or not password:
                    st.error("Identifiant et mot de passe requis.")
                elif login(username.strip(), password):
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<p style="text-align:center;color:#6C757D;font-size:0.75rem;margin-top:1rem;">'
            "ALBARKA · Application locale · Données confidentielles"
            "</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Guards utilisés dans chaque page (deuxième ligne de défense)
# ---------------------------------------------------------------------------

def require_auth():
    """
    Vérifie que l'utilisateur est connecté.
    Si non, affiche la page de login et stoppe.
    (Normalement inutile avec st.navigation() mais gardé comme filet de sécurité.)
    """
    if not is_authenticated():
        show_login_page()
        st.stop()


def require_role(*roles: str):
    """
    Vérifie que l'utilisateur connecté a l'un des rôles autorisés.
    Si non, affiche un message d'accès refusé et stoppe la page.
    """
    require_auth()
    if get_role() not in roles:
        st.error("Accès refusé — vous n'avez pas les droits nécessaires pour cette page.")
        st.stop()


# ---------------------------------------------------------------------------
# Badge utilisateur sidebar (appelé en tête de chaque page)
# ---------------------------------------------------------------------------

def show_user_badge():
    """
    Affiche dans la sidebar :
      - Logo ALBARKA (en haut)
      - Nom + rôle de l'utilisateur connecté
      - Bouton de déconnexion
    """
    from core.ui import show_sidebar_logo

    user = get_current_user()
    if not user:
        return

    role_labels = {
        "super_admin": "Super Admin",
        "admin":       "Admin",
        "commercial":  "Commercial",
    }

    with st.sidebar:
        show_sidebar_logo()
        st.markdown(
            f'<div class="user-badge">'
            f'  <div class="user-badge-name">{user["nom"]}</div>'
            f'  <div class="user-badge-role">'
            f'    {role_labels.get(user["role"], user["role"])}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button("Se déconnecter", use_container_width=True, key="btn_logout"):
            logout()
