"""
api/import_pf.py
================
POST /import/portefeuille

Remplace pages/9_Portefeuilles.py (onglet Import).

Pipeline :
  1. Parser le fichier Excel ALBARKA (détection auto de l'en-tête et des colonnes)
  2. Créer le portefeuille et ses clients en base
  3. Retourner un résumé JSON
"""
from __future__ import annotations

import re
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from core import db
from api.deps import RequireSuperAdmin

router = APIRouter(prefix="/import", tags=["Import"])


# ── Parsing (extrait de pages/9_Portefeuilles.py) ─────────────────────────────

def _parse_portefeuille_file(raw: bytes) -> list[dict]:
    """
    Parse le fichier Excel ALBARKA.
    Détecte automatiquement la ligne d'en-tête (cherche 'ccial' ou 'msisdn')
    et les colonnes MSISDN, nom, profil POS.
    Retourne [{msisdn, nom, pos_profile}].
    """
    df_raw = pd.read_excel(BytesIO(raw), header=None, dtype=str)

    # 1. Trouver la ligne d'en-tête
    header_row = None
    for i, row in df_raw.iterrows():
        vals = [
            str(v).strip().lower()
            for v in row
            if pd.notna(v) and str(v).strip() not in ("", "nan")
        ]
        if any("ccial" in v or "msisdn" in v for v in vals):
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            "Ligne d'en-tête non trouvée. Vérifiez que le fichier contient "
            "une colonne 'numéro_ccial' ou 'msisdn'."
        )

    headers = [
        str(v).strip().lower() if pd.notna(v) and str(v).strip() not in ("", "nan") else ""
        for v in df_raw.iloc[header_row]
    ]

    # 2. Trouver la colonne MSISDN dans les données
    col_msisdn_data = None
    for i in range(header_row + 1, min(header_row + 10, len(df_raw))):
        row = df_raw.iloc[i]
        for j, val in enumerate(row):
            v = re.sub(r"[^0-9]", "", str(val))
            if re.match(r"^237[0-9]{8,9}$", v):
                col_msisdn_data = j
                break
        if col_msisdn_data is not None:
            break

    if col_msisdn_data is None:
        raise ValueError(
            "Colonne MSISDN introuvable. Les numéros doivent être au format 237XXXXXXXXX."
        )

    # 3. Colonne nom client
    col_nom_h = next(
        (i for i, h in enumerate(headers) if "nom" in h and "puce" not in h and "pos" not in h),
        None,
    )

    # 4. Colonne profil POS (contient 'MTNC' dans les données)
    col_profil_data = None
    for i in range(header_row + 1, min(header_row + 5, len(df_raw))):
        row = df_raw.iloc[i]
        for j, val in enumerate(row):
            if "MTNC" in str(val):
                col_profil_data = j
                break
        if col_profil_data is not None:
            break
    if col_profil_data is None:
        col_profil_data = next(
            (i for i, h in enumerate(headers) if "profil" in h or "profile" in h or "puce" in h),
            None,
        )

    # 5. Extraire les clients
    clients: list[dict] = []
    for i in range(header_row + 1, len(df_raw)):
        row = df_raw.iloc[i]

        msisdn_raw = str(row.iloc[col_msisdn_data]).strip() if col_msisdn_data < len(row) else ""
        nom        = str(row.iloc[col_nom_h]).strip() if col_nom_h is not None and col_nom_h < len(row) else ""
        profil     = str(row.iloc[col_profil_data]).strip() if col_profil_data is not None and col_profil_data < len(row) else ""

        for bad in ("nan", "None", "NaN"):
            if msisdn_raw == bad: msisdn_raw = ""
            if nom == bad:        nom = ""
            if profil == bad:     profil = ""

        msisdn_clean = re.sub(r"[^0-9]", "", msisdn_raw)
        if not msisdn_clean or len(msisdn_clean) < 9:
            continue
        if re.sub(r"[^0-9]", "", nom) == msisdn_clean:
            nom = ""

        clients.append({"msisdn": msisdn_clean, "nom": nom, "pos_profile": profil})

    return clients


# ── Schémas ───────────────────────────────────────────────────────────────────

class ResultatImportPordefeuille(BaseModel):
    portefeuille_id: int
    nom:             str
    commercial:      str
    nb_clients:      int
    message:         str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/portefeuille",
    response_model=ResultatImportPordefeuille,
    summary="Importer un portefeuille clients",
    description=(
        "Accepte un fichier Excel ALBARKA (.xlsx). "
        "L'en-tête est détecté automatiquement quel que soit le nombre de lignes vides. "
        "commercial_id : identifiant du commercial auquel rattacher le portefeuille."
    ),
)
async def importer_portefeuille(
    fichier:       UploadFile = File(..., description="Fichier Excel ALBARKA (.xlsx)"),
    commercial_id: int        = Form(..., description="ID du commercial"),
    nom:           str        = Form(..., description="Nom du portefeuille"),
    _: RequireSuperAdmin = None,
) -> ResultatImportPordefeuille:

    raw = await fichier.read()

    # Vérifier que le commercial existe
    commerciaux = db.list_commerciaux_complet()
    com = next((c for c in commerciaux if c["id"] == commercial_id), None)
    if not com:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commercial id={commercial_id} introuvable.",
        )

    # Parser le fichier
    try:
        clients_parsed = _parse_portefeuille_file(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de lecture du fichier : {e}",
        )

    if not clients_parsed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun client valide trouvé dans le fichier.",
        )

    # Convertir au format attendu par db.create_portefeuille
    from datetime import date
    clients_db = [
        {
            "nom":       c["nom"] or c["msisdn"],
            "telephone": c["msisdn"],
            "localite":  c["pos_profile"],
        }
        for c in clients_parsed
    ]

    pf_id = db.create_portefeuille(
        commercial_id=commercial_id,
        nom=nom.strip(),
        date_import=date.today().isoformat(),
        clients=clients_db,
    )

    return ResultatImportPordefeuille(
        portefeuille_id=pf_id,
        nom=nom.strip(),
        commercial=com["dsm_name"],
        nb_clients=len(clients_parsed),
        message=f"Portefeuille '{nom}' créé — {len(clients_parsed)} clients.",
    )
