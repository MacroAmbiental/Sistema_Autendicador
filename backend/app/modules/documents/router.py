from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.modules.documents.repository import document_repository
from app.modules.documents.schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from app.modules.documents.service import create_document, list_documents, update_document
from app.services.firebase_document_service import persist_document_to_firebase
from app.services.hash_service import calculate_sha256
from app.services.pdf_service import authenticate_pdf
from app.services.qrcode_service import build_verification_url

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_document_route():
    return list_documents()


@router.get("/{public_id}")
async def get_document_route(public_id: str):
    document = document_repository.get_by_public_id(public_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return document


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def create_document_route(payload: DocumentCreate):
    return create_document(payload)


@router.post("/authenticate", status_code=status.HTTP_201_CREATED)
async def authenticate_document_route(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    reference_period: str | None = Form(default=None),
    owner_name: str | None = Form(default=None),
    collection_name: str = Form(default="documents"),
):
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não pode estar vazio.",
        )

    public_id = str(uuid4())
    now = datetime.now(timezone.utc)
    original_hash = calculate_sha256(content)
    verification_url = build_verification_url(public_id)
    authenticated_pdf = authenticate_pdf(content, verification_url)
    authenticated_hash = calculate_sha256(authenticated_pdf)

    document = {
        "internal_id": str(uuid4()),
        "public_id": public_id,
        "title": title.strip(),
        "document_type": document_type.strip(),
        "reference_period": reference_period.strip() if reference_period else None,
        "owner_name": owner_name.strip() if owner_name else None,
        "collection_name": collection_name.strip() or "documents",
        "content": file.filename or title.strip(),
        "status": "autenticado",
        "hashes": [original_hash, authenticated_hash],
        "original_hash": original_hash,
        "authenticated_hash": authenticated_hash,
        "verification_url": verification_url,
        "created_at": now,
        "updated_at": now,
        "versions": [
            {
                "version": 1,
                "original_hash": original_hash,
                "authenticated_hash": authenticated_hash,
                "created_at": now.isoformat(),
            }
        ],
    }

    document_repository.save(document)
    return persist_document_to_firebase(document, content, authenticated_pdf)


@router.get("/{public_id}/versions")
async def document_versions_route(public_id: str):
    document = document_repository.get_by_public_id(public_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    hashes = document.get("hashes", [])
    return {
        "public_id": public_id,
        "versions": [
            {
                "version": index + 1,
                "hash": hash_value,
                "created_at": document.get("created_at"),
            }
            for index, hash_value in enumerate(hashes)
        ],
        "total_versions": len(hashes),
    }


@router.patch("/{public_id}", response_model=DocumentResponse)
async def update_document_route(public_id: str, payload: DocumentUpdate):
    return update_document(public_id, payload)
