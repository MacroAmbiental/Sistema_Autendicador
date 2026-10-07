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


def test_sql_table_connection_reads_render_database(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, *args, **kwargs):
            self.query = query

        @property
        def description(self):
            return [type('Column', (), {'name': 'id'})(), type('Column', (), {'name': 'title'})(), type('Column', (), {'name': 'document_type'})(), type('Column', (), {'name': 'owner_name'})(), type('Column', (), {'name': 'content'})()]

        def fetchall(self):
            return [
                {
                    "id": 1,
                    "title": "Documento SQL",
                    "document_type": "laudo",
                    "owner_name": "Maria",
                    "content": "Conteúdo validado",
                }
            ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self, **kwargs):
            return FakeCursor()

    monkeypatch.setattr("app.api.routers.sql.psycopg.connect", lambda *args, **kwargs: FakeConnection())

    response = client.post(
        "/api/v1/sql/connect",
        json={
            "connection_string": "postgresql://user:pass@render-host:5432/dbname",
            "table_name": "documentos",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["table_name"] == "documentos"
    assert payload["count"] == 1
    assert payload["rows"][0]["title"] == "Documento SQL"


def test_sql_document_create_and_update_in_render_table(monkeypatch):
    class FakeCursor:
        def __init__(self, *args, **kwargs):
            self.executed = []
            self.description = [
                type('Column', (), {'name': 'id'})(),
                type('Column', (), {'name': 'title'})(),
                type('Column', (), {'name': 'document_type'})(),
                type('Column', (), {'name': 'reference_period'})(),
                type('Column', (), {'name': 'owner_name'})(),
                type('Column', (), {'name': 'content'})(),
                type('Column', (), {'name': 'collection_name'})(),
                type('Column', (), {'name': 'status'})(),
                type('Column', (), {'name': 'hashes'})(),
                type('Column', (), {'name': 'created_at'})(),
                type('Column', (), {'name': 'updated_at'})(),
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, *args, **kwargs):
            self.executed.append((str(query), args, kwargs))

        def fetchall(self):
            return [
                {
                    'id': 1,
                    'title': 'Relatório SQL',
                    'document_type': 'laudo',
                    'reference_period': '2026-Q4',
                    'owner_name': 'Maria',
                    'content': 'status: pendente',
                    'collection_name': 'documentos',
                    'status': 'created',
                    'hashes': '["abc"]',
                    'created_at': '2026-01-01T00:00:00+00:00',
                    'updated_at': '2026-01-01T00:00:00+00:00',
                }
            ]

        def fetchone(self):
            return (1,)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self, **kwargs):
            return FakeCursor()

    monkeypatch.setattr("app.api.routers.sql.psycopg.connect", lambda *args, **kwargs: FakeConnection())

    create_response = client.post(
        "/api/v1/sql/documents",
        json={
            "connection_string": "postgresql://user:pass@render-host:5432/dbname",
            "table_name": "documentos",
            "title": "Relatório SQL",
            "document_type": "laudo",
            "reference_period": "2026-Q4",
            "owner_name": "Maria",
            "content": "status: pendente",
        },
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["status"] == "created"
    assert len(create_payload["hashes"]) == 1

    update_response = client.patch(
        "/api/v1/sql/documents/1",
        json={
            "connection_string": "postgresql://user:pass@render-host:5432/dbname",
            "table_name": "documentos",
            "content": "status: aprovado",
            "owner_name": "Maria",
        },
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["status"] == "updated"
    assert len(update_payload["hashes"]) == 2
