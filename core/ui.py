"""
core/ui.py
===========

Helpers de présentation et charte graphique ALBARKA.

Usage dans chaque page :
    from core.ui import apply_theme, show_logo, show_page_header

    apply_theme()           # injecter le CSS global (appeler en début de page)
    show_logo(size="md")    # afficher le logo dans la sidebar ou en page
    show_page_header("Mon titre", "Sous-titre optionnel")

Charte graphique ALBARKA :
    Jaune     #F5A623  — boutons, accents, highlights, bordures actives
    Jaune foncé #E0950F — hover boutons
    Noir      #1A1A1A  — textes, titres, navigation
    Blanc     #FFFFFF  — fonds, cartes
    Gris clair #F8F9FA — séparations, fonds secondaires
    Gris moyen #E9ECEF — bordures, dividers
"""

import base64
from pathlib import Path

import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────

C_JAUNE        = "#F5A623"
C_JAUNE_FONCE  = "#E0950F"
C_NOIR         = "#1A1A1A"
C_BLANC        = "#FFFFFF"
C_GRIS_CLAIR   = "#F8F9FA"
C_GRIS_MOYEN   = "#E9ECEF"
C_GRIS_TEXTE   = "#6C757D"

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo_albarka.svg"


# ──────────────────────────────────────────────────────────────────────────────
# Lecture du logo
# ──────────────────────────────────────────────────────────────────────────────

def _logo_svg() -> str:
    """Retourne le contenu brut du fichier SVG du logo."""
    if LOGO_PATH.exists():
        return LOGO_PATH.read_text(encoding="utf-8")
    # Fallback inline si le fichier n'existe pas
    return """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80">
      <polygon points="32,0 64,32 32,64 0,32" fill="#F5A623" transform="translate(8,8)"/>
      <polygon points="32,12 52,32 32,52 12,32" fill="#1A1A1A" transform="translate(8,8)"/>
      <polygon points="32,22 42,32 32,42 22,32" fill="#F5A623" transform="translate(8,8)"/>
      <circle cx="40" cy="40" r="5" fill="#1A1A1A"/>
      <text x="88" y="46" font-family="Arial" font-size="32" font-weight="900"
            letter-spacing="2" fill="#1A1A1A">ALBARKA</text>
      <text x="90" y="64" font-family="Arial" font-size="11" letter-spacing="3"
            fill="#F5A623">SUPER AGENT MOBILE MONEY</text>
    </svg>"""


def _logo_b64() -> str:
    """Retourne le logo en base64 (pour src d'une balise <img>)."""
    svg = _logo_svg()
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"


# ──────────────────────────────────────────────────────────────────────────────
# CSS global
# ──────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Variables ───────────────────────────────────────────────── */
:root {
    --albarka-jaune:       #F5A623;
    --albarka-jaune-fonce: #E0950F;
    --albarka-noir:        #1A1A1A;
    --albarka-blanc:       #FFFFFF;
    --albarka-gris-clair:  #F8F9FA;
    --albarka-gris-moyen:  #E9ECEF;
    --albarka-gris-texte:  #6C757D;
    --radius:              8px;
    --shadow:              0 2px 8px rgba(0,0,0,0.08);
}

/* ── Fond général ────────────────────────────────────────────── */
.stApp {
    background-color: var(--albarka-blanc);
}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--albarka-noir) !important;
    border-right: 3px solid var(--albarka-jaune);
}
[data-testid="stSidebar"] * {
    color: var(--albarka-blanc) !important;
}
[data-testid="stSidebar"] .stMarkdown a {
    color: var(--albarka-jaune) !important;
}
/* Séparateur sidebar */
[data-testid="stSidebar"] hr {
    border-color: rgba(245, 166, 35, 0.3) !important;
}
/* Texte de navigation actif */
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: var(--albarka-jaune) !important;
    border-radius: var(--radius);
}
[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: var(--albarka-noir) !important;
    font-weight: 700 !important;
}
/* Hover navigation */
[data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(245, 166, 35, 0.15) !important;
    border-radius: var(--radius);
}

/* ── Boutons principaux ──────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {
    background-color: var(--albarka-jaune) !important;
    color: var(--albarka-noir) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
    transition: background-color 0.2s ease, transform 0.1s ease;
}
.stButton > button:hover {
    background-color: var(--albarka-jaune-fonce) !important;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0);
}

/* ── Boutons de téléchargement ───────────────────────────────── */
.stDownloadButton > button {
    background-color: var(--albarka-noir) !important;
    color: var(--albarka-blanc) !important;
    border: 2px solid var(--albarka-jaune) !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
}
.stDownloadButton > button:hover {
    background-color: var(--albarka-jaune) !important;
    color: var(--albarka-noir) !important;
}

/* ── Métriques (cartes KPI) ──────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: var(--albarka-gris-clair);
    border-radius: var(--radius);
    padding: 14px 18px !important;
    border-left: 4px solid var(--albarka-jaune);
    box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] {
    color: var(--albarka-gris-texte) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    color: var(--albarka-noir) !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
}
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Onglets ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tab"] {
    color: var(--albarka-gris-texte) !important;
    font-weight: 600;
    border-radius: var(--radius) var(--radius) 0 0;
    transition: color 0.15s;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--albarka-jaune) !important;
    border-bottom: 3px solid var(--albarka-jaune) !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: var(--albarka-jaune) !important;
}

/* ── Selectbox / Widgets ─────────────────────────────────────── */
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stSlider"] label,
[data-testid="stDateInput"] label,
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
    color: var(--albarka-noir) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}

/* ── Dataframe / Tables ──────────────────────────────────────── */
[data-testid="stDataFrame"] th {
    background-color: var(--albarka-noir) !important;
    color: var(--albarka-blanc) !important;
    font-weight: 700 !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background-color: rgba(245, 166, 35, 0.08) !important;
}

/* ── Alerts / Info / Warning / Error ─────────────────────────── */
[data-testid="stAlert"][data-baseweb="notification"] {
    border-radius: var(--radius) !important;
}

/* ── Dividers ────────────────────────────────────────────────── */
hr {
    border-color: var(--albarka-gris-moyen) !important;
    margin: 1.2rem 0 !important;
}

/* ── Titres de page ──────────────────────────────────────────── */
h1 {
    color: var(--albarka-noir) !important;
    font-weight: 800 !important;
    border-bottom: 3px solid var(--albarka-jaune);
    padding-bottom: 0.4rem;
    margin-bottom: 1rem !important;
}
h2, h3 {
    color: var(--albarka-noir) !important;
    font-weight: 700 !important;
}

/* ── Expander ────────────────────────────────────────────────── */
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: var(--albarka-noir) !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--albarka-jaune) !important;
}

/* ── Footer ──────────────────────────────────────────────────── */
footer { display: none !important; }
#MainMenu { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── Formulaire de connexion ─────────────────────────────────── */
.login-container {
    background-color: var(--albarka-blanc);
    border-radius: 12px;
    padding: 2.5rem 2rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    border-top: 5px solid var(--albarka-jaune);
    max-width: 440px;
    margin: 0 auto;
}
.login-logo {
    display: flex;
    justify-content: center;
    margin-bottom: 1.5rem;
}

/* ── Page header ─────────────────────────────────────────────── */
.page-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.2rem;
}
.page-header-logo {
    height: 44px;
    flex-shrink: 0;
}
.page-header-title {
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--albarka-noir);
    margin: 0;
    line-height: 1.2;
}
.page-header-subtitle {
    font-size: 0.85rem;
    color: var(--albarka-gris-texte);
    margin: 0;
}

/* ── Sidebar logo container ──────────────────────────────────── */
.sidebar-logo {
    padding: 1rem 0.5rem 0.5rem 0.5rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid rgba(245,166,35,0.3);
}

/* ── Badge rôle utilisateur ──────────────────────────────────── */
.user-badge {
    background-color: rgba(245,166,35,0.15);
    border: 1px solid rgba(245,166,35,0.4);
    border-radius: 6px;
    padding: 6px 12px;
    margin-top: 4px;
}
.user-badge-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--albarka-blanc);
}
.user-badge-role {
    font-size: 0.75rem;
    color: var(--albarka-jaune);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ── Conteneur stat card pour dashboard ─────────────────────── */
.stat-card {
    background: var(--albarka-blanc);
    border-radius: var(--radius);
    border-left: 4px solid var(--albarka-jaune);
    padding: 16px;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
# Fonctions publiques
# ──────────────────────────────────────────────────────────────────────────────

def apply_theme() -> None:
    """
    Injecte le CSS global ALBARKA dans la page courante.
    À appeler en début de chaque page, après st.set_page_config().
    """
    st.markdown(_CSS, unsafe_allow_html=True)


def show_logo(size: str = "md", center: bool = False) -> None:
    """
    Affiche le logo ALBARKA en HTML inline (SVG embarqué en base64).

    size : "sm" (160px) | "md" (240px) | "lg" (320px) | "xl" (420px)
    center : True pour centrer horizontalement
    """
    widths = {"sm": 160, "md": 240, "lg": 320, "xl": 420}
    w = widths.get(size, 240)
    b64 = _logo_b64()
    align = "text-align:center;" if center else ""
    st.markdown(
        f'<div style="{align}margin-bottom:0.5rem;">'
        f'<img src="{b64}" width="{w}" alt="Logo ALBARKA" style="max-width:100%;">'
        f'</div>',
        unsafe_allow_html=True,
    )


def show_sidebar_logo() -> None:
    """
    Affiche le logo ALBARKA en haut de la sidebar.
    À appeler dans la sidebar (dans un `with st.sidebar:` ou directement
    depuis show_user_badge).
    """
    b64 = _logo_b64()
    st.sidebar.markdown(
        f'<div class="sidebar-logo">'
        f'<img src="{b64}" width="200" alt="ALBARKA" style="max-width:100%;filter:brightness(0) invert(1);">'
        f'</div>',
        unsafe_allow_html=True,
    )


def show_page_header(title: str, subtitle: str = "") -> None:
    """
    Affiche un en-tête de page avec logo inline + titre + sous-titre optionnel.
    Remplace st.title() pour un rendu cohérent avec la charte.
    """
    b64 = _logo_b64()
    sub_html = (
        f'<p class="page-header-subtitle">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f'<div class="page-header">'
        f'  <img src="{b64}" class="page-header-logo" alt="ALBARKA">'
        f'  <div>'
        f'    <p class="page-header-title">{title}</p>'
        f'    {sub_html}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def show_login_logo() -> None:
    """
    Affiche le logo centré et en grande taille pour la page de connexion.
    """
    b64 = _logo_b64()
    st.markdown(
        f'<div class="login-logo">'
        f'<img src="{b64}" width="280" alt="ALBARKA" style="max-width:90%;">'
        f'</div>',
        unsafe_allow_html=True,
    )


def badge_role(role: str) -> str:
    """Retourne un label lisible pour l'affichage du rôle."""
    return {
        "super_admin": "Super Administrateur",
        "admin":       "Administrateur",
        "commercial":  "Commercial",
    }.get(role, role)
