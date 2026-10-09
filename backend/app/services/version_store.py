"""Armazenamento de versoes imutaveis e auditorias.

Firebase: Firestore (indice transacional) + Cloud Storage (PDF/JSON, create-only).
Local: SOMENTE para testes ou desenvolvimento explicitamente configurado.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.firebase import get_firestore, get_storage_bucket
from app.services.hash_service import calculate_sha256

_local_lock = threading.RLock()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _local_root() -> Path:
    if settings.app_env.lower() == "production":
        raise RuntimeError("Armazenamento local proibido em producao.")
    root = Path(os.getenv("AUTH_LOCAL_DIR", settings.auth_local_dir)).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _mode():
    mode = os.getenv("AUTH_STORAGE_MODE", settings.auth_storage_mode).strip().lower()
    if mode not in {"firebase", "local"}:
        raise RuntimeError("AUTH_STORAGE_MODE deve ser firebase ou local")
    return mode


def _safe_file(root: Path, *parts: str) -> Path:
    # IDs entram apenas apos validacao na camada Pydantic.
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Identificador de documento invalido")
    return path


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write_create_only(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as file:
            file.write(data)
    except FileExistsError:
        if calculate_sha256(path.read_bytes()) != calculate_sha256(data):
            raise ValueError("Conflito: arquivo imutavel ja existe com conteudo diferente")


def _write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _local_upsert(document_id: str, version_id: str, metadata: dict, pdf: bytes, snapshot: bytes) -> dict:
    with _local_lock:
        root = _local_root()
        parent = _safe_file(root, "documents", document_id)
        version_index = parent / "versions" / (version_id + ".json")
        old = _read_json(version_index)
        if old:
            if old["content_hash"] != metadata["content_hash"] or old["source_pdf_hash"] != metadata["source_pdf_hash"]:
                raise ValueError("event_id ja utilizado para outro conteudo")
            return old
        index_path = parent / "index.json"
        index = _read_json(index_path) or {"document_id": document_id, "latest_version": 0}
        _write_create_only(parent / "files" / (version_id + ".pdf"), pdf)
        _write_create_only(parent / "snapshots" / (version_id + ".json"), snapshot)
        item = dict(metadata, version_id=version_id, number=index["latest_version"] + 1,
                    previous_version=index.get("latest_version_id"), created_at=utc_now(), state="ready")
        _write_json_atomic(version_index, item)
        index.update(latest_version=item["number"], latest_version_id=version_id,
                     updated_at=item["created_at"], title=item["title"], document_type=item["document_type"])
        _write_json_atomic(index_path, index)
        return item


def _firebase_upload(bucket, path, data, content_type):
    from google.api_core.exceptions import PreconditionFailed
    blob = bucket.blob(path)
    try:
        blob.upload_from_string(data, content_type=content_type, if_generation_match=0)
    except PreconditionFailed:
        existing = blob.download_as_bytes()
        if calculate_sha256(existing) != calculate_sha256(data):
            raise ValueError("Conflito de objeto de armazenamento imutavel")


def _firebase_upsert(document_id: str, version_id: str, metadata: dict, pdf: bytes, snapshot: bytes) -> dict:
    from firebase_admin import firestore
    db = get_firestore()
    bucket = get_storage_bucket()
    ref = db.collection("autenticacoes_checklists").document(document_id)
    ver = ref.collection("versoes").document(version_id)
    current = ver.get()
    if current.exists:
        old = current.to_dict()
        if old["content_hash"] != metadata["content_hash"] or old["source_pdf_hash"] != metadata["source_pdf_hash"]:
            raise ValueError("event_id ja utilizado para outro conteudo")
        return old
    # A indexacao so e publicada depois de ambos os blobs existirem.
    _firebase_upload(bucket, f"checklists/{document_id}/{version_id}.pdf", pdf, "application/pdf")
    _firebase_upload(bucket, f"checklists/{document_id}/{version_id}.json", snapshot, "application/json")

    @firestore.transactional
    def publish(tx):
        existing = ver.get(transaction=tx)
        if existing.exists:
            old = existing.to_dict()
            if old["content_hash"] != metadata["content_hash"] or old["source_pdf_hash"] != metadata["source_pdf_hash"]:
                raise ValueError("event_id ja utilizado para outro conteudo")
            return old
        current_root = ref.get(transaction=tx)
        index = current_root.to_dict() if current_root.exists else {}
        now = utc_now()
        item = dict(metadata, version_id=version_id, number=int(index.get("latest_version", 0)) + 1,
                    previous_version=index.get("latest_version_id"), created_at=now, state="ready")
        tx.set(ver, item)
        tx.set(ref, {"document_id": document_id, "latest_version": item["number"],
                     "latest_version_id": version_id, "title": item["title"],
                     "document_type": item["document_type"], "updated_at": now}, merge=True)
        return item

    return publish(db.transaction())


def save_version(document_id: str, version_id: str, metadata: dict, pdf: bytes, snapshot: bytes):
    if _mode() == "local":
        return _local_upsert(document_id, version_id, metadata, pdf, snapshot)
    return _firebase_upsert(document_id, version_id, metadata, pdf, snapshot)


def get_document(document_id: str) -> dict | None:
    if _mode() == "local":
        return _read_json(_safe_file(_local_root(), "documents", document_id, "index.json"))
    snap = get_firestore().collection("autenticacoes_checklists").document(document_id).get()
    return snap.to_dict() if snap.exists else None


def get_version(document_id: str, version_id: str) -> dict | None:
    if _mode() == "local":
        return _read_json(_safe_file(_local_root(), "documents", document_id, "versions", version_id + ".json"))
    snap = get_firestore().collection("autenticacoes_checklists").document(document_id).collection("versoes").document(version_id).get()
    return snap.to_dict() if snap.exists else None


def list_versions(document_id: str) -> list[dict]:
    if _mode() == "local":
        folder = _safe_file(_local_root(), "documents", document_id, "versions")
        records = [_read_json(f) for f in folder.glob("*.json")] if folder.exists() else []
    else:
        ref = get_firestore().collection("autenticacoes_checklists").document(document_id)
        records = [snap.to_dict() for snap in ref.collection("versoes").stream()]
    return sorted((r for r in records if r and r.get("state") == "ready"), key=lambda r: r["number"])


def get_file(document_id: str, version_id: str, extension: str) -> bytes:
    if extension not in {"pdf", "json"}:
        raise ValueError("Formato nao permitido")
    if _mode() == "local":
        subfolder = "files" if extension == "pdf" else "snapshots"
        return _safe_file(_local_root(), "documents", document_id, subfolder, version_id + "." + extension).read_bytes()
    return get_storage_bucket().blob(f"checklists/{document_id}/{version_id}.{extension}").download_as_bytes()


def record_audit(data: dict):
    data = dict(data, audit_id=uuid.uuid4().hex, timestamp_utc=utc_now())
    if _mode() == "local":
        with _local_lock:
            root = _local_root()
            _write_json_atomic(_safe_file(root, "audit", data["audit_id"] + ".json"), data)
    else:
        get_firestore().collection("auditoria_consultas").document(data["audit_id"]).set(data)


def list_documents(limit=100):
    if _mode() == "local":
        root = _safe_file(_local_root(), "documents")
        results = [_read_json(f) for f in root.glob("*/index.json")] if root.exists() else []
        return sorted((r for r in results if r), key=lambda r: r.get("updated_at", ""), reverse=True)[:limit]
    return [s.to_dict() for s in get_firestore().collection("autenticacoes_checklists").limit(limit).stream()]


def list_audits(limit=100):
    if _mode() == "local":
        root = _safe_file(_local_root(), "audit")
        rows = [_read_json(f) for f in root.glob("*.json")] if root.exists() else []
        return sorted((r for r in rows if r), key=lambda r: r["timestamp_utc"], reverse=True)[:limit]
    from google.cloud.firestore_v1 import Query
    ref = get_firestore().collection("auditoria_consultas")
    return [s.to_dict() for s in ref.order_by("timestamp_utc", direction=Query.DESCENDING).limit(limit).stream()]
