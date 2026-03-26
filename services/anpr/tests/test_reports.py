from __future__ import annotations

from datetime import date, datetime, time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.anpr.reporting_service import buildDailyReportFromDatabase
from app.anpr.pdf_report import build_presence_pdf
from app.api.routes import reports as reports_router


def test_daily_report_real_shape(monkeypatch):
    def fake_employees():
        return [
            {
                "full_name": "Sara",
                "plate_number": "AAA-1",
                "department": "IT",
                "employee_code": "EMP-1",
                "is_active": True,
            }
        ]

    def fake_logs(*_args, **_kwargs):
        day = date(2026, 3, 26)
        return [
            {
                "id": 1,
                "plate_number": "AAA-1",
                "entry_time": datetime.combine(day, time(hour=9, minute=5)),
                "exit_time": datetime.combine(day, time(hour=17, minute=0)),
                "status": "AUTHORIZED",
            }
        ]

    def fake_unknown(*_args, **_kwargs):
        return []

    monkeypatch.setattr("app.anpr.reporting_service.fetch_employees", fake_employees)
    monkeypatch.setattr("app.anpr.reporting_service.fetch_parking_logs_range", fake_logs)
    monkeypatch.setattr("app.anpr.reporting_service.fetch_unknown_detections_range", fake_unknown)

    report = buildDailyReportFromDatabase(date(2026, 3, 26))
    assert report["summary"]["total_employees"] == 1
    assert report["employees"][0]["full_name"] == "Sara"


def test_pdf_generation(tmp_path):
    report = {
        "report_type": "daily",
        "start_date": date(2026, 3, 26),
        "end_date": date(2026, 3, 26),
        "generated_at": datetime(2026, 3, 26, 10, 0, 0),
        "summary": {
            "total_employees": 1,
            "employees_present": 1,
            "employees_absent": 0,
            "total_presences": 1,
            "total_late": 0,
            "total_anomalies": 0,
            "total_presence_minutes": 480.0,
            "avg_presence_minutes": 480.0,
            "first_arrival": {"timestamp": datetime(2026, 3, 26, 9, 0, 0), "employee": {"full_name": "Sara"}},
            "last_exit": {"timestamp": datetime(2026, 3, 26, 17, 0, 0), "employee": {"full_name": "Sara"}},
        },
        "employees": [
            {
                "full_name": "Sara",
                "plate_number": "AAA-1",
                "department": "IT",
                "employee_code": "EMP-1",
                "is_active": True,
                "days_present": 1,
                "days_absent": 0,
                "late_count": 0,
                "total_minutes": 480.0,
                "avg_minutes": 480.0,
                "status": "present",
                "anomalies_count": 0,
                "daily": [
                    {
                        "date": date(2026, 3, 26),
                        "first_entry": datetime(2026, 3, 26, 9, 0, 0),
                        "last_exit": datetime(2026, 3, 26, 17, 0, 0),
                        "total_minutes": 480.0,
                        "late": False,
                        "status": "present",
                        "anomalies": [],
                    }
                ],
            }
        ],
        "anomalies": {"entry_without_exit": [], "incoherent": [], "duplicates": [], "unknown_plates": []},
    }

    output = tmp_path / "report.pdf"
    build_presence_pdf(report, output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_preview_endpoint(monkeypatch):
    sample = {
        "report_type": "daily",
        "start_date": date(2026, 3, 26),
        "end_date": date(2026, 3, 26),
        "generated_at": datetime(2026, 3, 26, 10, 0, 0),
        "summary": {
            "total_employees": 0,
            "employees_present": 0,
            "employees_absent": 0,
            "total_presences": 0,
            "total_late": 0,
            "total_anomalies": 0,
            "total_presence_minutes": 0.0,
            "avg_presence_minutes": 0.0,
            "first_arrival": {"timestamp": None, "employee": None},
            "last_exit": {"timestamp": None, "employee": None},
        },
        "employees": [],
        "anomalies": {"entry_without_exit": [], "incoherent": [], "duplicates": [], "unknown_plates": []},
    }

    monkeypatch.setattr(reports_router, "build_report_payload", lambda _payload: sample)

    app = FastAPI()
    app.include_router(reports_router.router)
    client = TestClient(app)

    response = client.post("/anpr/reports/preview", json={"report_type": "daily", "date": "2026-03-26"})
    assert response.status_code == 200
    data = response.json()
    assert data["report_type"] == "daily"
