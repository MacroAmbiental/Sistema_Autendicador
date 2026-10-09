"""Tests offline: Firebase e simulado por backend local explicitamente ativado."""
import base64
import hashlib
import os

import fitz
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from io import BytesIO

from app.main import app
from app.core.config import settings

client = TestClient(app)
KEY = "chave-teste-com-mais-de-32-caracteres-123"


@pytest.fixture(autouse=True)
def local_config(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_STORAGE_MODE", "local")
    monkeypatch.setenv("AUTH_LOCAL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "integration_api_key", KEY)
    monkeypatch.setattr(settings, "admin_api_key", "chave-separada-admin-mais-32-caracteres-1234")
    monkeypatch.setattr(settings, "verification_base_url", "https://verificar.exemplo.com")
    monkeypatch.setattr(settings, "app_env", "development")


def pdf_original():
    buf = BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(40, 750, "CHECKLIST ORIGINAL")
    pdf.save()
    return buf.getvalue()


def register(content, event, pdf=None, document_id="EQ01_SEMANA_20261005"):
    return client.post("/api/v1/checklists/versions", headers={"X-Integration-Key": KEY}, json={
        "document_id": document_id, "event_id": event, "title": "Checklist semanal",
        "content_json": content, "pdf_base64": base64.b64encode(pdf).decode() if pdf is not None else None,
        "signature_status": "assinado" if event == "evento-SST" else "pendente",
    })


def test_version_history_verification_and_pdf_integrity():
    assert client.post("/api/v1/checklists/versions", json={}).status_code == 503 if not settings.integration_api_key else client.post("/api/v1/checklists/versions", json={}).status_code == 401
    source = pdf_original()
    v1 = register('{"dia":"segunda","respostas":["ok"]}', "evento-1", source)
    assert v1.status_code == 201, v1.text
    d1 = v1.json()
    assert d1["number"] == 1
    assert d1["verification_url"].endswith(d1["version_id"])
    final_pdf = client.get(d1["pdf_path"])
    assert final_pdf.status_code == 200
    assert hashlib.sha256(final_pdf.content).hexdigest() == d1["pdf_hash"]
    rendered = fitz.open(stream=final_pdf.content, filetype="pdf")
    assert len(rendered[0].get_images()) >= 1
    assert "AUTENTICADOR" in rendered[0].get_text()
    rendered.close()
    verify = client.get(f"/api/v1/verify/{d1['document_id']}/{d1['version_id']}")
    assert verify.status_code == 200 and verify.json()["valid"] is True
    same = register('{"dia":"segunda","respostas":["ok"]}', "evento-1", source)
    assert same.json()["version_id"] == d1["version_id"]
    assert same.json()["number"] == 1
    v2 = register('{"dia":"terca","respostas":["nc"]}', "evento-2")
    assert v2.status_code == 201, v2.text
    assert v2.json()["number"] == 2
    sst = register('{"dia":"terca","assinaturas":{"sst":"presente"}}', "evento-SST")
    assert sst.status_code == 201
    assert sst.json()["number"] == 3
    versions = client.get("/api/v1/checklists/EQ01_SEMANA_20261005/versions").json()["versions"]
    assert [v["number"] for v in versions] == [1, 2, 3]
    first_after = client.get(f"/api/v1/verify/{d1['document_id']}/{d1['version_id']}").json()
    assert first_after["valid"] is True and first_after["is_latest"] is False
    upload = client.post(f"/api/v1/verify/{d1['document_id']}/{d1['version_id']}/file",
                         files={"file": ("f.pdf", final_pdf.content, "application/pdf")})
    assert upload.json()["valid"] is True
    tampered = bytearray(final_pdf.content); tampered[120] ^= 1
    rejected = client.post(f"/api/v1/verify/{d1['document_id']}/{d1['version_id']}/file",
                           files={"file": ("f.pdf", bytes(tampered), "application/pdf")})
    assert rejected.json()["valid"] is False
    audit = client.get("/api/v1/admin/audits", headers={"X-Admin-Key": "chave-separada-admin-mais-32-caracteres-1234"}).json()
    assert len(audit) >= 4
    assert audit[0]["datetime_br"].count("/") == 2


def test_reject_changed_reuse_and_invalid_pdf():
    assert register('{"x":1}', "evento-1").status_code == 201
    assert register('{"x":2}', "evento-1").status_code == 400
    assert register('{"x":1}', "evento-2", b"NOT PDF").status_code == 400
    assert client.get("/api/v1/admin/checklists").status_code == 401


def test_qrcode_of_each_pdf_opens_its_exact_version():
    # Teste de leitura real do QR: opcional em maquinas sem OpenCV instalado.
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    document_id = "EQUIP_ESTOQUE_5_MODELO_9_SEMANA_20261005"
    versions = []
    for idx in range(2):
        reply = register('{"resposta": %d}' % idx, "alteracao-%d" % idx, pdf_original(), document_id=document_id)
        assert reply.status_code == 201, reply.text
        record = reply.json()
        data = client.get(record["pdf_path"])
        assert data.status_code == 200
        pdf = fitz.open(stream=data.content, filetype="pdf")
        pixel = pdf[0].get_pixmap(matrix=fitz.Matrix(4, 4))
        image = np.frombuffer(pixel.samples, dtype=np.uint8).reshape(pixel.height, pixel.width, pixel.n)
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        qr_link, _, _ = cv2.QRCodeDetector().detectAndDecode(bgr)
        pdf.close()
        assert qr_link == record["verification_url"]
        assert qr_link.endswith("/" + record["version_id"])
        versions.append(record)
    assert versions[0]["verification_url"] != versions[1]["verification_url"]
    old = client.get("/api/v1/verify/" + document_id + "/" + versions[0]["version_id"]).json()
    assert old["valid"] is True and old["is_latest"] is False
