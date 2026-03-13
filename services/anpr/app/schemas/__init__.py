"""Service-level schemas for smart parking ANPR."""

from app.schemas.anpr import AskRequest, AskResponse, DetectDecision, DetectResponse, ExitResponse

__all__ = ["AskRequest", "AskResponse", "DetectDecision", "DetectResponse", "ExitResponse"]
