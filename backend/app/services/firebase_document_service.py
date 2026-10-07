from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.core.firebase import get_firestore, get_storage_bucket


def has_firebase_configuration() -> bool:
    return bool(settings.firebase_project_id and settings.firebase_storage_bucket)


def persist_document_to_firebase(document: dict, original_pdf: bytes, authenticated_pdf: bytes) -> dict:
    if not has_firebase_configuration():
        document["storage"] = "memory"
        return document

    try:
        storage = get_storage_bucket()
        public_id = document["public_id"]
        original_path = f"documents/{public_id}/original/{public_id}_original.pdf"
        authenticated_path = f"documents/{public_id}/authenticated/{public_id}_authenticated.pdf"

        storage.blob(original_path).upload_from_string(original_pdf, content_type="application/pdf")
        storage.blob(authenticated_path).upload_from_string(authenticated_pdf, content_type="application/pdf")

        document["original_path"] = original_path
        document["authenticated_path"] = authenticated_path
        document["storage"] = "firebase"
        document["versions"] = document.get("versions", [])
        document["updated_at"] = datetime.now(timezone.utc)

        firestore_client = get_firestore()
        firestore_client.collection("documents").document(public_id).set(document)
    except Exception:
        document["storage"] = "memory"

    return document
