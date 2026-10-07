from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=(
        "API do sistema Autenticador Macroambiental para "
        "validação, integridade, autenticação e "
        "rastreabilidade de documentos."
    ),
    version="0.1.0",
    debug=settings.debug,
)


# ============================================================
# CORS
# ============================================================

allowed_origins = [
    # Desenvolvimento local
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    # Produção
    "https://sistema-de-equipamentos.onrender.com",
]



app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Arquivos estáticos
# ============================================================

static_dir = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=static_dir),
    name="static",
)


# ============================================================
# API
# ============================================================

app.include_router(api_router)



# ============================================================
# Health Check
# ============================================================

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": "0.1.0",
    }


# ============================================================
# Root
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "application": settings.app_name,
        "status": "running",
        "version": "0.1.0",
    }



# ============================================================
# Frontend
# ============================================================

@app.get("/frontend", include_in_schema=False)
async def frontend_page():
    return FileResponse(
        static_dir / "index.html"
    )