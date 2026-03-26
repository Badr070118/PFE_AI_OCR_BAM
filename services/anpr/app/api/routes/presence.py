from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from app.anpr.presence_service import getPresenceOverviewDashboard, getRealAnomalies, _parse_date

router = APIRouter(tags=["presence"])


@router.get("/anpr/presence/overview")
def presence_overview(date: str | None = None) -> dict:
    target = _parse_date(date) if date else None
    if date and not target:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD expected)")
    return getPresenceOverviewDashboard(target)


@router.get("/anpr/presence/anomalies")
def presence_anomalies(start_date: str | None = None, end_date: str | None = None) -> dict:
    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else None
    if (start_date and not start) or (end_date and not end):
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD expected)")
    return getRealAnomalies(start, end)


__all__ = ["router"]
