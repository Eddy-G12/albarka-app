"""
api/import_sae.py
=================
POST /import/sae

Remplace pages/6_Cash_Flow.py (onglet Import SAE).

Pipeline :
  1. Lire le fichier SAE XLSX ou CSV (read_sae_file)
  2. Détecter le mois depuis le nom de fichier (ou param mois)
  3. Upsert les POS et leur cashflow en base (import_sae_file)
  4. Retourner un résumé JSON
"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from core.cashflow import import_sae_file
from api.deps import RequireSuperAdmin

router = APIRouter(prefix="/import", tags=["Import"])


# ── Schéma de réponse ─────────────────────────────────────────────────────────

class ResultatImportSae(BaseModel):
    mois:           str
    nb_pos:         int
    total_cash_in:  float
    total_cash_out: float
    message:        str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/sae",
    response_model=ResultatImportSae,
    summary="Importer un fichier SAE MTN (Cash Flow POS)",
    description=(
        "Accepte un fichier SAE MTN (.xlsx ou .csv). "
        "Le mois est détecté automatiquement depuis le nom du fichier (ex. JUILLET_2026, 2026-07) ; "
        "il peut être surcharge via le champ mois (format AAAA-MM)."
    ),
)
async def importer_sae(
    fichier: UploadFile = File(..., description="Fichier SAE MTN (.xlsx ou .csv)"),
    mois: str | None = Form(
        None,
        description="Mois AAAA-MM (optionnel — auto-détecté depuis le nom du fichier)",
    ),
    _: RequireSuperAdmin = None,
) -> ResultatImportSae:

    raw = await fichier.read()

    try:
        resultat = import_sae_file(
            raw,
            nom_fichier=fichier.filename or "",
            mois=mois.strip() if mois else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'import SAE : {e}",
        )

    return ResultatImportSae(
        mois=resultat["mois"],
        nb_pos=resultat["nb_pos"],
        total_cash_in=resultat["total_cash_in"],
        total_cash_out=resultat["total_cash_out"],
        message=f"Import SAE réussi — {resultat['nb_pos']} POS — mois {resultat['mois']}",
    )
