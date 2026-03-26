from __future__ import annotations

from datetime import date, datetime, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.anpr.attendance import AttendanceConfig, aggregate_attendance
from app.anpr.pdf_report import build_attendance_pdf
from app.api.routes import reports as reports_router


def test_daily_aggregation_late_and_incomplete(monkeypatch):
    def fake_config():
        return AttendanceConfig(standard_start=time(hour=9, minute=0), late_minutes=15, dedup_minutes=5)

    def fake_employees():
        return [
            {
                "full_name": "Sara",
                "plate_number": "AAA-1",
                "department": "IT",
                "employee_code": "EMP-1",
                "is_active": True,
            },
            {
                "full_name": "Omar",
                "plate_number": "BBB-2",
                "department": "HR",
                "employee_code": "EMP-2",
                "is_active": True,
            },
        ]

    def fake_vehicles():
        return [
            {
                "owner_name": "Sara",
                "plate_number": "AAA-1",
                "vehicle_type": "IT",
                "status": "AUTHORIZED",
            },
            {
                "owner_name": "Omar",
                "plate_number": "BBB-2",
                "vehicle_type": "HR",
                "status": "AUTHORIZED",
            },
        ]

    def fake_logs(*_args, **_kwargs):
        day = date(2026, 3, 26)
        return [
            {
                "plate_number": "AAA-1",
                "entry_time": datetime.combine(day, time(hour=9, minute=5)),
                "exit_time": datetime.combine(day, time(hour=17, minute=0)),
                "status": "AUTHORIZED",
            },
            {
                "plate_number": "BBB-2",
                "entry_time": datetime.combine(day, time(hour=9, minute=40)),
                "exit_time": None,
                "status": "AUTHORIZED",
            },
        ]

    def fake_unknown(*_args, **_kwargs):
        return []

    monkeypatch.setattr("app.anpr.attendance.build_attendance_config", fake_config)
    monkeypatch.setattr("app.anpr.attendance.fetch_employees", fake_employees)
    monkeypatch.setattr("app.anpr.attendance.fetch_vehicles", fake_vehicles)
    monkeypatch.setattr("app.anpr.attendance.fetch_parking_logs_range", fake_logs)
    monkeypatch.setattr("app.anpr.attendance.fetch_unknown_detections_range", fake_unknown)

    result = aggregate_attendance(date(2026, 3, 26), date(2026, 3, 26))
    summary = result["summary"]
    assert summary["total_employees"] == 2
    assert summary["employees_present"] == 2
    assert summary["total_late"] == 1

    employees = {emp["plate_number"]: emp for emp in result["employees"]}
    assert employees["AAA-1"]["late_count"] == 0
    assert employees["BBB-2"]["late_count"] == 1
    assert employees["BBB-2"]["anomalies_count"] == 1


def test_pdf_generation(tmp_path):
    report = {
        "report_type": "daily",
        "start_date": date(2026, 3, 26),
        "end_date": date(2026, 3, 26),
        "generated_at": datetime(2026, 3, 26, 10, 0, 0),
        "summary": {
            "total_employees": 1,
            "employees_present": 1,
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
    build_attendance_pdf(report, output)
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


@pytest.mark.parametrize("report_id", [1])
def test_generate_endpoint(monkeypatch, report_id):
    sample = {
        "report_id": report_id,
        "report_type": "daily",
        "start_date": date(2026, 3, 26),
        "end_date": date(2026, 3, 26),
        "generated_at": datetime(2026, 3, 26, 10, 0, 0),
        "file_name": "demo.pdf",
        "summary": {
            "total_employees": 0,
            "employees_present": 0,
            "total_presences": 0,
            "total_late": 0,
            "total_anomalies": 0,
            "total_presence_minutes": 0.0,
            "avg_presence_minutes": 0.0,
            "first_arrival": {"timestamp": None, "employee": None},
            "last_exit": {"timestamp": None, "employee": None},
        },
    }

    monkeypatch.setattr(reports_router, "generate_report", lambda _payload: sample)

    app = FastAPI()
    app.include_router(reports_router.router)
    client = TestClient(app)

    response = client.post("/anpr/reports/generate", json={"report_type": "daily", "date": "2026-03-26"})
    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == report_id
