from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_document_success():
    payload = {
        "title": "Relatório Semanal de Atividades",
        "document_type": "weekly_report",
        "reference_period": "2026-W40",
        "owner_name": "João da Silva",
        "content": "Versão inicial do relatório",
        "collection_name": "relatorios",
    }

    response = client.post("/api/v1/documents", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert data["title"] == payload["title"]
    assert data["document_type"] == payload["document_type"]
    assert data["reference_period"] == payload["reference_period"]
    assert data["owner_name"] == payload["owner_name"]
    assert data["collection_name"] == payload["collection_name"]
    assert data["status"] == "created"
    assert len(data["hashes"]) == 1
    assert data["internal_id"]
    assert data["public_id"]
    assert data["created_at"]


def test_document_generates_new_hash_on_update():
    create_payload = {
        "title": "Controle de Aprovação",
        "document_type": "approval",
        "collection_name": "aprovacoes",
        "content": "status: pendente",
    }

    create_response = client.post("/api/v1/documents", json=create_payload)
    public_id = create_response.json()["public_id"]

    update_response = client.patch(
        f"/api/v1/documents/{public_id}",
        json={"content": "status: aprovado", "owner_name": "Maria"},
    )

    assert update_response.status_code == 200
    data = update_response.json()

    assert len(data["hashes"]) == 2
    assert data["hashes"][0] != data["hashes"][1]
    assert data["status"] == "updated"
    assert data["owner_name"] == "Maria"


def test_document_keeps_fixed_identifier_and_chained_versions():
    create_payload = {
        "title": "Checklist de Fiscalização",
        "document_id": "CHECK-000123",
        "document_type": "checklist",
        "collection_name": "checklists",
        "content": "item_1: pendente",
    }

    create_response = client.post("/api/v1/documents", json=create_payload)
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    public_id = created["public_id"]

    assert created["document_id"] == "CHECK-000123"
    assert created["version"] == 1
    assert created["previous_hash"] is None

    update_response = client.patch(
        f"/api/v1/documents/{public_id}",
        json={"content": "item_1: concluido", "document_id": "CHECK-000123"},
    )

    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()

    assert updated["document_id"] == "CHECK-000123"
    assert updated["version"] == 2
    assert updated["previous_hash"] == created["hashes"][-1]
    assert len(updated["hashes"]) == 2
    assert updated["hashes"][0] != updated["hashes"][1]


def test_legacy_sql_endpoints_are_not_exposed():
    # O SQL connector recebia um DSN arbitrario do cliente, criando risco SSRF.
    # A integracao oficial usa apenas a chave servidor-servidor e Firebase.
    assert client.post("/api/v1/sql/connect", json={}).status_code == 404
    assert client.post("/api/v1/sql/documents", json={}).status_code == 404
