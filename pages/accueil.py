"""
pages/accueil.py
=================
Page d'accueil post-connexion — affiche les modules disponibles selon le rôle.
"""

import streamlit as st
from core.auth import get_current_user, get_role, show_user_badge
from core.ui import apply_theme, show_page_header

apply_theme()
show_user_badge()

user = get_current_user()
role = get_role()

role_labels = {
    "super_admin": "Super Administrateur",
    "admin":       "Administrateur",
    "commercial":  "Commercial",
}

show_page_header(
    "Système de pilotage réseau agents",
    f"Bienvenue, {user['nom']} · {role_labels.get(role, role)}",
)

st.divider()

if role == "super_admin":
    st.markdown("""
    ### Modules disponibles

    | Module | Description |
    |---|---|
    | **Dashboard Global** | Vue consolidée de toutes les performances du réseau |
    | **Transactions** | Import CSV MoMo — nettoyage, TCD, points touchés, clients servis |
    | **Suivi QR Code** | Classification des agents par statut d'utilisation QR |
    | **Étude Comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Cash Flow** | Import fichier SAE MTN — classements POS, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code (métriques, segments, DSM) |
    | **Portefeuilles** | Gestion des portefeuilles clients par commercial |
    | **Appro / Destockage** | Suivi appros et destockages (calculé depuis Transactions) |
    | **Comparaisons MoM** | Évolutions mensuelles tous indicateurs |
    | **Réactivité Commerciale** | Transactions/jour, clients/jour, temps mort, recharge |
    | **MoMo App (Parrainages)** | Saisie et suivi des parrainages Mobile Money |
    | **Suivi Personnes** | Suivi des personnes spécialement suivies |
    | **Administration** | Gestion des utilisateurs, aliases, seuils |
    """)

elif role == "admin":
    st.markdown("""
    ### Modules disponibles

    | Module | Description |
    |---|---|
    | **Dashboard Global** | Vue consolidée de toutes les performances du réseau |
    | **Étude Comparative** | Comparaison de deux dates QR Code |
    | **Historique** | Consultation des traitements passés |
    | **Cash Flow** | Classements POS, alertes seuil |
    | **Dashboard QR Code** | Vue agrégée réseau QR Code |
    | **Portefeuilles** | Consultation des portefeuilles clients |
    | **Appro / Destockage** | Consultation appros et destockages |
    | **Comparaisons MoM** | Évolutions mensuelles tous indicateurs |
    | **Réactivité Commerciale** | Transactions/jour, clients/jour, temps mort, recharge |
    """)

elif role == "commercial":
    st.markdown("""
    ### Votre espace personnel

    | Module | Description |
    |---|---|
    | **Mon Dashboard** | Vos agents QR Code, votre rang cash, vos indicateurs |
    | **Comparaisons MoM** | Vos évolutions mensuelles |
    """)

st.divider()
st.caption("ALBARKA — Application locale · Aucune donnée transmise à un serveur externe")
