from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from app.anpr.presence_service import getPresenceOverviewDashboard, _parse_date

router = APIRouter(tags=["presence"])


@router.get("/anpr/presence/overview")
def presence_overview(date: str | None = None) -> dict:
    target = _parse_date(date) if date else None
    if date and not target:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD expected)")
    return getPresenceOverviewDashboard(target)


__all__ = ["router"]
