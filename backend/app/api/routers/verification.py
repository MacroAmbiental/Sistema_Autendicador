from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.modules.documents.repository import document_repository
from app.services.hash_service import calculate_sha256
from app.services.pdf_service import authenticate_pdf, verify_pdf_against_hash

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.get("/{public_id}")
async def get_verification(public_id: str):
    document = document_repository.get_by_public_id(public_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    return {
        "public_id": document["public_id"],
        "title": document.get("title"),
        "document_type": document.get("document_type"),
        "status": document.get("status"),
        "verification_url": document.get("verification_url"),
        "original_hash": document.get("original_hash"),
        "authenticated_hash": document.get("authenticated_hash"),
        "hashes": document.get("hashes", []),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "valid": document.get("status") in {"autenticado", "updated"},
    }


@router.post("/{public_id}/file")
async def verify_document_file(public_id: str, file: UploadFile = File(...)):
    document = document_repository.get_by_public_id(public_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    uploaded_content = await file.read()
    expected_hash = document.get("authenticated_hash") or document.get("hashes", [None])[-1]
    if expected_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este documento ainda não possui hash autenticado registrado.",
        )

    authenticated_version = authenticate_pdf(uploaded_content, document["verification_url"])
    actual_hash = calculate_sha256(authenticated_version)
    is_valid = verify_pdf_against_hash(authenticated_version, expected_hash)
    return {
        "public_id": public_id,
        "document_title": document.get("title"),
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "valid": is_valid,
        "status": "autenticado" if is_valid else "alterado",
    }
