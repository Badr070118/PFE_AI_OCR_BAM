"""Service-level schemas for smart parking ANPR."""

from app.schemas.anpr import (
    AskRequest,
    AskResponse,
    AuthorizedEmployeeRequest,
    AuthorizedEmployeeResponse,
    DetectDecision,
    DetectResponse,
    ExitResponse,
)
from app.schemas.report import ReportGenerateResponse, ReportListItem, ReportPreviewResponse, ReportRequest

__all__ = [
    "AskRequest",
    "AskResponse",
    "DetectDecision",
    "DetectResponse",
    "ExitResponse",
    "AuthorizedEmployeeRequest",
    "AuthorizedEmployeeResponse",
    "ReportRequest",
    "ReportPreviewResponse",
    "ReportGenerateResponse",
    "ReportListItem",
]
