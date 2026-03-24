from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    file_name: str
    data: Dict[str, Any]
    raw_text: Optional[str] = None
    llama_output: Optional[str] = None
    doc_type_detection: Optional[Dict[str, Any]] = None
    structured_extraction: Optional[Dict[str, Any]] = None
    tables_html: Optional[list[Dict[str, Any]]] = None
    pdf_kind_detection: Optional[Dict[str, Any]] = None
    structured_extraction_error: Optional[str] = None
    structured_pages_html: Optional[Dict[str, Any]] = None
    structured_html: Optional[str] = None
    extracted_json_template: Optional[Dict[str, Any]] = None
    template_extraction_meta: Optional[Dict[str, Any]] = None
    date_uploaded: datetime

    class Config:
        from_attributes = True


class DocumentAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class DocumentAskResponse(BaseModel):
    answer: str
    found: bool
    fields_used: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float


class BatchItemResult(BaseModel):
    filename: str
    status: str
    document_type: Optional[str] = None
    db_id: Optional[int] = None
    error: Optional[str] = None


class BatchSummary(BaseModel):
    batch_id: int
    total_files: int
    success_count: int
    failed_count: int
    status: str
    created_at: datetime
    results: list[BatchItemResult] = Field(default_factory=list)


class BatchHistoryItem(BaseModel):
    batch_id: int
    total_files: int
    success_count: int
    failed_count: int
    status: str
    created_at: datetime
