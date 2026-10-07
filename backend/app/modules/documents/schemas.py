from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    document_id: Optional[str] = Field(default=None, min_length=3, max_length=120)
    document_type: str = Field(..., min_length=2, max_length=80)
    reference_period: Optional[str] = Field(default=None, max_length=80)
    owner_name: Optional[str] = Field(default=None, max_length=120)
    collection_name: str = Field(default="documents", min_length=2, max_length=120)
    content: str = Field(default="", min_length=1, max_length=20000)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    document_id: Optional[str] = Field(default=None, min_length=3, max_length=120)
    document_type: Optional[str] = Field(default=None, min_length=2, max_length=80)
    reference_period: Optional[str] = Field(default=None, max_length=80)
    owner_name: Optional[str] = Field(default=None, max_length=120)
    collection_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    content: Optional[str] = Field(default=None, min_length=1, max_length=20000)
    status: Optional[str] = Field(default=None, max_length=40)
    finalized: Optional[bool] = None


class DocumentResponse(BaseModel):
    internal_id: str
    public_id: str
    document_id: str
    title: str
    document_type: str
    reference_period: Optional[str] = None
    owner_name: Optional[str] = None
    collection_name: str
    content: str
    status: str
    version: int = 1
    previous_hash: Optional[str] = None
    finalized: bool = False
    hashes: list[str]
    created_at: datetime
    updated_at: datetime
