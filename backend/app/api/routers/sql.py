import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from psycopg import sql

router = APIRouter(prefix="/sql", tags=["SQL"])


class SqlConnectionRequest(BaseModel):
    connection_string: str = Field(..., min_length=10)
    table_name: str = Field(..., min_length=2, max_length=128)
    limit: int = Field(default=100, ge=1, le=500)


class SqlDocumentCreateRequest(BaseModel):
    connection_string: str = Field(..., min_length=10)
    table_name: str = Field(..., min_length=2, max_length=128)
    title: str = Field(..., min_length=1, max_length=255)
    document_type: str | None = Field(default=None, max_length=120)
    reference_period: str | None = Field(default=None, max_length=120)
    owner_name: str | None = Field(default=None, max_length=180)
    content: str = ""
    collection_name: str | None = Field(default=None, max_length=120)


class SqlDocumentUpdateRequest(BaseModel):
    connection_string: str = Field(..., min_length=10)
    table_name: str = Field(..., min_length=2, max_length=128)
    title: str | None = Field(default=None, max_length=255)
    document_type: str | None = Field(default=None, max_length=120)
    reference_period: str | None = Field(default=None, max_length=120)
    owner_name: str | None = Field(default=None, max_length=180)
    content: str | None = None
    collection_name: str | None = Field(default=None, max_length=120)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def _normalize_hashes(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value]
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        return [raw_value] if raw_value else []
    return [str(raw_value)]


def _validate_postgres_url(connection_string: str) -> str:
    normalized_url = connection_string.strip()
    if not normalized_url:
        raise ValueError("Informe a string de conexão do Render.")
    if not normalized_url.lower().startswith(("postgresql://", "postgres://")):
        raise ValueError("Use uma string de conexão PostgreSQL válida do Render.")
    return normalized_url


def _fetch_table_columns(connection_string: str, table_name: str) -> set[str]:
    with psycopg.connect(_validate_postgres_url(connection_string), connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                  AND table_schema = current_schema()
                """,
                (table_name,),
            )
            rows = cursor.fetchall()

            values: set[str] = set()
            for row in rows:
                if isinstance(row, dict):
                    for key in row.keys():
                        if key is not None:
                            values.add(str(key).lower())
                elif row:
                    value = row[0] if isinstance(row, (list, tuple)) else row
                    if value is not None:
                        values.add(str(value).lower())
            return values


def _build_record_dict(fields: dict[str, Any], columns: set[str]) -> dict[str, Any]:
    return {
        key: value
        for key, value in fields.items()
        if key in columns and value is not None
    }


def _coerce_row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)

    columns = [column.name for column in getattr(cursor, "description", []) or []]
    if columns and isinstance(row, (list, tuple)):
        return dict(zip(columns, row, strict=False))
    return dict(row) if isinstance(row, dict) else {}


def read_sql_table(connection_string: str, table_name: str, limit: int = 100) -> list[dict[str, Any]]:
    normalized_url = _validate_postgres_url(connection_string)

    with psycopg.connect(normalized_url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            query = sql.SQL("SELECT * FROM {} ORDER BY 1 LIMIT %s").format(sql.Identifier(table_name))
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            if not rows:
                return []

            if isinstance(rows[0], dict):
                return [dict(row) for row in rows]

            columns = [column.name for column in getattr(cursor, "description", []) or []]
            if not columns and isinstance(rows[0], (list, tuple)):
                columns = [f"column_{index + 1}" for index in range(len(rows[0]))]

            return [dict(zip(columns, row, strict=False)) for row in rows]


@router.post("/connect")
async def connect_sql_table(payload: SqlConnectionRequest):
    try:
        rows = read_sql_table(payload.connection_string, payload.table_name, payload.limit)
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "status": "connected",
        "table_name": payload.table_name,
        "count": len(rows),
        "rows": rows,
    }


@router.post("/documents")
async def create_sql_document(payload: SqlDocumentCreateRequest):
    try:
        normalized_url = _validate_postgres_url(payload.connection_string)
        columns = _fetch_table_columns(normalized_url, payload.table_name)
        content = (payload.content or "").strip()
        now = datetime.now(timezone.utc).isoformat()
        hashes = [_hash_content(content)] if content else []
        table_name = payload.table_name.strip()
        collection_name = (payload.collection_name or table_name).strip() or table_name

        record = {
            "title": payload.title.strip(),
            "document_type": payload.document_type.strip() if payload.document_type else None,
            "reference_period": payload.reference_period.strip() if payload.reference_period else None,
            "owner_name": payload.owner_name.strip() if payload.owner_name else None,
            "content": content,
            "collection_name": collection_name,
            "status": "created",
            "hashes": json.dumps(hashes),
            "created_at": now,
            "updated_at": now,
        }

        fields = _build_record_dict(record, columns)
        if not fields:
            raise ValueError("A tabela informada não contém colunas compatíveis para autenticação de documentos.")

        column_names = list(fields.keys())

        with psycopg.connect(normalized_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
                        sql.Identifier(table_name),
                        sql.SQL(", ").join(sql.Identifier(column_name) for column_name in column_names),
                        sql.SQL(", ").join(sql.Placeholder() for _ in column_names),
                    ),
                    list(fields.values()),
                )
                rows = cursor.fetchall()
                row = rows[0] if rows else cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível inserir o registro na tabela SQL.",
            )

        if isinstance(row, dict):
            response = dict(row)
        else:
            response = _coerce_row_mapping(cursor, row)
            if not response:
                response = {key: value for key, value in zip(column_names, row, strict=False)}
        response["hashes"] = hashes
        response["status"] = "created"
        response["collection_name"] = collection_name
        return response
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/documents/{record_id}")
async def update_sql_document(record_id: str, payload: SqlDocumentUpdateRequest):
    try:
        normalized_url = _validate_postgres_url(payload.connection_string)
        table_name = payload.table_name.strip()
        with psycopg.connect(normalized_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                query = sql.SQL("SELECT * FROM {} WHERE id = %s OR public_id = %s LIMIT 1").format(sql.Identifier(table_name))
                cursor.execute(query, (record_id, record_id))
                rows = cursor.fetchall()
                row = rows[0] if rows else None
                if row is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro não encontrado na tabela SQL.")

                row_data = _coerce_row_mapping(cursor, row)

                updated_content = payload.content.strip() if payload.content is not None else row_data.get("content", "")
                updated_title = payload.title.strip() if payload.title is not None else row_data.get("title", "")
                updated_document_type = payload.document_type.strip() if payload.document_type is not None else row_data.get("document_type")
                updated_reference_period = payload.reference_period if payload.reference_period is not None else row_data.get("reference_period")
                updated_owner_name = payload.owner_name.strip() if payload.owner_name is not None else row_data.get("owner_name")
                updated_collection_name = payload.collection_name.strip() if payload.collection_name is not None else row_data.get("collection_name", table_name)

                existing_hashes = _normalize_hashes(row_data.get("hashes"))
                new_hash = _hash_content(updated_content)
                final_hashes = [*existing_hashes, new_hash]

                update_values = {
                    "title": updated_title,
                    "document_type": updated_document_type,
                    "reference_period": updated_reference_period,
                    "owner_name": updated_owner_name,
                    "content": updated_content,
                    "collection_name": updated_collection_name,
                    "status": "updated",
                    "hashes": json.dumps(final_hashes),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                allowed_columns = _fetch_table_columns(normalized_url, table_name)
                update_fields = _build_record_dict(update_values, allowed_columns)
                if not update_fields:
                    raise ValueError("A tabela informada não contém colunas compatíveis para atualização de documentos.")

                assignments = [sql.SQL("{} = %s").format(sql.Identifier(column)) for column in update_fields]
                query = sql.SQL("UPDATE {} SET {} WHERE id = %s OR public_id = %s").format(
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(assignments),
                )
                cursor.execute(query, [*update_fields.values(), record_id, record_id])

                cursor.execute(
                    sql.SQL("SELECT * FROM {} WHERE id = %s OR public_id = %s LIMIT 1").format(sql.Identifier(table_name)),
                    (record_id, record_id),
                )
                updated_rows = cursor.fetchall()
                updated_row = updated_rows[0] if updated_rows else None
                if updated_row is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível recuperar o registro atualizado.")

                result = _coerce_row_mapping(cursor, updated_row)
                result.update(
                    {
                        "title": updated_title,
                        "document_type": updated_document_type,
                        "reference_period": updated_reference_period,
                        "owner_name": updated_owner_name,
                        "content": updated_content,
                        "collection_name": updated_collection_name,
                        "status": "updated",
                        "hashes": final_hashes,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                return result
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
