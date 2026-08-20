"""
app.py — Point d'entrée de l'application ALBARKA
=================================================

Ce fichier gère uniquement la page d'accueil / connexion.
Les fonctionnalités sont dans le dossier pages/ :
  - 1_Transactions.py        (Super Admin)
  - 2_Suivi_QR_Code.py       (Super Admin)
  - 3_Etude_Comparative.py   (Super Admin / Admin)
  - 4_Historique.py          (Super Admin / Admin)
  - 5_Administration.py      (Super Admin)

Lancement : streamlit run app.py
"""

import streamlit as st
from core import db
from core.auth import require_auth, show_user_badge, get_current_user, get_role

st.set_page_config(
    page_title="ALBARKA — Pilotage réseau agents",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# --- Connexion obligatoire ---
require_auth()

# --- Badge utilisateur dans la sidebar ---
show_user_badge()

# --- Accueil selon le rôle ---
user = get_current_user()
role = get_role()

role_labels = {
    "super_admin": "Super Administrateur",
    "admin":       "Administrateur",
    "commercial":  "Commercial",
}

st.title("ALBARKA — Système de pilotage réseau agents")
st.markdown(f"Bienvenue, **{user['nom']}** · *{role_labels.get(role, role)}*")
st.divider()

if role == "super_admin":
    st.markdown("""
    ### Accès disponibles
    Utilisez le menu de navigation à gauche pour accéder aux modules :

    | Module | Description |
    |---|---|
    | **Transactions** | Import des listings Mobile Money, tableaux croisés |
    | **Suivi QR Code** | Classification des agents par statut d'utilisation QR |
    | **Étude comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Administration** | Gestion des utilisateurs et configuration des seuils |
    | **Cash Flow** | Import listings MoMo, classements Top/Flop, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code (métriques, segments, DSM) |
    """)

elif role == "admin":
    st.markdown("""
    ### Accès disponibles
    Utilisez le menu de navigation à gauche pour accéder aux modules :

    | Module | Description |
    |---|---|
    | **Étude comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Cash Flow** | Classements Top/Flop cash in/out, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code (métriques, segments, DSM) |
    """)

elif role == "commercial":
    st.markdown("""
    ### Votre espace personnel
    Utilisez le menu de navigation à gauche pour accéder à votre dashboard.

    | Module | Description |
    |---|---|
    | **Mon Dashboard** | Vos agents, vos statuts QR Code, votre rang cash in/out |
    """)

st.divider()
st.caption("ALBARKA — Application locale · Aucune donnée transmise à un serveur externe")
