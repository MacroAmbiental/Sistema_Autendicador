import hashlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.hash_service import calculate_sha256

client = TestClient(app)


def test_hash_service_calculates_sha256_for_bytes():
    payload = b"documento autentico"

    assert calculate_sha256(payload) == hashlib.sha256(payload).hexdigest()


def test_authenticate_pdf_document_from_upload():
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog >>\n"
        b"endobj\n"
        b"trailer\n"
        b"<< /Root 1 0 R >>\n"
        b"%%EOF\n"
    )

    response = client.post(
        "/api/v1/documents/authenticate",
        files={"file": ("contrato.pdf", pdf_bytes, "application/pdf")},
        data={
            "title": "Contrato de Teste",
            "document_type": "contract",
            "reference_period": "2026-Q4",
            "owner_name": "Maria",
            "collection_name": "contratos",
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "autenticado"
    assert data["original_hash"]
    assert data["authenticated_hash"]
    assert data["verification_url"].endswith(f"/verificar/{data['public_id']}")


def test_verify_document_file_hash():
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog >>\n"
        b"endobj\n"
        b"trailer\n"
        b"<< /Root 1 0 R >>\n"
        b"%%EOF\n"
    )

    create_response = client.post(
        "/api/v1/documents/authenticate",
        files={"file": ("relatorio.pdf", pdf_bytes, "application/pdf")},
        data={
            "title": "Relatório",
            "document_type": "report",
            "collection_name": "relatorios",
        },
    )
    assert create_response.status_code == 201, create_response.text
    document = create_response.json()

    verification_response = client.post(
        f"/api/v1/verify/{document['public_id']}/file",
        files={"file": ("relatorio.pdf", pdf_bytes, "application/pdf")},
    )

    assert verification_response.status_code == 200, verification_response.text
    payload = verification_response.json()
    assert payload["valid"] is True
    assert payload["expected_hash"] == document["authenticated_hash"]
