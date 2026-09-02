"""
api/qr.py
=========
Remplace src/services/qr.ts

Endpoints :
  GET /qr/dates                 → dates disponibles (cache CSV)
  GET /qr/repartition           → agents + métriques pour une date
  GET /qr/segments              → répartition par segment
  GET /qr/dsm                   → répartition par DSM
  GET /qr/prioritaires          → agents non actifs (à traiter)
  GET /qr/comparaison           → comparaison entre 2 dates (mouvements)
  GET /qr/mom                   → MoM QR Code (stats M vs M-1)
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from fastapi import APIRouter, Query, HTTPException

from core import db
from api.deps import RequireAdmin, RequireAll
from api.schemas import (
    QrAgentOut, RepartitionQr, RepartitionQrResponse,
    QrParSegment, QrParDsm, MouvementQr, ComparaisonQrResponse,
)

router = APIRouter(prefix="/qr", tags=["QR Code"])

CACHE_DIR = db.DATA_DIR / "qr_code" / "_cache"
STATUT_ORDER = ["sans_qr", "non_utilise", "risque", "actif"]

# Correspondance entre les valeurs string du cache et les littéraux TypeScript
STATUT_MAP = {
    "Sans QR Code":          "sans_qr",
    "QR non utilisé (+30j)": "non_utilise",
    "Risque inactivité":     "risque",
    "Actif":                 "actif",
}


def _dates_disponibles() -> list[str]:
    imports = db.list_imports("qr_code")
    return sorted(
        [imp["cle"] for imp in imports if (CACHE_DIR / f"{imp['cle']}.csv").exists()],
        reverse=True,
    )


def _load_cache(date_iso: str) -> pd.DataFrame:
    path = CACHE_DIR / f"{date_iso}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Cache QR introuvable pour {date_iso}")
    return pd.read_csv(path, dtype={"pos_msisdn": str})


def _agent_to_out(row: dict) -> QrAgentOut:
    statut_raw = row.get("statut", "Actif")
    statut_ts  = STATUT_MAP.get(statut_raw, "actif")
    return QrAgentOut(
        pos_msisdn=str(row.get("pos_msisdn", "")),
        pos_name=str(row.get("pos_name", "")),
        dsm_name=str(row.get("dsm_name", "")),
        segment_group=str(row.get("segment_group", "")),
        region=str(row["region"]) if pd.notna(row.get("region")) else "",
        town=str(row["town"]) if pd.notna(row.get("town")) else "",
        statut=statut_ts,
        last_qr_co_date=str(row["last_qr_co_date"]) if pd.notna(row.get("last_qr_co_date")) else None,
        active_deployed=float(row["active_deployed"]) if pd.notna(row.get("active_deployed")) else None,
        active_30=int(row.get("active_30", 0)) if pd.notna(row.get("active_30")) else 0,
        days_since_last_use=int(row["days_since_last_use"]) if pd.notna(row.get("days_since_last_use")) else None,
    )


def _calc_repartition(agents: list[QrAgentOut]) -> RepartitionQr:
    total = len(agents) or 1
    par_statut = {s: 0 for s in STATUT_ORDER}
    for a in agents:
        par_statut[a.statut] = par_statut.get(a.statut, 0) + 1
    deployes = total - par_statut["sans_qr"]
    return RepartitionQr(
        total=len(agents),
        par_statut=par_statut,
        taux_deploiement=deployes / total * 100,
        taux_utilisation=par_statut["actif"] / total * 100,
        taux_non_utilises=par_statut["non_utilise"] / total * 100,
        taux_risque=par_statut["risque"] / total * 100,
        taux_sans_qr=par_statut["sans_qr"] / total * 100,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/dates", response_model=list[str])
def dates_qr(_: RequireAll = None):
    """Dates disponibles dans le cache QR Code."""
    return _dates_disponibles()


@router.get("/repartition", response_model=RepartitionQrResponse)
def repartition_qr(
    date_ref: str = Query(..., description="Date ISO AAAA-MM-JJ"),
    dsm_name: Optional[str] = Query(None),
    _: RequireAll = None,
):
    """Répartition des agents par statut QR pour une date de référence."""
    df = _load_cache(date_ref)
    if dsm_name:
        df = df[df["dsm_name"] == dsm_name]
    agents = [_agent_to_out(row) for row in df.to_dict("records")]
    return RepartitionQrResponse(agents=agents, repartition=_calc_repartition(agents))


@router.get("/segments", response_model=list[QrParSegment])
def qr_par_segment(
    date_ref: str = Query(...),
    dsm_name: Optional[str] = Query(None),
    _: RequireAll = None,
):
    """Répartition par segment_group."""
    df = _load_cache(date_ref)
    if dsm_name:
        df = df[df["dsm_name"] == dsm_name]
    segments = sorted(df["segment_group"].dropna().unique())
    result = []
    for seg in segments:
        sub = df[df["segment_group"] == seg]
        agents = [_agent_to_out(r) for r in sub.to_dict("records")]
        rep = _calc_repartition(agents)
        result.append(QrParSegment(
            segment=seg,
            total=len(agents),
            actif=rep.par_statut["actif"],
            risque=rep.par_statut["risque"],
            non_utilise=rep.par_statut["non_utilise"],
            sans_qr=rep.par_statut["sans_qr"],
        ))
    return result


@router.get("/dsm", response_model=list[QrParDsm])
def qr_par_dsm(
    date_ref: str = Query(...),
    _: RequireAdmin = None,
):
    """Répartition par DSM, triée par nb d'agents actifs décroissant."""
    df = _load_cache(date_ref)
    dsm_list = sorted(df["dsm_name"].dropna().unique())
    result = []
    for dsm in dsm_list:
        sub = df[df["dsm_name"] == dsm]
        agents = [_agent_to_out(r) for r in sub.to_dict("records")]
        rep = _calc_repartition(agents)
        result.append(QrParDsm(
            dsm_name=dsm,
            total=len(agents),
            actif=rep.par_statut["actif"],
            risque=rep.par_statut["risque"],
            non_utilise=rep.par_statut["non_utilise"],
            sans_qr=rep.par_statut["sans_qr"],
            taux_utilisation=rep.taux_utilisation,
        ))
    return sorted(result, key=lambda x: x.actif, reverse=True)


@router.get("/prioritaires", response_model=list[QrAgentOut])
def agents_prioritaires(
    date_ref: str = Query(...),
    dsm_name: Optional[str] = Query(None),
    _: RequireAll = None,
):
    """Agents non actifs (Sans QR, Non utilisé, Risque inactivité)."""
    df = _load_cache(date_ref)
    if dsm_name:
        df = df[df["dsm_name"] == dsm_name]
    df = df[df["statut"] != "Actif"]
    return [_agent_to_out(r) for r in df.to_dict("records")]


@router.get("/comparaison", response_model=ComparaisonQrResponse)
def comparaison_qr(
    date_a: str = Query(..., description="Date antérieure"),
    date_b: str = Query(..., description="Date récente"),
    _: RequireAdmin = None,
):
    """Comparaison entre deux dates QR : mouvements de statuts détaillés."""
    df_a = _load_cache(date_a)
    df_b = _load_cache(date_b)

    agents_a = {r["pos_msisdn"]: _agent_to_out(r) for r in df_a.to_dict("records")}
    agents_b = {r["pos_msisdn"]: _agent_to_out(r) for r in df_b.to_dict("records")}

    mouvements = [
        MouvementQr(
            pos_msisdn=msisdn,
            pos_name=b.pos_name,
            dsm_name=b.dsm_name,
            segment_group=b.segment_group,
            statut_avant=agents_a[msisdn].statut,
            statut_apres=b.statut,
        )
        for msisdn, b in agents_b.items()
        if msisdn in agents_a and agents_a[msisdn].statut != b.statut
    ]

    segments = sorted(df_b["segment_group"].dropna().unique())
    par_segment = [
        {
            "segment": seg,
            "avant": int((df_a["segment_group"] == seg).sum()),
            "apres": int((df_b["segment_group"] == seg).sum()),
        }
        for seg in segments
    ]

    list_a = list(agents_a.values())
    list_b = list(agents_b.values())

    return ComparaisonQrResponse(
        date_a=date_a,
        date_b=date_b,
        repartition_a=_calc_repartition(list_a),
        repartition_b=_calc_repartition(list_b),
        par_segment=par_segment,
        mouvements=mouvements,
    )


@router.get("/mom")
def qr_mom(
    date_m1: str = Query(..., description="Date antérieure M-1"),
    date_m: str  = Query(..., description="Date récente M"),
    dsm_name: Optional[str] = Query(None),
    _: RequireAll = None,
):
    """MoM QR : évolution des KPIs entre deux dates."""
    df_m1 = _load_cache(date_m1)
    df_m  = _load_cache(date_m)
    if dsm_name:
        df_m1 = df_m1[df_m1["dsm_name"] == dsm_name]
        df_m  = df_m[df_m["dsm_name"]   == dsm_name]

    rep_m1 = _calc_repartition([_agent_to_out(r) for r in df_m1.to_dict("records")])
    rep_m  = _calc_repartition([_agent_to_out(r) for r in df_m.to_dict("records")])

    return {
        "date_m1":          date_m1,
        "date_m":           date_m,
        "repartition_m1":   rep_m1,
        "repartition_m":    rep_m,
    }
