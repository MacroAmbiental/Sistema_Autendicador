"""API de autenticacao entre sistemas: versoes publicas imutaveis."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.hash_service import calculate_sha256
from app.services.pdf_service import authenticate_pdf
from app.services.snapshot_pdf import create_snapshot_pdf
from app.services import version_store as store

router = APIRouter(tags=["Checklist authentication"])
SAFE_ID = r"^[a-zA-Z0-9_-]+$"


def secure_write(x_integration_key: str | None = Header(default=None)):
    expected = settings.integration_api_key
    if not expected:
        raise HTTPException(503, "INTEGRATION_API_KEY nao configurada")
    if not hmac.compare_digest(x_integration_key or "", expected):
        raise HTTPException(401, "Credencial de integracao invalida")


def secure_admin(x_admin_key: str | None = Header(default=None)):
    expected = settings.admin_api_key
    if not expected:
        raise HTTPException(503, "ADMIN_API_KEY nao configurada")
    if not hmac.compare_digest(x_admin_key or "", expected):
        raise HTTPException(401, "Credencial de administrador invalida")


def _audit_item(document_id: str, version_id: str, user_agent: str, result: str) -> dict:
    device = "Mobile" if any(marker in user_agent.lower() for marker in ("mobile", "android", "iphone")) else "Desktop"
    return {"document_id": document_id, "version_id": version_id,
            "device": device, "datetime_br": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S"),
            "result": result}


class VersionRequest(BaseModel):
    document_id: str = Field(..., min_length=4, max_length=160, pattern=SAFE_ID)
    event_id: str = Field(..., min_length=6, max_length=240)
    title: str = Field(..., min_length=2, max_length=200)
    document_type: str = Field(default="checklist", max_length=80)
    source: str = Field(default="equipamentos", max_length=100)
    content_json: str = Field(..., min_length=2, max_length=3_000_000)
    pdf_base64: str | None = None
    signature_status: str = Field(default="pendente", max_length=50)
    reference_period: str | None = Field(default=None, max_length=80)


def _version_id(document_id: str, event_id: str) -> str:
    # HMAC torna o identificador do link publico nao enumeravel.
    return hmac.new(settings.integration_api_key.encode(), f"{document_id}|{event_id}".encode(), hashlib.sha256).hexdigest()[:40]


def _decode_pdf(encoded: str) -> bytes:
    encoded = encoded.partition(",")[2] if encoded.startswith("data:") else encoded
    try:
        result = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("PDF em base64 invalido") from exc
    if len(result) > settings.max_pdf_bytes:
        raise ValueError("PDF excede tamanho maximo")
    return result


def _sanitize_metadata(record: dict):
    # Nunca expor event_id e caminhos de armazenamento ao publico.
    return {key: value for key, value in record.items() if key not in {"event_id", "source_pdf_hash"}}


def _register(request: VersionRequest):
    try:
        normalized = json.dumps(json.loads(request.content_json), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except (ValueError, TypeError) as exc:
        raise ValueError("content_json precisa ser JSON valido") from exc
    content = normalized.encode("utf-8")
    if len(content) > 3_000_000:
        raise ValueError("Snapshot JSON excede 3MB")
    original = _decode_pdf(request.pdf_base64) if request.pdf_base64 else create_snapshot_pdf(request.title, normalized)
    if len(original) > settings.max_pdf_bytes:
        raise ValueError("PDF excede tamanho maximo")
    identifier = _version_id(request.document_id, request.event_id)
    verification_url = (settings.verification_base_url.rstrip("/") + "/verificar/" + quote(request.document_id, safe="") + "/" + identifier)
    verified_pdf = authenticate_pdf(original, verification_url)
    if len(verified_pdf) > settings.max_pdf_bytes:
        raise ValueError("PDF autenticado excede limite permitido")
    metadata = {
        "document_id": request.document_id, "event_id": request.event_id,
        "title": request.title, "document_type": request.document_type,
        "source": request.source, "signature_status": request.signature_status,
        "reference_period": request.reference_period,
        "content_hash": calculate_sha256(content),
        "source_pdf_hash": calculate_sha256(original),
        "pdf_hash": calculate_sha256(verified_pdf),
        "verification_url": verification_url,
    }
    return store.save_version(request.document_id, identifier, metadata, verified_pdf, content)


@router.post("/checklists/versions", status_code=201, dependencies=[Depends(secure_write)])
async def register_version(payload: VersionRequest):
    try:
        registered = await run_in_threadpool(_register, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {**_sanitize_metadata(registered), "pdf_path": f"/api/v1/verify/{payload.document_id}/{registered['version_id']}/pdf"}


@router.get("/checklists/{document_id}/versions")
async def versions(document_id: str):
    if not document_id or len(document_id) > 160 or not document_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Documento invalido")
    root = await run_in_threadpool(store.get_document, document_id)
    if not root:
        raise HTTPException(404, "Documento nao encontrado")
    records = await run_in_threadpool(store.list_versions, document_id)
    return {"document_id": document_id, "latest_version": root.get("latest_version"),
            "versions": [_sanitize_metadata(v) for v in records]}


@router.get("/verify/{document_id}/{version_id}")
async def verify_public(document_id: str, version_id: str, request: Request):
    doc = await run_in_threadpool(store.get_document, document_id)
    record = await run_in_threadpool(store.get_version, document_id, version_id) if doc else None
    if not record or record.get("state") != "ready":
        # Consultas a identificadores inexistentes tambem entram na trilha de auditoria.
        try:
            await run_in_threadpool(store.record_audit,
                _audit_item(document_id, version_id, request.headers.get("user-agent", ""), "nao_encontrado"))
        except Exception as exc:
            raise HTTPException(503, "Falha ao registrar auditoria") from exc
        raise HTTPException(404, "Versao nao encontrada")
    try:
        original_pdf = await run_in_threadpool(store.get_file, document_id, version_id, "pdf")
        snapshot = await run_in_threadpool(store.get_file, document_id, version_id, "json")
        valid = (calculate_sha256(original_pdf) == record["pdf_hash"] and
                 calculate_sha256(snapshot) == record["content_hash"])
    except Exception:
        valid = False
    result = "autentico" if valid else "integridade_comprometida"
    # Registrar consulta antes de responder: nao declarar valido sem auditoria.
    try:
        await run_in_threadpool(store.record_audit,
            _audit_item(document_id, version_id, request.headers.get("user-agent", ""), result))
    except Exception as exc:
        raise HTTPException(503, "Falha ao registrar auditoria da consulta") from exc
    public = _sanitize_metadata(record)
    public.update(valid=valid, status=result, is_latest=doc.get("latest_version_id") == version_id,
                  latest_version=doc.get("latest_version"),
                  pdf_path=f"/api/v1/verify/{document_id}/{version_id}/pdf")
    return public


@router.get("/verify/{document_id}/{version_id}/pdf")
async def read_version_pdf(document_id: str, version_id: str, request: Request):
    record = await run_in_threadpool(store.get_version, document_id, version_id)
    if not record:
        raise HTTPException(404, "Versao nao encontrada")
    try:
        pdf = await run_in_threadpool(store.get_file, document_id, version_id, "pdf")
    except Exception as exc:
        raise HTTPException(503, "PDF indisponivel") from exc
    matched = calculate_sha256(pdf) == record["pdf_hash"]
    try:
        await run_in_threadpool(store.record_audit,
            _audit_item(document_id, version_id, request.headers.get("user-agent", ""),
                        "pdf_consultado" if matched else "integridade_comprometida"))
    except Exception as exc:
        raise HTTPException(503, "Falha na auditoria") from exc
    if not matched:
        raise HTTPException(409, "Integridade do PDF comprometida")
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="checklist-{version_id[:12]}.pdf"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/verify/{document_id}/{version_id}/file")
async def compare_file(document_id: str, version_id: str, request: Request, file: UploadFile = File(...)):
    record = await run_in_threadpool(store.get_version, document_id, version_id)
    if not record:
        raise HTTPException(404, "Versao nao encontrada")
    contents = await file.read(settings.max_pdf_bytes + 1)
    if len(contents) > settings.max_pdf_bytes:
        raise HTTPException(413, "Arquivo maior que o limite permitido")
    is_valid = calculate_sha256(contents) == record["pdf_hash"]
    await run_in_threadpool(store.record_audit,
        _audit_item(document_id, version_id, request.headers.get("user-agent", ""),
                    "arquivo_identico" if is_valid else "arquivo_divergente"))
    return {"valid": is_valid, "status": "autentico" if is_valid else "alterado",
            "expected_hash": record["pdf_hash"], "actual_hash": calculate_sha256(contents)}


@router.get("/admin/checklists", dependencies=[Depends(secure_admin)])
async def admin_documents(limit: int = 50):
    return await run_in_threadpool(store.list_documents, min(max(limit, 1), 200))


@router.get("/admin/audits", dependencies=[Depends(secure_admin)])
async def admin_audits(limit: int = 100):
    return await run_in_threadpool(store.list_audits, min(max(limit, 1), 200))
