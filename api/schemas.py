"""
api/schemas.py
==============
Modèles Pydantic — mapping exact des types TypeScript du frontend.
Chaque interface TypeScript dans src/types/index.ts a son équivalent ici.
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    mot_de_passe: str


class UtilisateurOut(BaseModel):
    id: int
    username: str
    nom: str
    role: Literal["super_admin", "admin", "commercial"]
    actif: bool
    dsm_name: Optional[str] = None
    created_at: Optional[str] = None


class LoginResponse(BaseModel):
    utilisateur: UtilisateurOut
    token: str


# ── Commercial ────────────────────────────────────────────────────────────────

class CommercialOut(BaseModel):
    id: int
    utilisateur_id: Optional[int] = None
    dsm_name: str
    telephone: Optional[str] = None
    zone: Optional[str] = None
    actif: bool
    alias: Optional[str] = None


# ── Cash Flow commercial (transactions_momo) ──────────────────────────────────

class LigneCashCommercial(BaseModel):
    commercial_id: int
    dsm_name: str
    cash_in: float
    cash_out: float
    nb_transactions: int


class EvolutionCashReseau(BaseModel):
    mois: str
    cash_in: float
    cash_out: float


class AlerteSeuilCommercial(BaseModel):
    commercial_id: int
    dsm_name: str
    cash_in: float
    cash_out: float
    nb_transactions: int
    ecart_in: float
    ecart_out: float


class AlertesSeuilResponse(BaseModel):
    seuil_in: float
    seuil_out: float
    lignes: list[AlerteSeuilCommercial]


# ── Cash Flow POS (source SAE MTN) ────────────────────────────────────────────

class CashflowPosOut(BaseModel):
    pos_id: int
    acceptor_id: str
    agent_name: str
    agent_msisdn: str
    mois: str
    cash_in: float
    cash_out: float


class ClassementPosResponse(BaseModel):
    top: list[CashflowPosOut]
    flop: list[CashflowPosOut]
    total: int


class AlerteSeuilPos(BaseModel):
    pos_id: int
    acceptor_id: str
    agent_name: str
    agent_msisdn: str
    mois: str
    cash_in: float
    cash_out: float
    ecart_in: float
    ecart_out: float


class AlertesSeuilPosResponse(BaseModel):
    seuil_in: float
    seuil_out: float
    lignes: list[AlerteSeuilPos]


# ── Comparaison MoM POS ───────────────────────────────────────────────────────

class ComparaisonMoMPos(BaseModel):
    mois: list[str]
    top_par_mois: dict[str, list[CashflowPosOut]]
    flop_par_mois: dict[str, list[CashflowPosOut]]
    top_cumule: list[dict]
    constants_top: list[str]
    constants_flop: list[str]


# ── Appro / Destockage ────────────────────────────────────────────────────────

class LigneApproOut(BaseModel):
    commercial_id: int
    dsm_name: str
    nb_appros: int
    montant_appros: float
    nb_destockages: int
    montant_destockages: float


class EvolutionApproReseau(BaseModel):
    mois: str
    montant_appros: float
    montant_destockages: float
    nb_appros: int
    nb_destockages: int


class DetailApproOut(BaseModel):
    id: int
    commercial_id: int
    dsm_name: str
    date_op: str
    type_op: Literal["appro", "destockage"]
    nb_ops: int
    montant: float
    source_fichier: Optional[str] = None


# ── MoM Cash ─────────────────────────────────────────────────────────────────

class LigneCashMoM(BaseModel):
    commercial_id: int
    dsm_name: str
    cash_in_precedent: float
    cash_in: float
    cash_out_precedent: float
    cash_out: float


class CashMoMResponse(BaseModel):
    mois: str
    precedent: str
    lignes: list[LigneCashMoM]


# ── MoM Appro ────────────────────────────────────────────────────────────────

class LigneApproMoM(BaseModel):
    dsm_name: str
    appro_precedent: float
    appro: float
    destoc_precedent: float
    destockage: float


class ApproMoMResponse(BaseModel):
    mois: str
    precedent: str
    lignes: list[LigneApproMoM]


# ── QR Code ───────────────────────────────────────────────────────────────────

class QrAgentOut(BaseModel):
    pos_msisdn: str
    pos_name: str
    dsm_name: str
    segment_group: str
    region: Optional[str] = None
    town: Optional[str] = None
    statut: Literal["actif", "risque", "non_utilise", "sans_qr"]
    last_qr_co_date: Optional[str] = None
    active_deployed: Optional[float] = None
    active_30: int = 0
    days_since_last_use: Optional[int] = None


class RepartitionQr(BaseModel):
    total: int
    par_statut: dict[str, int]
    taux_deploiement: float
    taux_utilisation: float
    taux_non_utilises: float
    taux_risque: float
    taux_sans_qr: float


class RepartitionQrResponse(BaseModel):
    agents: list[QrAgentOut]
    repartition: RepartitionQr


class QrParSegment(BaseModel):
    segment: str
    total: int
    actif: int
    risque: int
    non_utilise: int
    sans_qr: int


class QrParDsm(BaseModel):
    dsm_name: str
    total: int
    actif: int
    risque: int
    non_utilise: int
    sans_qr: int
    taux_utilisation: float


class MouvementQr(BaseModel):
    pos_msisdn: str
    pos_name: str
    dsm_name: str
    segment_group: str
    statut_avant: str
    statut_apres: str


class ComparaisonQrResponse(BaseModel):
    date_a: str
    date_b: str
    repartition_a: RepartitionQr
    repartition_b: RepartitionQr
    par_segment: list[dict]
    mouvements: list[MouvementQr]


# ── Terrain : points touchés ──────────────────────────────────────────────────

class PointToucheCommercial(BaseModel):
    commercial_id: int
    dsm_name: str
    total_points: int
    jours_actifs: int
    moyenne_jour: float


class PointToucheDetail(BaseModel):
    commercial_id: int
    dsm_name: str
    date_op: str
    nb_points: int


class PointsTouchesResponse(BaseModel):
    par_commercial: list[PointToucheCommercial]
    detail: list[PointToucheDetail]


# ── Terrain : clients servis ──────────────────────────────────────────────────

class ClientServiOut(BaseModel):
    msisdn: str
    nom: Optional[str] = None
    nb_transactions: int
    premiere: str
    derniere: str


class ClientsServisResponse(BaseModel):
    lignes: list[ClientServiOut]
    clients_distincts: int
    total_transactions: int


# ── Terrain : réactivité ──────────────────────────────────────────────────────

class ReactiviteOut(BaseModel):
    commercial_id: int
    dsm_name: str
    alias: Optional[str] = None
    nb_transactions: int
    jours_actifs: int
    tx_par_jour: float
    clients_par_jour: float
    temps_mort_median: Optional[float] = None
    temps_mort_max: Optional[float] = None
    temps_recharge_median: Optional[float] = None
    temps_recharge_min: Optional[float] = None


# ── Terrain : portefeuilles ───────────────────────────────────────────────────

class PortefeuilleOut(BaseModel):
    id: int
    commercial_id: int
    dsm_name: str
    nom: str
    date_import: str
    nb_clients: int


class ClientPortefeuilleOut(BaseModel):
    id: int
    portefeuille_id: int
    nom: str
    telephone: Optional[str] = None
    localite: Optional[str] = None


class LigneCouverture(BaseModel):
    msisdn: str
    nom: str
    profil_pos: Optional[str] = None
    nb_contacts: int
    premiere: Optional[str] = None
    derniere: Optional[str] = None


class CouvertureResponse(BaseModel):
    lignes: list[LigneCouverture]
    clients_touches: int
    clients_non_touches: int
    taux_couverture: float
    total_contacts: int


# ── Gestion : historique ──────────────────────────────────────────────────────

class ImportRecordOut(BaseModel):
    id: int
    type_fichier: str
    cle: str
    date_donnees: Optional[str] = None
    chemin_fichier: str
    nb_lignes: Optional[int] = None
    date_execution: str
    fichier_disponible: bool


# ── Gestion : parrainages ─────────────────────────────────────────────────────

class ParrainageOut(BaseModel):
    personne: str
    date_op: str
    nb: int


class ParrainageCreate(BaseModel):
    personne: str
    date_op: str
    nb: int


class ParrainageSyntheseItem(BaseModel):
    personne: str
    total: int


class ParrainagesResponse(BaseModel):
    lignes: list[ParrainageOut]
    synthese: list[ParrainageSyntheseItem]
    total: int


# ── Gestion : suivi personnes ─────────────────────────────────────────────────

class SuiviPersonneOut(BaseModel):
    id: int
    commercial_id: int
    dsm_name: str
    nom_personne: str
    montant: float
    date_heure: str


class SuiviPersonneCreate(BaseModel):
    commercial_id: int
    nom_personne: str
    montant: float
    date_heure: str


class SuiviPersonneSyntheseItem(BaseModel):
    dsm_name: str
    nom_personne: str
    montant: float
    nb_entrees: int


class SuiviPersonnesResponse(BaseModel):
    lignes: list[SuiviPersonneOut]
    synthese: list[SuiviPersonneSyntheseItem]
    montant_total: float
    personnes_distinctes: int


# ── Administration : seuils ───────────────────────────────────────────────────

class SeuilOut(BaseModel):
    id: int
    type_flux: Literal["cash_in", "cash_out"]
    valeur: float
    mois: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class SeuilCreate(BaseModel):
    type_flux: Literal["cash_in", "cash_out"]
    valeur: float
    mois: Optional[str] = None


# ── Administration : utilisateurs ────────────────────────────────────────────

class UtilisateurCreate(BaseModel):
    username: str
    nom: str
    role: Literal["super_admin", "admin", "commercial"]
    mot_de_passe: str
    dsm_name: Optional[str] = None


class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = None
    actif: Optional[bool] = None


class CommercialUpdate(BaseModel):
    telephone: Optional[str] = None
    zone: Optional[str] = None
    dsm_name: Optional[str] = None
    actif: Optional[bool] = None
    alias: Optional[str] = None
