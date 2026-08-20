"""
core/auth.py
============

Gestion de la session d'authentification dans Streamlit.

Utilise st.session_state pour conserver l'utilisateur connecté entre les
reruns. L'authentification repose sur la table `utilisateurs` de db.py
(hash SHA-256, pas de dépendance externe).

Usage type dans une page :
    from core.auth import require_auth, get_current_user, logout

    require_auth()                       # affiche le formulaire si non connecté, stoppe sinon
    user = get_current_user()            # dict {id, username, nom, role}
    require_role("super_admin")          # stoppe si le rôle n'est pas autorisé
"""

import streamlit as st
from core import db

SESSION_KEY = "albarka_user"


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


def login(username: str, password: str) -> bool:
    """Tente une connexion. Retourne True si succès, False sinon."""
    user = db.authenticate_user(username, password)
    if user:
        st.session_state[SESSION_KEY] = user
        return True
    return False


def logout():
    """Déconnecte l'utilisateur courant."""
    if SESSION_KEY in st.session_state:
        del st.session_state[SESSION_KEY]
    st.rerun()


def show_login_form():
    """Affiche le formulaire de connexion centré."""
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("## Connexion")
        st.markdown("Entrez vos identifiants pour accéder à l'application.")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Identifiant", placeholder="ex. giovanni")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Identifiant et mot de passe requis.")
                elif login(username.strip(), password):
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")


def require_auth():
    """
    À appeler en tête de chaque page.
    Si l'utilisateur n'est pas connecté, affiche le formulaire et stoppe
    l'exécution de la page (st.stop()).
    """
    if not is_authenticated():
        show_login_form()
        st.stop()


def require_role(*roles: str):
    """
    Vérifie que l'utilisateur connecté a l'un des rôles autorisés.
    Sinon affiche un message d'accès refusé et stoppe la page.
    """
    require_auth()
    if get_role() not in roles:
        st.error("Accès refusé — vous n'avez pas les droits nécessaires pour cette page.")
        st.stop()


def show_user_badge():
    """Affiche dans la sidebar le nom de l'utilisateur connecté + bouton déconnexion."""
    user = get_current_user()
    if not user:
        return
    role_labels = {
        "super_admin": "Super Admin",
        "admin":       "Admin",
        "commercial":  "Commercial",
    }
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**{user['nom']}**")
        st.caption(role_labels.get(user["role"], user["role"]))
        if st.button("Se déconnecter", use_container_width=True, key="btn_logout"):
            logout()
