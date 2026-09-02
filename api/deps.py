"""
api/deps.py
===========
Dépendances FastAPI partagées :
  - Création / vérification des JWT
  - Récupération de l'utilisateur connecté depuis le token
  - Guards require_role pour restreindre l'accès par rôle
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import db

# ── Configuration JWT ─────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "albarka-dev-secret-change-in-production")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 heures

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Création du token ─────────────────────────────────────────────────────────

def creer_token(user_id: int, username: str, role: str) -> str:
    """Génère un JWT signé contenant l'identité de l'utilisateur."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub":      str(user_id),
        "username": username,
        "role":     role,
        "exp":      expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Vérification du token ─────────────────────────────────────────────────────

def _extraire_payload(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dépendance : utilisateur courant ─────────────────────────────────────────

def get_utilisateur_courant(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """
    Injecte l'utilisateur connecté dans chaque endpoint sécurisé.
    Lève 401 si le token est absent, invalide ou expiré.
    """
    payload  = _extraire_payload(token)
    user_id  = int(payload.get("sub", 0))
    utilisateur = db.get_user_by_id(user_id)
    if not utilisateur or not utilisateur.get("actif"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable ou désactivé.",
        )
    return utilisateur


UtilisateurCourant = Annotated[dict, Depends(get_utilisateur_courant)]


# ── Guards de rôle ────────────────────────────────────────────────────────────

def _guard(*roles: str):
    """Factory qui retourne une dépendance vérifiant que l'utilisateur a l'un des rôles."""
    def _dep(utilisateur: UtilisateurCourant) -> dict:
        if utilisateur["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé — droits insuffisants.",
            )
        return utilisateur
    return _dep


# Dépendances prêtes à l'emploi dans les routers
RequireAdmin      = Annotated[dict, Depends(_guard("super_admin", "admin"))]
RequireSuperAdmin = Annotated[dict, Depends(_guard("super_admin"))]
RequireAll        = Annotated[dict, Depends(_guard("super_admin", "admin", "commercial"))]
