from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.anpr.reporting_service import build_report_payload, generate_report, get_report, list_reports
from app.core.config import get_settings
from app.schemas.report import ReportGenerateResponse, ReportListItem, ReportPreviewResponse, ReportRequest

router = APIRouter(tags=["reports"])


@router.post("/anpr/reports/preview", response_model=ReportPreviewResponse)
def preview_report(payload: ReportRequest) -> dict:
    try:
        report = build_report_payload(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return report


@router.post("/anpr/reports/generate", response_model=ReportGenerateResponse)
def generate_report_endpoint(payload: ReportRequest) -> dict:
    try:
        report = generate_report(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report_id = report.get("report_id")
    return {
        "report_id": report_id,
        "report_type": report.get("report_type"),
        "start_date": report.get("start_date"),
        "end_date": report.get("end_date"),
        "generated_at": report.get("generated_at"),
        "file_name": report.get("file_name"),
        "download_url": f"/api/anpr/reports/{report_id}/download",
        "summary": report.get("summary"),
    }


@router.get("/anpr/reports", response_model=list[ReportListItem])
def list_reports_endpoint(limit: int = 50) -> list[dict]:
    reports = list_reports(limit=limit)
    payload = []
    for item in reports:
        report_id = item.get("id")
        payload.append(
            {
                "report_id": report_id,
                "report_type": item.get("report_type"),
                "start_date": item.get("start_date"),
                "end_date": item.get("end_date"),
                "generated_at": item.get("generated_at"),
                "file_name": item.get("file_name"),
                "download_url": f"/api/anpr/reports/{report_id}/download",
                "summary": item.get("summary"),
            }
        )
    return payload


@router.get("/anpr/reports/{report_id}/download")
def download_report(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    settings = get_settings()
    base_dir = Path(settings.anpr_reports_dir).resolve()
    file_path = Path(report.get("file_path", "")).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    if base_dir not in file_path.parents and file_path != base_dir:
        raise HTTPException(status_code=400, detail="Invalid report path")

    return FileResponse(file_path, filename=report.get("file_name"))


__all__ = ["router"]
