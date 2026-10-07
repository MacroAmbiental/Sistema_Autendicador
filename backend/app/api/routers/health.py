from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.firebase import get_firestore

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "application": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/firebase")
async def firebase_health_check():
    try:
        db = get_firestore()
        doc_ref = db.collection("_system").document("health")
        doc_ref.set({"status": "ok"})
        document = doc_ref.get()

        return {
            "status": "ok",
            "firebase": "connected",
            "firestore": {"status": document.to_dict().get("status")},
        }
    except Exception as exc:  # pragma: no cover - external dependency path
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Firebase.",
        ) from exc