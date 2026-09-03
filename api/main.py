"""
api/main.py
===========
Point d'entrée de l'API FastAPI ALBARKA.

Lancement :
  uvicorn api.main:app --reload --port 8000

Ou depuis la racine du projet :
  PATH="$HOME/.local/bin:$PATH" uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Documentation interactive : http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Charge .env si présent (développement local)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import db
from api.auth    import router as router_auth
from api.cash    import router as router_cash
from api.qr      import router as router_qr
from api.terrain import router as router_terrain
from api.gestion import router as router_gestion

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ALBARKA API",
    version="2.0.0",
    description=(
        "API REST pour le système de pilotage décisionnel ALBARKA. "
        "Expose les données Mobile Money, QR Code, Appro/Destockage, "
        "Portefeuilles et Administration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Autoriser le frontend React (Vite dev sur :5173 et prod)
ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Initialisation DB au démarrage ────────────────────────────────────────────

@app.on_event("startup")
def startup():
    db.init_db()


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(router_auth)
app.include_router(router_cash)
app.include_router(router_qr)
app.include_router(router_terrain)
app.include_router(router_gestion)


# ── Healthcheck ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health():
    """Vérifie que l'API est opérationnelle."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/", tags=["Meta"])
def root():
    return {
        "message": "ALBARKA API — voir /docs pour la documentation interactive.",
        "docs":    "/docs",
    }
