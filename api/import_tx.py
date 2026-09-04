"""
api/import_tx.py
================
POST /import/transactions

Remplace pages/1_Transactions.py (onglet import).

Pipeline :
  1. Lire et nettoyer le CSV Mobile Money (clean_transactions)
  2. Générer le classeur Excel (build_transactions_workbook) → sauvé sur disque
  3. Calculer les points touchés (compute_points_touches)
  4. Identifier le commercial depuis le nom de fichier
  5. Si alias configuré :
       - Extraire et persister les clients servis
       - Extraire et persister l'appro / déstockage
  6. Persister l'historique d'import (table imports)
  7. Retourner un résumé JSON
"""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from core import db
from core.transactions import (
    clean_transactions,
    build_transactions_workbook,
    compute_points_touches,
    extract_clients_servis,
    extract_appro_from_workbook,
)
from api.deps import RequireSuperAdmin

router = APIRouter(prefix="/import", tags=["Import"])


# ── Schéma de réponse ─────────────────────────────────────────────────────────

class ResultatImportTx(BaseModel):
    fichier:           str
    nb_lignes:         int
    points_par_jour:   float
    commercial:        str | None
    alias:             str | None
    nb_clients_servis: int
    appro_ok:          bool
    message:           str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/transactions",
    response_model=list[ResultatImportTx],
    summary="Importer des CSV Mobile Money",
    description=(
        "Accepte un ou plusieurs fichiers CSV bruts MTN. Pour chaque fichier : "
        "nettoyage, génération du classeur Excel, calcul des points touchés, "
        "extraction des clients servis et de l'appro/déstockage (si alias configuré)."
    ),
)
async def importer_transactions(
    fichiers: list[UploadFile] = File(..., description="CSV bruts MTN (un par commercial)"),
    _: RequireSuperAdmin = None,
) -> list[ResultatImportTx]:

    commerciaux    = db.list_commerciaux()
    com_by_dsm     = {c["dsm_name"].upper(): c for c in commerciaux}
    resultats: list[ResultatImportTx] = []

    for f in fichiers:
        cle       = Path(f.filename or "inconnu").stem
        raw_bytes = await f.read()

        # 1. Nettoyage
        try:
            df = clean_transactions(io.BytesIO(raw_bytes))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{f.filename} : impossible de lire le CSV — {e}",
            )

        if df.empty:
            resultats.append(ResultatImportTx(
                fichier=f.filename or cle, nb_lignes=0, points_par_jour=0.0,
                commercial=None, alias=None, nb_clients_servis=0, appro_ok=False,
                message="Aucune ligne exploitable après nettoyage.",
            ))
            continue

        # 2. Classeur Excel
        wb     = build_transactions_workbook(df, source_label=cle)
        chemin = db.build_output_path("transactions", cle)
        wb.save(chemin)

        # 3. Points touchés
        pts = compute_points_touches(df)

        # 4. Identification du commercial
        commercial_match = None
        stem_upper = cle.upper()
        for dsm, com in com_by_dsm.items():
            if dsm in stem_upper:
                commercial_match = com
                break

        nb_clients_servis = 0
        appro_ok          = False

        if commercial_match:
            com_id = commercial_match["id"]
            alias  = commercial_match.get("alias_csv")

            if alias:
                # 5a. Clients servis
                try:
                    clients_list = extract_clients_servis(df, alias)
                    if clients_list:
                        db.save_clients_servis(
                            com_id,
                            contreparties=clients_list,
                            source_fichier=f.filename,
                        )
                        nb_clients_servis = len(clients_list)
                except Exception:
                    pass  # non bloquant

                # 5b. Appro / Déstockage
                try:
                    appro_rows = extract_appro_from_workbook(chemin, alias)
                    if appro_rows:
                        conn = db.get_connection()
                        try:
                            for row_a in appro_rows:
                                conn.execute("""
                                    INSERT INTO appro
                                        (commercial_id, date_op, type_op,
                                         nb_ops, montant, source_fichier)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(commercial_id, date_op, type_op)
                                    DO UPDATE SET
                                        nb_ops         = excluded.nb_ops,
                                        montant        = excluded.montant,
                                        source_fichier = excluded.source_fichier,
                                        created_at     = datetime('now')
                                """, (
                                    com_id,
                                    row_a["date_op"],
                                    row_a["type_op"],
                                    row_a.get("nb_ops", 0),
                                    row_a.get("montant", 0.0),
                                    f.filename,
                                ))
                            conn.commit()
                            appro_ok = True
                        finally:
                            conn.close()
                except Exception:
                    pass  # non bloquant

        # 6. Historique
        date_donnees = str(df["Date"].max())
        db.save_import("transactions", cle, date_donnees, chemin, nb_lignes=len(df))

        resultats.append(ResultatImportTx(
            fichier=f.filename or cle,
            nb_lignes=len(df),
            points_par_jour=pts["moyenne_par_jour"],
            commercial=commercial_match["dsm_name"] if commercial_match else None,
            alias=commercial_match.get("alias_csv") if commercial_match else None,
            nb_clients_servis=nb_clients_servis,
            appro_ok=appro_ok,
            message="OK",
        ))

    return resultats
