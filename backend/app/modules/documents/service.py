import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.modules.documents.repository import document_repository
from app.modules.documents.schemas import DocumentCreate, DocumentResponse, DocumentUpdate


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def _next_document_id() -> str:
    return f"CHECK-{uuid.uuid4().hex[:8].upper()}"


def create_document(payload: DocumentCreate) -> DocumentResponse:
    internal_id = str(uuid.uuid4())
    public_id = secrets.token_urlsafe(18)
    created_at = datetime.now(timezone.utc)
    content = payload.content.strip() if payload.content else ""
    document_id = (payload.document_id or _next_document_id()).strip()
    document = {
        "internal_id": internal_id,
        "public_id": public_id,
        "document_id": document_id,
        "title": payload.title.strip(),
        "document_type": payload.document_type.strip(),
        "reference_period": payload.reference_period,
        "owner_name": payload.owner_name.strip() if payload.owner_name else None,
        "collection_name": payload.collection_name.strip() or "documents",
        "content": content,
        "status": "created",
        "version": 1,
        "previous_hash": None,
        "finalized": False,
        "hashes": [_hash_content(content)],
        "created_at": created_at,
        "updated_at": created_at,
    }

    document_repository.save(document)

    return DocumentResponse(**document)


def list_documents() -> list[DocumentResponse]:
    return [DocumentResponse(**document) for document in document_repository.list_all()]


def update_document(public_id: str, payload: DocumentUpdate) -> DocumentResponse:
    document = document_repository.get_by_public_id(public_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    updated_content = payload.content.strip() if payload.content is not None else document["content"]
    updated_title = payload.title.strip() if payload.title is not None else document["title"]
    updated_document_id = payload.document_id.strip() if payload.document_id is not None else document.get("document_id", _next_document_id())
    updated_document_type = payload.document_type.strip() if payload.document_type is not None else document["document_type"]
    updated_reference_period = payload.reference_period if payload.reference_period is not None else document["reference_period"]
    updated_owner_name = payload.owner_name.strip() if payload.owner_name is not None else document["owner_name"]
    updated_collection_name = payload.collection_name.strip() if payload.collection_name is not None else document["collection_name"]
    previous_hash = document.get("hashes", [])[-1] if document.get("hashes") else None
    next_version = int(document.get("version", len(document.get("hashes", [])))) + 1

    new_hash = _hash_content(updated_content)
    document["title"] = updated_title
    document["document_id"] = updated_document_id
    document["document_type"] = updated_document_type
    document["reference_period"] = updated_reference_period
    document["owner_name"] = updated_owner_name
    document["collection_name"] = updated_collection_name
    document["content"] = updated_content
    document["hashes"] = [*document.get("hashes", []), new_hash]
    document["status"] = payload.status.strip() if payload.status is not None else "updated"
    document["version"] = next_version
    document["previous_hash"] = previous_hash
    document["finalized"] = bool(payload.finalized) if payload.finalized is not None else False
    document["updated_at"] = datetime.now(timezone.utc)

    document_repository.save(document)

    return DocumentResponse(**document)
