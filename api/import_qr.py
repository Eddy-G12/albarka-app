"""
api/import_qr.py
================
POST /import/qr

Remplace pages/2_Suivi_QR_Code.py (onglet import).

Pipeline :
  1. Lire le fichier XLSX ou GZ QR Code (read_qr_file)
  2. Classifier les agents selon la date de référence (classify)
  3. Générer le rapport Excel (build_report_workbook) → sauvé sur disque
  4. Sauvegarder le cache CSV → data/qr_code/_cache/{date_iso}.csv
  5. Persister l'historique d'import (table imports)
  6. Retourner un résumé JSON
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from core import db
from core.qr_code import read_qr_file, classify, build_report_workbook
from api.deps import RequireSuperAdmin

router = APIRouter(prefix="/import", tags=["Import"])

CACHE_QR_DIR = db.DATA_DIR / "qr_code" / "_cache"
CACHE_QR_DIR.mkdir(parents=True, exist_ok=True)

CACHE_COLUMNS = [
    "pos_msisdn", "pos_name", "segment_group", "dsm_name",
    "region", "territory", "site_name", "statut", "priorite", "days_since_last_use",
]


def _guess_date(name: str) -> date | None:
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _save_cache(df_classified: pd.DataFrame, date_iso: str) -> None:
    path = CACHE_QR_DIR / f"{date_iso}.csv"
    df_classified[CACHE_COLUMNS].to_csv(path, index=False)


# ── Schéma de réponse ─────────────────────────────────────────────────────────

class ResultatImportQr(BaseModel):
    date_ref:   str
    nb_agents:  int
    sans_qr:    int
    non_utilise: int
    risque:     int
    actif:      int
    fichier_rapport: str
    message:    str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/qr",
    response_model=ResultatImportQr,
    summary="Importer un fichier QR Code",
    description=(
        "Accepte un fichier QR Code (.xlsx ou .gz). "
        "La date de référence est détectée automatiquement depuis le nom du fichier ; "
        "elle peut être surchargée via le champ date_ref (format AAAA-MM-JJ)."
    ),
)
async def importer_qr(
    fichier:  UploadFile = File(..., description="Fichier QR Code (.xlsx ou .gz)"),
    date_ref: str | None = Form(
        None,
        description="Date de référence ISO (AAAA-MM-JJ). Auto-détectée si absente.",
    ),
    _: RequireSuperAdmin = None,
) -> ResultatImportQr:

    raw = await fichier.read()

    # Résoudre la date de référence
    ref: date | None = None
    if date_ref:
        try:
            ref = date.fromisoformat(date_ref)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"date_ref invalide : '{date_ref}'. Format attendu : AAAA-MM-JJ",
            )
    if ref is None:
        ref = _guess_date(fichier.filename or "")
    if ref is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Impossible de détecter la date depuis le nom du fichier. "
                "Passez date_ref=AAAA-MM-JJ dans le formulaire."
            ),
        )

    # Lecture + classification
    try:
        df_raw = read_qr_file(raw)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur de lecture du fichier QR : {e}",
        )

    if df_raw.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucune ligne lue dans le fichier — vérifiez le format.",
        )

    df_classified = classify(df_raw, ref)
    date_iso = ref.isoformat()

    # Rapport Excel
    wb     = build_report_workbook(df_classified, ref, source_label="ALBARKA")
    chemin = db.build_output_path("qr_code", date_iso)
    wb.save(chemin)

    # Cache CSV
    _save_cache(df_classified, date_iso)

    # Historique
    db.save_import("qr_code", date_iso, date_iso, chemin, nb_lignes=len(df_classified))

    counts = df_classified["statut"].value_counts()

    return ResultatImportQr(
        date_ref=date_iso,
        nb_agents=len(df_classified),
        sans_qr=int(counts.get("Sans QR Code", 0)),
        non_utilise=int(counts.get("QR non utilisé (+30j)", 0)),
        risque=int(counts.get("Risque inactivité", 0)),
        actif=int(counts.get("Actif", 0)),
        fichier_rapport=str(chemin.name),
        message="Import QR Code réussi.",
    )
