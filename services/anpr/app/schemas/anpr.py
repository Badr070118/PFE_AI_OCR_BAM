from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DetectDecision(BaseModel):
    status: str
    action: str
    gate: str
    owner_name: str | None = None
    vehicle_type: str | None = None
    reason: str | None = None
    event: str = Field(default="entry")


class DetectResponse(BaseModel):
    plate_text: str
    has_plate: bool
    ocr_mode: str
    media_type: str = Field(default="image")
    decision: DetectDecision
    artifacts: dict[str, str | None]
    log_id: int
    image_path: str | None = None
    timestamp: datetime


class ExitResponse(BaseModel):
    plate_text: str | None = None
    closed: bool
    log_id: int | None = None
    message: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    intent: str | None = None
    confidence: float | None = None


class AuthorizedEmployeeRequest(BaseModel):
    full_name: str
    department: str
    plate_number: str
    is_authorized: bool = True
    employee_code: str | None = None


class AuthorizedEmployeeResponse(BaseModel):
    full_name: str
    department: str
    plate_number: str
    authorized: bool
    vehicle_id: int
    employee_id: int
