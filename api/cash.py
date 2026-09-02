"""
api/cash.py
===========
Remplace src/services/cash.ts

Endpoints :
  GET  /cash/commercial           → cash in/out par commercial pour un mois
  GET  /cash/commercial/evolution → évolution mensuelle réseau
  GET  /cash/alertes-commercial   → alertes seuil (commerciaux)
  GET  /cash/pos                  → cashflow POS pour un mois (source SAE)
  GET  /cash/pos/classement       → Top/Flop N POS
  GET  /cash/pos/alertes          → alertes seuil POS
  POST /cash/pos/mom              → comparaison multi-mois POS
  GET  /cash/appro                → appro/destockage par commercial
  GET  /cash/appro/evolution      → évolution mensuelle appro réseau
  GET  /cash/appro/detail         → détail journalier appro
  GET  /cash/mom                  → MoM cash commercial
  GET  /cash/appro/mom            → MoM appro commercial
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core import db
from core.appro import get_appro_par_mois, get_appro, get_mois_disponibles_appro
from api.deps import RequireAdmin, RequireAll
from api.schemas import (
    LigneCashCommercial, EvolutionCashReseau, AlertesSeuilResponse, AlerteSeuilCommercial,
    CashflowPosOut, ClassementPosResponse, AlerteSeuilPos, AlertesSeuilPosResponse,
    ComparaisonMoMPos, LigneApproOut, EvolutionApproReseau, DetailApproOut,
    CashMoMResponse, LigneCashMoM, ApproMoMResponse, LigneApproMoM,
)

router = APIRouter(prefix="/cash", tags=["Cash Flow"])


def _mois_precedent(mois: str) -> str:
    dt = datetime.strptime(mois + "-01", "%Y-%m-%d")
    if dt.month == 1:
        return f"{dt.year - 1}-12"
    return f"{dt.year}-{dt.month - 1:02d}"


# ── Cash commercial ────────────────────────────────────────────────────────────

@router.get("/commercial", response_model=list[LigneCashCommercial])
def cash_par_commercial(
    mois: str = Query(..., description="Format AAAA-MM"),
    _: RequireAdmin = None,
):
    """Retourne le cash in/out par commercial pour un mois (table transactions_momo)."""
    from core.cashflow import get_cashflow
    lignes = get_cashflow(mois=mois)
    return [
        LigneCashCommercial(
            commercial_id=r["commercial_id"],
            dsm_name=r["dsm_name"],
            cash_in=r["cash_in"],
            cash_out=r["cash_out"],
            nb_transactions=r["nb_transactions"],
        )
        for r in lignes
    ]


@router.get("/commercial/evolution", response_model=list[EvolutionCashReseau])
def evolution_cash_reseau(_: RequireAdmin = None):
    """Évolution mensuelle agrégée réseau."""
    from core.cashflow import get_cashflow
    conn = db.get_connection()
    mois_list = [
        r["mois"]
        for r in conn.execute(
            "SELECT DISTINCT mois FROM transactions_momo ORDER BY mois"
        ).fetchall()
    ]
    conn.close()
    result = []
    for mois in mois_list:
        lignes = get_cashflow(mois=mois)
        result.append(EvolutionCashReseau(
            mois=mois,
            cash_in=sum(r["cash_in"] for r in lignes),
            cash_out=sum(r["cash_out"] for r in lignes),
        ))
    return result


@router.get("/alertes-commercial", response_model=AlertesSeuilResponse)
def alertes_seuil_commercial(
    mois: str = Query(..., description="Format AAAA-MM"),
    _: RequireAdmin = None,
):
    """Alertes seuil cash in/out pour les commerciaux."""
    from core.cashflow import list_alertes_seuil
    data = list_alertes_seuil(mois)
    seuil_in  = data.get("seuil_cash_in")  or 0
    seuil_out = data.get("seuil_cash_out") or 0

    lignes = []
    for r in data.get("commerciaux_sous_seuil_cash_in", []):
        lignes.append(AlerteSeuilCommercial(
            commercial_id=r["commercial_id"], dsm_name=r["dsm_name"],
            cash_in=r["cash_in"], cash_out=r["cash_out"],
            nb_transactions=r.get("nb_transactions", 0),
            ecart_in=r["cash_in"] - seuil_in, ecart_out=0,
        ))
    for r in data.get("commerciaux_sous_seuil_cash_out", []):
        exist = next((l for l in lignes if l.commercial_id == r["commercial_id"]), None)
        if exist:
            exist.ecart_out = r["cash_out"] - seuil_out
        else:
            lignes.append(AlerteSeuilCommercial(
                commercial_id=r["commercial_id"], dsm_name=r["dsm_name"],
                cash_in=r["cash_in"], cash_out=r["cash_out"],
                nb_transactions=r.get("nb_transactions", 0),
                ecart_in=0, ecart_out=r["cash_out"] - seuil_out,
            ))
    return AlertesSeuilResponse(seuil_in=seuil_in, seuil_out=seuil_out, lignes=lignes)


# ── Cash Flow POS ──────────────────────────────────────────────────────────────

def _pos_to_out(r: dict) -> CashflowPosOut:
    return CashflowPosOut(
        pos_id=r.get("pos_id", 0),
        acceptor_id=r["acceptorid"],
        agent_name=r.get("agent_name") or "",
        agent_msisdn=r.get("agent_msisdn") or "",
        mois=r["mois"],
        cash_in=r["cash_in"],
        cash_out=r["cash_out"],
    )


@router.get("/pos", response_model=list[CashflowPosOut])
def cashflow_pos(
    mois: str = Query(..., description="Format AAAA-MM"),
    _: RequireAdmin = None,
):
    """Cashflow de tous les POS pour un mois (source SAE MTN)."""
    return [_pos_to_out(r) for r in db.get_cashflow_pos(mois)]


@router.get("/pos/mois", response_model=list[str])
def mois_cashflow_pos(_: RequireAdmin = None):
    """Liste des mois disponibles dans cashflow_pos."""
    return db.list_mois_cashflow_pos()


@router.get("/pos/classement", response_model=ClassementPosResponse)
def classement_pos(
    mois: str = Query(...),
    flux: str = Query("cash_in", description="cash_in ou cash_out"),
    n: int = Query(20, ge=1, le=100),
    _: RequireAdmin = None,
):
    """Top N et Flop N des POS pour un mois et un type de flux."""
    if flux not in ("cash_in", "cash_out"):
        flux = "cash_in"
    top  = [_pos_to_out(r) for r in db.top_flop_pos(mois, flux, n=n, ordre="top")]
    flop = [_pos_to_out(r) for r in db.top_flop_pos(mois, flux, n=n, ordre="flop")]
    total = len(db.get_cashflow_pos(mois))
    return ClassementPosResponse(top=top, flop=flop, total=total)


@router.get("/pos/alertes", response_model=AlertesSeuilPosResponse)
def alertes_seuil_pos(
    mois: str = Query(...),
    _: RequireAdmin = None,
):
    """Alertes seuil cash in/out pour les POS."""
    from core.cashflow import list_alertes_seuil_pos
    data = list_alertes_seuil_pos(mois)
    seuil_in  = data.get("seuil_cash_in")  or 0
    seuil_out = data.get("seuil_cash_out") or 0

    def _to_alerte(r: dict, flux: str) -> AlerteSeuilPos:
        return AlerteSeuilPos(
            pos_id=r.get("pos_id", 0),
            acceptor_id=r["acceptorid"],
            agent_name=r.get("agent_name") or "",
            agent_msisdn=r.get("agent_msisdn") or "",
            mois=mois,
            cash_in=r["cash_in"],
            cash_out=r["cash_out"],
            ecart_in=r["cash_in"] - seuil_in,
            ecart_out=r["cash_out"] - seuil_out,
        )

    lignes = [
        _to_alerte(r, "cash_in")
        for r in data.get("pos_sous_seuil_cash_in", [])
        + data.get("pos_sous_seuil_cash_out", [])
    ]
    return AlertesSeuilPosResponse(seuil_in=seuil_in, seuil_out=seuil_out, lignes=lignes)


class MoMListe(BaseModel):
    mois: list[str]


@router.post("/pos/mom", response_model=ComparaisonMoMPos)
def comparaison_mom_pos(body: MoMListe, _: RequireAdmin = None):
    """Comparaison multi-mois POS : Top20/Flop10/Cumulé/Constants."""
    from core.cashflow import compute_mom_multi

    fichiers = [
        {"source": b"", "nom_fichier": "", "mois": m}
        for m in body.mois
    ]
    # compute_mom_multi attend des fichiers bruts — ici on passe directement
    # les données déjà en base via get_cashflow_pos
    top_par_mois: dict = {}
    flop_par_mois: dict = {}
    cumul: dict = {}

    for mois in body.mois:
        lignes = sorted(db.get_cashflow_pos(mois), key=lambda x: x["cash_in"], reverse=True)
        top_par_mois[mois]  = [_pos_to_out(r) for r in lignes[:20]]
        flop_par_mois[mois] = [_pos_to_out(r) for r in lignes[-10:][::-1]]
        for r in lignes:
            cle = r["acceptorid"]
            if cle not in cumul:
                cumul[cle] = {"agent_name": r.get("agent_name",""), "cumul": 0}
            cumul[cle]["cumul"] += r["cash_in"]

    top_cumule = sorted(
        [{"acceptor_id": k, "agent_name": v["agent_name"], "cumul": v["cumul"]}
         for k, v in cumul.items()],
        key=lambda x: x["cumul"], reverse=True,
    )[:10]

    def _ids(source: dict) -> list[str]:
        sets = [set(p.acceptor_id for p in lst) for lst in source.values()]
        if not sets:
            return []
        result = sets[0]
        for s in sets[1:]:
            result &= s
        return list(result)

    return ComparaisonMoMPos(
        mois=body.mois,
        top_par_mois=top_par_mois,
        flop_par_mois=flop_par_mois,
        top_cumule=top_cumule,
        constants_top=_ids(top_par_mois),
        constants_flop=_ids(flop_par_mois),
    )


# ── Appro / Destockage ─────────────────────────────────────────────────────────

@router.get("/appro", response_model=list[LigneApproOut])
def appro_par_commercial(
    mois: str = Query(...),
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Appro/destockage agrégés par commercial pour un mois."""
    lignes = get_appro_par_mois(mois=mois)
    if commercial_id:
        lignes = [l for l in lignes if l["commercial_id"] == commercial_id]
    return [
        LigneApproOut(
            commercial_id=l.get("commercial_id", 0),
            dsm_name=l["dsm_name"],
            nb_appros=l["nb_appro"],
            montant_appros=l["montant_appro"],
            nb_destockages=l["nb_destockage"],
            montant_destockages=l["montant_destockage"],
        )
        for l in lignes
    ]


@router.get("/appro/mois", response_model=list[str])
def mois_appro(_: RequireAll = None):
    """Liste des mois disponibles pour l'appro/destockage."""
    return get_mois_disponibles_appro()


@router.get("/appro/evolution", response_model=list[EvolutionApproReseau])
def evolution_appro(
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Évolution mensuelle appro/destockage."""
    mois_list = get_mois_disponibles_appro()
    result = []
    for mois in mois_list:
        lignes = get_appro_par_mois(mois=mois)
        if commercial_id:
            lignes = [l for l in lignes if l.get("commercial_id") == commercial_id]
        result.append(EvolutionApproReseau(
            mois=mois,
            montant_appros=sum(l["montant_appro"] for l in lignes),
            montant_destockages=sum(l["montant_destockage"] for l in lignes),
            nb_appros=sum(l["nb_appro"] for l in lignes),
            nb_destockages=sum(l["nb_destockage"] for l in lignes),
        ))
    return result


@router.get("/appro/detail", response_model=list[DetailApproOut])
def detail_appro(
    commercial_id: Optional[int] = Query(None),
    mois: Optional[str] = Query(None),
    type_op: Optional[str] = Query(None),
    _: RequireAll = None,
):
    """Détail journalier appro/destockage filtrable."""
    from core.appro import get_appro_par_jour
    lignes = get_appro_par_jour(commercial_id=commercial_id, mois=mois)
    if type_op:
        lignes = [l for l in lignes if l["type_op"] == type_op]
    return [
        DetailApproOut(
            id=l["id"],
            commercial_id=l["commercial_id"],
            dsm_name=l["dsm_name"],
            date_op=l["date_op"],
            type_op=l["type_op"],
            nb_ops=l["nb_ops"] or 0,
            montant=l["montant"],
            source_fichier=l.get("source_fichier"),
        )
        for l in lignes
    ]


# ── MoM ────────────────────────────────────────────────────────────────────────

@router.get("/mom", response_model=CashMoMResponse)
def cash_mom(
    mois: str = Query(...),
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Cash MoM : comparaison mois M vs M-1."""
    from core.cashflow import get_cashflow
    precedent = _mois_precedent(mois)
    actuel    = {r["commercial_id"]: r for r in get_cashflow(mois=mois)}
    anterieur = {r["commercial_id"]: r for r in get_cashflow(mois=precedent)}

    ids = set(actuel) | set(anterieur)
    if commercial_id:
        ids = {commercial_id}

    lignes = []
    for cid in ids:
        a = actuel.get(cid, {})
        b = anterieur.get(cid, {})
        dsm = a.get("dsm_name") or b.get("dsm_name") or "—"
        lignes.append(LigneCashMoM(
            commercial_id=cid,
            dsm_name=dsm,
            cash_in_precedent=b.get("cash_in", 0),
            cash_in=a.get("cash_in", 0),
            cash_out_precedent=b.get("cash_out", 0),
            cash_out=a.get("cash_out", 0),
        ))
    return CashMoMResponse(mois=mois, precedent=precedent, lignes=lignes)


@router.get("/appro/mom", response_model=ApproMoMResponse)
def appro_mom(
    mois: str = Query(...),
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Appro MoM : comparaison mois M vs M-1."""
    precedent = _mois_precedent(mois)
    actuel    = {l["dsm_name"]: l for l in get_appro_par_mois(mois=mois)}
    anterieur = {l["dsm_name"]: l for l in get_appro_par_mois(mois=precedent)}

    noms = set(actuel) | set(anterieur)
    lignes = []
    for nom in noms:
        a = actuel.get(nom, {})
        b = anterieur.get(nom, {})
        if commercial_id:
            cid = a.get("commercial_id") or b.get("commercial_id")
            if cid != commercial_id:
                continue
        lignes.append(LigneApproMoM(
            dsm_name=nom,
            appro_precedent=b.get("montant_appro", 0),
            appro=a.get("montant_appro", 0),
            destoc_precedent=b.get("montant_destockage", 0),
            destockage=a.get("montant_destockage", 0),
        ))
    return ApproMoMResponse(mois=mois, precedent=precedent, lignes=lignes)
