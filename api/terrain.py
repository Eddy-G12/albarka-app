"""
api/terrain.py
==============
Remplace src/services/terrain.ts

Endpoints :
  GET  /terrain/points-touches          → synthèse + détail points touchés
  GET  /terrain/clients-servis          → clients servis par commercial
  GET  /terrain/reactivite              → indicateurs de réactivité
  GET  /terrain/portefeuilles           → liste des portefeuilles
  GET  /terrain/portefeuilles/{id}      → clients d'un portefeuille
  POST /terrain/portefeuilles/{id}/couverture  → calcul de couverture (CSV brut)
"""

from __future__ import annotations
import re
import io
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from fastapi import APIRouter, Query, HTTPException, UploadFile, File

from core import db
from api.deps import RequireAdmin, RequireAll
from api.schemas import (
    PointToucheCommercial, PointsTouchesResponse, PointToucheDetail,
    ClientServiOut, ClientsServisResponse,
    ReactiviteOut,
    PortefeuilleOut, ClientPortefeuilleOut,
    LigneCouverture, CouvertureResponse,
)

router = APIRouter(prefix="/terrain", tags=["Terrain"])

EXCLUDED = {"ALBARKA GN SARL", "ALBARKA GN SARL 5"}


# ── Points touchés ────────────────────────────────────────────────────────────

@router.get("/points-touches", response_model=PointsTouchesResponse)
def points_touches(
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Synthèse et détail journalier des points touchés par commercial."""
    commerciaux = db.list_commerciaux()
    if commercial_id:
        commerciaux = [c for c in commerciaux if c["id"] == commercial_id]

    par_commercial: list[PointToucheCommercial] = []
    detail: list[PointToucheDetail] = []

    for com in commerciaux:
        servis = db.list_clients_servis(com["id"])
        if not servis:
            continue
        par_date: dict[str, int] = {}
        for s in servis:
            d = s.get("premiere_date") or s.get("date_op") or "—"
            par_date[d] = par_date.get(d, 0) + s["nb_total"]

        total     = sum(par_date.values())
        jours     = len(par_date)
        moyenne   = round(total / jours, 1) if jours else 0.0

        par_commercial.append(PointToucheCommercial(
            commercial_id=com["id"],
            dsm_name=com["dsm_name"],
            total_points=total,
            jours_actifs=jours,
            moyenne_jour=moyenne,
        ))
        for d_op, nb in par_date.items():
            detail.append(PointToucheDetail(
                commercial_id=com["id"],
                dsm_name=com["dsm_name"],
                date_op=d_op,
                nb_points=nb,
            ))

    detail.sort(key=lambda x: x.date_op, reverse=True)
    return PointsTouchesResponse(par_commercial=par_commercial, detail=detail)


# ── Clients servis ────────────────────────────────────────────────────────────

@router.get("/clients-servis", response_model=ClientsServisResponse)
def clients_servis(
    commercial_id: Optional[int] = Query(None),
    du:  Optional[str] = Query(None),
    au:  Optional[str] = Query(None),
    _: RequireAll = None,
):
    """Historique des clients servis par un commercial sur une période."""
    lignes_db = db.list_clients_servis(commercial_id, date_debut=du, date_fin=au)
    lignes = [
        ClientServiOut(
            msisdn=l["msisdn_contrepartie"],
            nom=l.get("nom_contrepartie"),
            nb_transactions=l["nb_total"],
            premiere=l.get("premiere_date") or "",
            derniere=l.get("derniere_date") or "",
        )
        for l in lignes_db
    ]
    return ClientsServisResponse(
        lignes=lignes,
        clients_distincts=len(lignes),
        total_transactions=sum(l.nb_transactions for l in lignes),
    )


# ── Réactivité ────────────────────────────────────────────────────────────────

@router.get("/reactivite", response_model=list[ReactiviteOut])
def reactivite(_: RequireAdmin = None):
    """
    Indicateurs de réactivité depuis la table clients_servis.
    Note : temps mort et recharge nécessitent un re-calcul depuis les CSV bruts
    (voir POST /terrain/reactivite/calcul).
    Les valeurs retournées ici sont les agrégats disponibles en base.
    """
    commerciaux = db.list_commerciaux()
    result = []
    for com in commerciaux:
        servis = db.list_clients_servis(com["id"])
        if not servis:
            continue
        nb_tx    = sum(s["nb_total"] for s in servis)
        jours    = len(set(s.get("premiere_date","") for s in servis if s.get("premiere_date")))
        tx_jour  = round(nb_tx / jours, 2) if jours else 0.0
        cl_jour  = round(len(servis) / jours, 2) if jours else 0.0
        result.append(ReactiviteOut(
            commercial_id=com["id"],
            dsm_name=com["dsm_name"],
            alias=com.get("alias_csv"),
            nb_transactions=nb_tx,
            jours_actifs=jours,
            tx_par_jour=tx_jour,
            clients_par_jour=cl_jour,
            temps_mort_median=None,
            temps_mort_max=None,
            temps_recharge_median=None,
            temps_recharge_min=None,
        ))
    return result


class ReactiviteCalcResponse(ReactiviteOut):
    pass


@router.post("/reactivite/calcul", response_model=list[ReactiviteCalcResponse])
async def calcul_reactivite(
    fichiers: list[UploadFile] = File(...),
    _: RequireAdmin = None,
):
    """
    Calcule les indicateurs de réactivité depuis les CSV bruts MTN uploadés.
    Correspond à la page Réactivité Commerciale du frontend.
    """
    import numpy as np

    alias_map  = db.get_alias_map()
    com_by_dsm = {c["dsm_name"].upper(): c for c in db.list_commerciaux()}
    EXCLUDED   = {"ALBARKA GN SARL", "ALBARKA GN SARL 5"}

    result = []

    for upload in fichiers:
        raw = await upload.read()
        try:
            df = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"{upload.filename} : {e}")

        df.columns = df.columns.str.strip()
        if "Status" in df.columns:
            df = df[df["Status"].str.strip() == "Successful"]
        if "Type" in df.columns:
            df = df[df["Type"].str.strip() == "Transfer"]
        if "From name" in df.columns:
            df = df[~df["From name"].isin(EXCLUDED)]
        if "To name" in df.columns:
            df = df[~df["To name"].isin(EXCLUDED)]
        if "Date" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        if "Amount" in df.columns:
            df["Amount"] = pd.to_numeric(
                df["Amount"].astype(str).str.replace(r"[\s,]", "", regex=True),
                errors="coerce",
            ).fillna(0)
        if "Balance" in df.columns:
            df["Balance"] = pd.to_numeric(
                df["Balance"].astype(str).str.replace(r"[\s,]", "", regex=True),
                errors="coerce",
            )

        # Détecter l'alias
        alias = None
        if "From name" in df.columns and "To name" in df.columns:
            names = (
                set(df["From name"].str.strip().str.upper().dropna())
                | set(df["To name"].str.strip().str.upper().dropna())
            )
            for a_up, info in alias_map.items():
                if a_up in names:
                    alias = info["alias"]
                    com   = com_by_dsm.get(info["dsm_name"].upper())
                    break
        if not alias:
            continue

        alias_upper = alias.strip().upper()
        mask = (
            df["From name"].str.strip().str.upper() == alias_upper
        ) | (
            df["To name"].str.strip().str.upper() == alias_upper
        )
        df_own = df[mask].copy().sort_values("Date")
        if df_own.empty:
            continue

        def _cp(row):
            return row["To name"].strip() if row["From name"].strip().upper() == alias_upper else row["From name"].strip()

        df_own["_cp"]   = df_own.apply(_cp, axis=1)
        df_own["_date"] = df_own["Date"].dt.date

        nb_tx  = len(df_own)
        jours  = df_own["_date"].nunique()
        tx_j   = round(nb_tx / jours, 2) if jours else 0.0
        cl_j   = round(df_own.groupby("_date")["_cp"].nunique().mean(), 2)

        ecarts = []
        for _, grp in df_own.groupby("_date"):
            if len(grp) < 2:
                continue
            ts = grp["Date"].sort_values()
            diffs = ts.diff().dropna().dt.total_seconds() / 60
            ecarts.extend(diffs.tolist())

        tm_med = round(float(np.median(ecarts)), 1) if ecarts else None
        tm_max = round(float(max(ecarts)),        1) if ecarts else None

        tr_med = tr_min = None
        if "Balance" in df_own.columns:
            df_bal = df_own.dropna(subset=["Balance"]).reset_index(drop=True)
            recharges = []
            j = 0
            while j < len(df_bal) - 1:
                if df_bal.iloc[j]["Balance"] < 100_000:
                    k = j + 1
                    while k < len(df_bal) and df_bal.iloc[k]["Balance"] < 100_000:
                        k += 1
                    if k < len(df_bal):
                        dur = (df_bal.iloc[k]["Date"] - df_bal.iloc[j]["Date"]).total_seconds() / 60
                        if dur > 0:
                            recharges.append(dur)
                    j = k + 1
                else:
                    j += 1
            if recharges:
                tr_med = round(float(np.median(recharges)), 1)
                tr_min = round(float(min(recharges)),       1)

        result.append(ReactiviteCalcResponse(
            commercial_id=com["id"] if com else 0,
            dsm_name=com["dsm_name"] if com else alias,
            alias=alias,
            nb_transactions=nb_tx,
            jours_actifs=jours,
            tx_par_jour=tx_j,
            clients_par_jour=cl_j,
            temps_mort_median=tm_med,
            temps_mort_max=tm_max,
            temps_recharge_median=tr_med,
            temps_recharge_min=tr_min,
        ))

    return result


# ── Portefeuilles ──────────────────────────────────────────────────────────────

@router.get("/portefeuilles", response_model=list[PortefeuilleOut])
def liste_portefeuilles(
    commercial_id: Optional[int] = Query(None),
    _: RequireAll = None,
):
    """Liste des portefeuilles, filtrables par commercial."""
    pfs = db.list_portefeuilles(commercial_id=commercial_id)
    return [
        PortefeuilleOut(
            id=p["id"],
            commercial_id=p["commercial_id"],
            dsm_name=p["dsm_name"],
            nom=p["nom"],
            date_import=p["date_import"],
            nb_clients=p["nb_clients"],
        )
        for p in pfs
    ]


@router.get("/portefeuilles/{portefeuille_id}/clients", response_model=list[ClientPortefeuilleOut])
def clients_portefeuille(
    portefeuille_id: int,
    _: RequireAll = None,
):
    """Clients d'un portefeuille."""
    clients = db.list_clients(portefeuille_id)
    return [
        ClientPortefeuilleOut(
            id=c["id"],
            portefeuille_id=c["portefeuille_id"],
            nom=c["nom"],
            telephone=c.get("telephone"),
            localite=c.get("localite"),
        )
        for c in clients
    ]


@router.post("/portefeuilles/{portefeuille_id}/couverture", response_model=CouvertureResponse)
async def couverture_portefeuille(
    portefeuille_id: int,
    fichiers: list[UploadFile] = File(...),
    _: RequireAll = None,
):
    """
    Calcule la couverture d'un portefeuille depuis les CSV bruts MTN.
    Rapprochement par MSISDN (FRI:237XXXXXXXXX/MSISDN).
    """
    clients_pf = db.list_clients(portefeuille_id)
    if not clients_pf:
        raise HTTPException(404, "Portefeuille vide ou introuvable.")

    pf = db.get_portefeuille(portefeuille_id)
    alias = db.get_alias(pf["commercial_id"]) if pf else None
    alias_upper = alias.strip().upper() if alias else None

    msisdn_index: dict[str, dict] = {}
    for c in clients_pf:
        tel = re.sub(r"[^0-9]", "", str(c.get("telephone") or ""))
        if tel:
            msisdn_index[tel] = c

    def _extract_msisdn(val: str) -> str:
        m = re.search(r"(\d{9,12})/MSISDN", str(val))
        return m.group(1) if m else ""

    contacts: dict[str, dict] = {}

    for upload in fichiers:
        raw = await upload.read()
        try:
            df = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception:
            continue
        df.columns = df.columns.str.strip()
        if "Type" in df.columns:
            df = df[df["Type"].str.strip() == "Transfer"]
        if "From" not in df.columns or "To" not in df.columns:
            continue

        for _, row in df.iterrows():
            mf = _extract_msisdn(str(row.get("From", "")))
            mt = _extract_msisdn(str(row.get("To",   "")))
            nf = str(row.get("From name", "")).strip()
            nt = str(row.get("To name",   "")).strip()
            dt = str(row.get("Date", "")).strip()[:10]

            if alias_upper:
                if nf.upper() == alias_upper:
                    cp_msisdn = mt
                elif nt.upper() == alias_upper:
                    cp_msisdn = mf
                else:
                    continue
            else:
                cp_msisdn = mt if mf in msisdn_index else (mf if mt in msisdn_index else None)
                if not cp_msisdn:
                    continue

            if cp_msisdn and cp_msisdn in msisdn_index:
                if cp_msisdn not in contacts:
                    contacts[cp_msisdn] = {"nb": 0, "dates": []}
                contacts[cp_msisdn]["nb"] += 1
                if dt:
                    contacts[cp_msisdn]["dates"].append(dt)

    lignes: list[LigneCouverture] = []
    for c in clients_pf:
        tel  = re.sub(r"[^0-9]", "", str(c.get("telephone") or ""))
        data = contacts.get(tel, {})
        nb   = data.get("nb", 0)
        dates = sorted(data.get("dates", []))
        lignes.append(LigneCouverture(
            msisdn=tel or c.get("nom", ""),
            nom=c.get("nom", ""),
            profil_pos=c.get("localite"),
            nb_contacts=nb,
            premiere=dates[0]  if dates else None,
            derniere=dates[-1] if dates else None,
        ))

    touches     = sum(1 for l in lignes if l.nb_contacts > 0)
    non_touches = len(lignes) - touches
    taux        = touches / len(lignes) * 100 if lignes else 0
    total       = sum(l.nb_contacts for l in lignes)

    return CouvertureResponse(
        lignes=lignes,
        clients_touches=touches,
        clients_non_touches=non_touches,
        taux_couverture=round(taux, 1),
        total_contacts=total,
    )
