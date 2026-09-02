"""
api/auth.py
===========
Remplace src/services/auth.ts

Endpoints :
  POST /auth/login   → connexion, retourne JWT + profil utilisateur
  GET  /auth/me      → profil de l'utilisateur connecté
"""

from fastapi import APIRouter, HTTPException, status
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import db
from api.deps import creer_token, UtilisateurCourant
from api.schemas import LoginRequest, LoginResponse, UtilisateurOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_utilisateur_out(u: dict) -> UtilisateurOut:
    """Convertit un dict db → UtilisateurOut (camelCase → snake_case)."""
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


@router.post("/login", response_model=LoginResponse, summary="Connexion")
def login(body: LoginRequest):
    """
    Vérifie les identifiants et retourne un JWT.
    Correspond à connexion() dans auth.ts.
    """
    utilisateur = db.authenticate_user(body.username, body.mot_de_passe)
    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
        )
    if not utilisateur.get("actif"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé. Contactez un administrateur.",
        )
    token = creer_token(utilisateur["id"], utilisateur["username"], utilisateur["role"])
    return LoginResponse(
        utilisateur=_to_utilisateur_out(utilisateur),
        token=token,
    )


@router.get("/me", response_model=UtilisateurOut, summary="Profil courant")
def me(utilisateur: UtilisateurCourant):
    """Retourne le profil de l'utilisateur connecté à partir de son token."""
    return _to_utilisateur_out(utilisateur)
