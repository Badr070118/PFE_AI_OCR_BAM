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
