"""
api/gestion.py
==============
Remplace src/services/gestion.ts

Endpoints :
  GET    /gestion/imports                    → historique des traitements
  DELETE /gestion/imports/{id}               → supprime un enregistrement (pas le fichier)
  GET    /gestion/imports/{id}/download      → télécharge le fichier Excel généré
  GET    /gestion/parrainages                → liste + synthèse des parrainages
  POST   /gestion/parrainages                → saisir / cumuler des parrainages
  DELETE /gestion/parrainages/{personne}/{date} → supprimer un enregistrement
  GET    /gestion/suivi-personnes            → suivi personnes spécialement suivies
  POST   /gestion/suivi-personnes            → nouvelle entrée
  DELETE /gestion/suivi-personnes/{id}       → supprimer une entrée
  GET    /gestion/utilisateurs               → liste des comptes
  POST   /gestion/utilisateurs               → créer un compte
  PATCH  /gestion/utilisateurs/{id}          → modifier nom/actif
  GET    /gestion/commerciaux                → liste des commerciaux
  PATCH  /gestion/commerciaux/{id}           → modifier un commercial
  GET    /gestion/seuils                     → liste des seuils
  POST   /gestion/seuils                     → créer/modifier un seuil
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core import db
from api.deps import RequireAdmin, RequireSuperAdmin, UtilisateurCourant
from api.schemas import (
    ImportRecordOut,
    ParrainageOut, ParrainageCreate, ParrainagesResponse, ParrainageSyntheseItem,
    SuiviPersonneOut, SuiviPersonneCreate, SuiviPersonnesResponse, SuiviPersonneSyntheseItem,
    UtilisateurOut, UtilisateurCreate, UtilisateurUpdate,
    CommercialOut, CommercialUpdate,
    SeuilOut, SeuilCreate,
)

router = APIRouter(prefix="/gestion", tags=["Gestion"])


# ── Historique des imports ────────────────────────────────────────────────────

@router.get("/imports", response_model=list[ImportRecordOut])
def get_imports(
    type_fichier: Optional[str] = Query(None, description="qr_code | transactions | comparatif"),
    recherche:    Optional[str] = Query(None),
    limite:       int           = Query(5,  ge=1),
    offset:       int           = Query(0,  ge=0),
    _: RequireAdmin = None,
):
    """
    Historique paginé des traitements.
    - limite=5 par défaut → les 5 derniers (bouton 'Voir plus' incrémente de 10)
    """
    if type_fichier == "tous":
        type_fichier = None

    if recherche:
        lignes = db.search_imports(recherche)
        if type_fichier:
            lignes = [l for l in lignes if l["type_fichier"] == type_fichier]
    else:
        lignes = db.list_imports(type_fichier, limit=limite, offset=offset)

    return [
        ImportRecordOut(
            id=l["id"],
            type_fichier=l["type_fichier"],
            cle=l["cle"],
            date_donnees=l.get("date_donnees"),
            chemin_fichier=l["chemin_fichier"],
            nb_lignes=l.get("nb_lignes"),
            date_execution=l["date_execution"],
            fichier_disponible=Path(l["chemin_fichier"]).exists(),
        )
        for l in lignes
    ]


@router.get("/imports/total")
def total_imports(
    type_fichier: Optional[str] = Query(None),
    _: RequireAdmin = None,
):
    """Nombre total d'imports (pour la pagination)."""
    if type_fichier == "tous":
        type_fichier = None
    return {"total": db.count_imports(type_fichier)}


@router.delete("/imports/{import_id}", status_code=204)
def supprimer_import(
    import_id: int,
    _: RequireSuperAdmin = None,
):
    """
    Supprime l'enregistrement en base — JAMAIS le fichier Excel sur disque.
    Correspond à supprimerImport() dans gestion.ts.
    """
    conn = db.get_connection()
    row  = conn.execute("SELECT type_fichier, cle FROM imports WHERE id = ?", (import_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Import introuvable.")
    db.delete_import(row["type_fichier"], row["cle"])


@router.get("/imports/{import_id}/download")
def telecharger_import(
    import_id: int,
    _: RequireAdmin = None,
):
    """Retourne le fichier Excel généré pour un import donné."""
    conn = db.get_connection()
    row  = conn.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Import introuvable.")
    chemin = Path(row["chemin_fichier"])
    if not chemin.exists():
        raise HTTPException(404, "Fichier introuvable sur le disque.")
    return FileResponse(
        path=str(chemin),
        filename=chemin.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Parrainages ───────────────────────────────────────────────────────────────

@router.get("/parrainages", response_model=ParrainagesResponse)
def get_parrainages(
    du: Optional[str] = Query(None),
    au: Optional[str] = Query(None),
    _: RequireSuperAdmin = None,
):
    """Liste + synthèse des parrainages sur une période."""
    lignes_db = db.get_parrainages(date_debut=du, date_fin=au)
    lignes    = [ParrainageOut(personne=l["personne"], date_op=l["date_op"], nb=l["nb"]) for l in lignes_db]
    personnes = sorted({l.personne for l in lignes})
    synthese  = [
        ParrainageSyntheseItem(
            personne=p,
            total=sum(l.nb for l in lignes if l.personne == p),
        )
        for p in personnes
    ]
    synthese.sort(key=lambda x: x.total, reverse=True)
    return ParrainagesResponse(
        lignes=lignes,
        synthese=synthese,
        total=sum(l.nb for l in lignes),
    )


@router.post("/parrainages", status_code=201)
def enregistrer_parrainage(body: ParrainageCreate, _: RequireSuperAdmin = None):
    """Saisit ou cumule des parrainages (même personne + date → addition)."""
    db.save_parrainage(body.personne, body.date_op, body.nb)
    return {"ok": True}


@router.delete("/parrainages/{personne}/{date_op}", status_code=204)
def supprimer_parrainage(personne: str, date_op: str, _: RequireSuperAdmin = None):
    """Supprime un enregistrement de parrainage (personne × date)."""
    db.delete_parrainage(personne, date_op)


# ── Suivi personnes ───────────────────────────────────────────────────────────

@router.get("/suivi-personnes", response_model=SuiviPersonnesResponse)
def get_suivi_personnes(
    commercial_id: Optional[int] = Query(None),
    du:            Optional[str] = Query(None),
    au:            Optional[str] = Query(None),
    _: RequireSuperAdmin = None,
):
    """Suivi des personnes spécialement suivies."""
    lignes_db = db.get_suivi_personnes(commercial_id=commercial_id, date_debut=du, date_fin=au)

    lignes = [
        SuiviPersonneOut(
            id=l["id"],
            commercial_id=l["commercial_id"],
            dsm_name=l["dsm_name"],
            nom_personne=l["nom_personne"],
            montant=l["montant"],
            date_heure=l["date_heure"],
        )
        for l in lignes_db
    ]

    groupes: dict[str, dict] = {}
    for l in lignes:
        cle = f"{l.dsm_name}|{l.nom_personne}"
        if cle not in groupes:
            groupes[cle] = {"dsm_name": l.dsm_name, "nom_personne": l.nom_personne, "montant": 0.0, "nb": 0}
        groupes[cle]["montant"] += l.montant
        groupes[cle]["nb"]      += 1

    synthese = sorted(
        [SuiviPersonneSyntheseItem(
            dsm_name=v["dsm_name"], nom_personne=v["nom_personne"],
            montant=v["montant"], nb_entrees=v["nb"]
         ) for v in groupes.values()],
        key=lambda x: x.montant, reverse=True,
    )
    return SuiviPersonnesResponse(
        lignes=lignes,
        synthese=synthese,
        montant_total=sum(l.montant for l in lignes),
        personnes_distinctes=len({l.nom_personne for l in lignes}),
    )


@router.post("/suivi-personnes", status_code=201)
def enregistrer_suivi(body: SuiviPersonneCreate, _: RequireSuperAdmin = None):
    """Nouvelle entrée de suivi personne."""
    db.save_suivi_personne(
        commercial_id=body.commercial_id,
        nom_personne=body.nom_personne,
        montant=body.montant,
        date_heure=body.date_heure,
    )
    return {"ok": True}


@router.delete("/suivi-personnes/{entry_id}", status_code=204)
def supprimer_suivi(entry_id: int, _: RequireSuperAdmin = None):
    """Supprime une entrée de suivi."""
    db.delete_suivi_personne(entry_id)


# ── Administration : utilisateurs ─────────────────────────────────────────────

def _user_to_out(u: dict) -> UtilisateurOut:
    com = db.get_commercial_by_user_id(u["id"])
    return UtilisateurOut(
        id=u["id"],
        username=u["username"],
        nom=u["nom"],
        role=u["role"],
        actif=bool(u["actif"]),
        dsm_name=com["dsm_name"] if com else None,
        created_at=u.get("created_at"),
    )


@router.get("/utilisateurs", response_model=list[UtilisateurOut])
def get_utilisateurs(_: RequireSuperAdmin = None):
    return [_user_to_out(u) for u in db.list_users()]


@router.post("/utilisateurs", response_model=UtilisateurOut, status_code=201)
def creer_utilisateur(body: UtilisateurCreate, _: RequireSuperAdmin = None):
    try:
        db.create_user(
            username=body.username,
            nom=body.nom,
            role=body.role,
            password=body.mot_de_passe,
            dsm_name=body.dsm_name,
        )
    except Exception as e:
        raise HTTPException(400, str(e))
    u = next((u for u in db.list_users() if u["username"] == body.username.lower()), None)
    if not u:
        raise HTTPException(500, "Création échouée.")
    return _user_to_out(u)


@router.patch("/utilisateurs/{user_id}", response_model=UtilisateurOut)
def maj_utilisateur(user_id: int, body: UtilisateurUpdate, utilisateur: UtilisateurCourant):
    if utilisateur["role"] != "super_admin":
        raise HTTPException(403, "Accès refusé.")
    if user_id == utilisateur["id"]:
        raise HTTPException(400, "Vous ne pouvez pas modifier votre propre compte ici.")
    db.update_user(user_id, nom=body.nom, password=None)
    if body.actif is not None:
        db.toggle_user_actif(user_id) if bool(db.get_user_by_id(user_id)["actif"]) != body.actif else None
    u = db.get_user_by_id(user_id)
    return _user_to_out(u)


# ── Administration : commerciaux ──────────────────────────────────────────────

def _com_to_out(c: dict) -> CommercialOut:
    return CommercialOut(
        id=c["id"],
        utilisateur_id=c.get("utilisateur_id"),
        dsm_name=c["dsm_name"],
        telephone=c.get("telephone"),
        zone=c.get("zone"),
        actif=bool(c["com_actif"]),
        alias=c.get("alias_csv"),
    )


@router.get("/commerciaux", response_model=list[CommercialOut])
def get_commerciaux(_: RequireSuperAdmin = None):
    return [_com_to_out(c) for c in db.list_commerciaux_complet()]


@router.patch("/commerciaux/{commercial_id}", response_model=CommercialOut)
def maj_commercial(
    commercial_id: int,
    body: CommercialUpdate,
    _: RequireSuperAdmin = None,
):
    if body.alias is not None:
        db.set_alias(commercial_id, body.alias or None)
    db.update_commercial(
        commercial_id,
        telephone=body.telephone,
        zone=body.zone,
        dsm_name=body.dsm_name,
    )
    if body.actif is not None:
        com = next((c for c in db.list_commerciaux_complet() if c["id"] == commercial_id), None)
        if com and bool(com["com_actif"]) != body.actif:
            db.toggle_commercial_actif(commercial_id)
    com = next((c for c in db.list_commerciaux_complet() if c["id"] == commercial_id), None)
    if not com:
        raise HTTPException(404, "Commercial introuvable.")
    return _com_to_out(com)


# ── Administration : seuils ───────────────────────────────────────────────────

@router.get("/seuils", response_model=list[SeuilOut])
def get_seuils(_: RequireAdmin = None):
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT s.id, s.type_flux, s.valeur, s.mois, s.created_at, u.username AS created_by
        FROM seuils s LEFT JOIN utilisateurs u ON u.id = s.created_by
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [
        SeuilOut(
            id=r["id"],
            type_flux=r["type_flux"],
            valeur=r["valeur"],
            mois=r["mois"],
            created_by=r["created_by"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/seuils", response_model=SeuilOut, status_code=201)
def enregistrer_seuil(
    body: SeuilCreate,
    utilisateur: UtilisateurCourant,
    _: RequireAdmin = None,
):
    db.set_seuil(
        type_flux=body.type_flux,
        valeur=body.valeur,
        mois=body.mois or None,
        created_by=utilisateur["id"],
    )
    seuil = db.get_seuil(body.type_flux, body.mois or None)
    return SeuilOut(
        id=seuil["id"],
        type_flux=seuil["type_flux"],
        valeur=seuil["valeur"],
        mois=seuil.get("mois"),
        created_by=None,
        created_at=seuil.get("created_at"),
    )
