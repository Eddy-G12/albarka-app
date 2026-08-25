"""
app.py — Point d'entrée de l'application ALBARKA
=================================================

Ce fichier gère uniquement la page d'accueil / connexion.
Les fonctionnalités sont dans le dossier pages/ :
  - 0_Dashboard_Global.py    (Super Admin / Admin)
  - 1_Transactions.py        (Super Admin)
  - 2_Suivi_QR_Code.py       (Super Admin)
  - 3_Etude_Comparative.py   (Super Admin / Admin)
  - 4_Historique.py          (Super Admin / Admin)
  - 5_Administration.py      (Super Admin)
  - 6_Cash_Flow.py           (Super Admin / Admin)
  - 7_Dashboard_QR_Admin.py  (Super Admin / Admin)
  - 8_Mon_Dashboard.py       (Commercial)
  - 9_Portefeuilles.py       (Super Admin / Admin)
  - 10_Appro_Destockage.py   (Super Admin / Admin)
  - 11_Comparaison_MoM.py    (Tous)
  - 12_Reactivite_Commerciale.py (Super Admin / Admin)

Lancement : streamlit run app.py
"""

import streamlit as st
from core import db
from core.auth import require_auth, show_user_badge, get_current_user, get_role
from core.ui import apply_theme, show_page_header, show_login_logo

st.set_page_config(
    page_title="ALBARKA — Pilotage réseau agents",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Thème ALBARKA
apply_theme()

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

# En-tête avec logo
show_page_header(
    "Système de pilotage réseau agents",
    f"Bienvenue, {user['nom']} · {role_labels.get(role, role)}",
)

st.divider()

if role == "super_admin":
    st.markdown("""
    ### Accès disponibles
    Utilisez le menu de navigation à gauche pour accéder aux modules :

    | Module | Description |
    |---|---|
    | **Dashboard Global** | Vue consolidée de toutes les performances du réseau |
    | **Transactions** | Import des listings Mobile Money, tableaux croisés |
    | **Suivi QR Code** | Classification des agents par statut d'utilisation QR |
    | **Étude comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Administration** | Gestion des utilisateurs et configuration des seuils |
    | **Cash Flow** | Import listings MoMo, classements Top/Flop, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code (métriques, segments, DSM) |
    | **Réactivité Commerciale** | Transactions/jour, clients/jour, temps mort, temps de recharge |
    | **Portefeuilles** | Gestion des portefeuilles clients par commercial |
    | **Appro / Destockage** | Suivi des approvisionnements et destockages |
    | **Comparaisons MoM** | Évolutions mensuelles tous indicateurs |
    """)

elif role == "admin":
    st.markdown("""
    ### Accès disponibles
    Utilisez le menu de navigation à gauche pour accéder aux modules :

    | Module | Description |
    |---|---|
    | **Dashboard Global** | Vue consolidée de toutes les performances du réseau |
    | **Étude comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Cash Flow** | Classements Top/Flop cash in/out, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code (métriques, segments, DSM) |
    | **Réactivité Commerciale** | Transactions/jour, clients/jour, temps mort, temps de recharge |
    | **Portefeuilles** | Gestion des portefeuilles clients |
    | **Appro / Destockage** | Suivi des approvisionnements et destockages |
    | **Comparaisons MoM** | Évolutions mensuelles tous indicateurs |
    """)

elif role == "commercial":
    st.markdown("""
    ### Votre espace personnel
    Utilisez le menu de navigation à gauche pour accéder à votre dashboard.

    | Module | Description |
    |---|---|
    | **Mon Dashboard** | Vos agents, vos statuts QR Code, votre rang cash in/out |
    | **Comparaisons MoM** | Vos évolutions mensuelles |
    """)

st.divider()
st.caption("ALBARKA — Application locale · Aucune donnée transmise à un serveur externe")
