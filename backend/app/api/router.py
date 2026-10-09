from fastapi import APIRouter

from app.api.routers.health import router as health_router
from app.api.routers.verification import router as verification_router
from app.modules.documents.router import router as documents_router
from app.modules.documents.version_api import router as versions_router
from app.core.config import settings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(versions_router)
# Rotas experimentais antigas: somente em ambiente local, nunca em producao.
if settings.app_env == "development":
    api_router.include_router(documents_router)
    api_router.include_router(verification_router)
# A rota SQL antiga aceitava DSN arbitrario do cliente, risco SSRF; mantida fora da aplicacao.


