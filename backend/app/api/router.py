from fastapi import APIRouter

from app.api.routers.health import router as health_router
from app.api.routers.sql import router as sql_router
from app.api.routers.verification import router as verification_router
from app.modules.documents.router import router as documents_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(verification_router)
api_router.include_router(sql_router)

