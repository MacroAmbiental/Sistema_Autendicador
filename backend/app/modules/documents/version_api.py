"""API de autenticacao entre sistemas: versoes publicas imutaveis."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.firebase import get_firebase_app
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


def secure_viewer(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Login obrigatorio para validar documento")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, "Token de acesso ausente")

    try:
        get_firebase_app()
        from firebase_admin import auth
    except Exception as exc:
        raise HTTPException(503, "Firebase Admin nao configurado para validacao de login") from exc

    try:
        decoded = auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(401, "Token Firebase invalido ou expirado") from exc

    return {
        "uid": str(decoded.get("uid") or ""),
        "email": str(decoded.get("email") or "").strip() or None,
        "name": str(decoded.get("name") or "").strip() or None,
    }


def _audit_item(document_id: str, version_id: str, user_agent: str, result: str, viewer: dict | None = None) -> dict:
    device = "Mobile" if any(marker in user_agent.lower() for marker in ("mobile", "android", "iphone")) else "Desktop"
    payload = {
        "document_id": document_id,
        "version_id": version_id,
        "device": device,
        "datetime_br": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S"),
        "result": result,
    }
    if viewer:
        payload["viewer_uid"] = viewer.get("uid")
        payload["viewer_email"] = viewer.get("email")
        payload["viewer_name"] = viewer.get("name")
    return payload


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


def _normalize_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())


def _source_alias_for_url(source: str | None) -> str:
    raw = (source or "documentos").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug or "documentos"


def _select_versions_by_source(records: list[dict], source_alias: str) -> list[dict]:
    normalized_alias = _normalize_alias(source_alias)
    if not normalized_alias:
        return []
    return [record for record in records if _normalize_alias(str(record.get("source", ""))) == normalized_alias]


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
    if settings.app_env.lower() == "production":
        link = urlsplit(settings.verification_base_url)
        if (link.scheme != "https" or not link.hostname or
                link.hostname in {"localhost", "127.0.0.1", "::1"} or
                link.hostname.endswith(".localhost")):
            raise RuntimeError("Configure VERIFICATION_BASE_URL com o dominio HTTPS publico antes de autenticar PDFs")
    source_alias = _source_alias_for_url(request.source)
    verification_url = (
        settings.verification_base_url.rstrip("/")
        + "/Validador/"
        + quote(source_alias, safe="")
        + "/"
        + quote(request.document_id, safe="")
    )
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
async def versions(document_id: str, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if not document_id or len(document_id) > 160 or not document_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Documento invalido")
    root = await run_in_threadpool(store.get_document, document_id)
    if not root:
        raise HTTPException(404, "Documento nao encontrado")
    records = await run_in_threadpool(store.list_versions, document_id)
    return {"document_id": document_id, "latest_version": root.get("latest_version"),
            "versions": [_sanitize_metadata(v) for v in records]}


@router.get("/verify/{document_id}/{version_id}")
async def verify_public(document_id: str, version_id: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
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


@router.get("/validator/{source_alias}/{document_id}")
async def validate_by_source(
    document_id: str,
    source_alias: str,
    request: Request,
    response: Response,
    viewer: dict = Depends(secure_viewer),
):
    response.headers["Cache-Control"] = "no-store"
    if not document_id or len(document_id) > 160 or not document_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Documento invalido")

    doc = await run_in_threadpool(store.get_document, document_id)
    if not doc:
        raise HTTPException(404, "Documento nao encontrado")

    records = await run_in_threadpool(store.list_versions, document_id)
    scoped_versions = _select_versions_by_source(records, source_alias)
    if not scoped_versions:
        raise HTTPException(404, "Nenhuma versao encontrada para o apelido informado")

    current = scoped_versions[-1]
    version_id = current["version_id"]
    try:
        pdf_bytes = await run_in_threadpool(store.get_file, document_id, version_id, "pdf")
        snapshot = await run_in_threadpool(store.get_file, document_id, version_id, "json")
        valid = (calculate_sha256(pdf_bytes) == current["pdf_hash"] and calculate_sha256(snapshot) == current["content_hash"])
    except Exception:
        valid = False

    result = "autentico" if valid else "integridade_comprometida"
    await run_in_threadpool(
        store.record_audit,
        _audit_item(document_id, version_id, request.headers.get("user-agent", ""), f"validador_{result}", viewer),
    )

    versions_payload = [
        {
            "version_id": version.get("version_id"),
            "number": version.get("number"),
            "created_at": version.get("created_at"),
            "team_name": version.get("source"),
            "signature_status": version.get("signature_status"),
        }
        for version in scoped_versions
    ]

    return {
        "document_id": document_id,
        "source_alias": source_alias,
        "title": current.get("title"),
        "document_type": current.get("document_type"),
        "reference_period": current.get("reference_period"),
        "signature_status": current.get("signature_status"),
        "version_id": version_id,
        "version_number": current.get("number"),
        "latest_version": scoped_versions[-1].get("number"),
        "pdf_hash": current.get("pdf_hash"),
        "pdf_path": f"/api/v1/verify/{document_id}/{version_id}/pdf",
        "valid": valid,
        "status": result,
        "versions": versions_payload,
    }


@router.post("/validator/{source_alias}/{document_id}/file")
async def compare_file_by_source(
    source_alias: str,
    document_id: str,
    request: Request,
    file: UploadFile = File(...),
    viewer: dict = Depends(secure_viewer),
):
    records = await run_in_threadpool(store.list_versions, document_id)
    scoped_versions = _select_versions_by_source(records, source_alias)
    if not scoped_versions:
        raise HTTPException(404, "Nenhuma versao encontrada para o apelido informado")

    current = scoped_versions[-1]
    version_id = current["version_id"]
    contents = await file.read(settings.max_pdf_bytes + 1)
    if len(contents) > settings.max_pdf_bytes:
        raise HTTPException(413, "Arquivo maior que o limite permitido")

    actual_hash = calculate_sha256(contents)
    is_valid = actual_hash == current["pdf_hash"]
    await run_in_threadpool(
        store.record_audit,
        _audit_item(
            document_id,
            version_id,
            request.headers.get("user-agent", ""),
            "validador_arquivo_identico" if is_valid else "validador_arquivo_divergente",
            viewer,
        ),
    )

    return {
        "valid": is_valid,
        "status": "autentico" if is_valid else "alterado",
        "document_id": document_id,
        "source_alias": source_alias,
        "version_id": version_id,
        "expected_hash": current["pdf_hash"],
        "actual_hash": actual_hash,
    }


@router.get("/admin/checklists", dependencies=[Depends(secure_admin)])
async def admin_documents(limit: int = 50):
    return await run_in_threadpool(store.list_documents, min(max(limit, 1), 200))


@router.get("/admin/audits", dependencies=[Depends(secure_admin)])
async def admin_audits(limit: int = 100):
    return await run_in_threadpool(store.list_audits, min(max(limit, 1), 200))
