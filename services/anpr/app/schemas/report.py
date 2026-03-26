from datetime import date as DateType, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    report_type: Literal["daily", "weekly", "monthly", "yearly", "custom"]
    date: Optional[DateType] = None
    year: Optional[int] = None
    week: Optional[int] = Field(default=None, ge=1, le=53)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    start_date: Optional[DateType] = None
    end_date: Optional[DateType] = None


class ReportEdge(BaseModel):
    timestamp: Optional[datetime] = None
    employee: Optional[dict[str, Any]] = None


class ReportSummary(BaseModel):
    total_employees: int
    employees_present: int
    employees_absent: int
    total_presences: int
    total_late: int
    total_anomalies: int
    total_presence_minutes: float
    avg_presence_minutes: float
    first_arrival: ReportEdge
    last_exit: ReportEdge


class EmployeeDay(BaseModel):
    date: DateType
    first_entry: Optional[datetime] = None
    last_exit: Optional[datetime] = None
    total_minutes: float
    late: bool
    status: str
    anomalies: list[str] = []


class EmployeeSummary(BaseModel):
    full_name: str
    plate_number: Optional[str] = None
    department: Optional[str] = None
    employee_code: Optional[str] = None
    is_active: bool
    days_present: int
    days_absent: int
    late_count: int
    total_minutes: float
    avg_minutes: float
    status: str
    anomalies_count: int
    daily: list[EmployeeDay]


class ReportPreviewResponse(BaseModel):
    report_type: str
    start_date: DateType
    end_date: DateType
    generated_at: datetime
    summary: ReportSummary
    employees: list[EmployeeSummary]
    anomalies: dict[str, list[dict[str, Any]]]


class ReportGenerateResponse(BaseModel):
    report_id: int
    report_type: str
    start_date: DateType
    end_date: DateType
    generated_at: datetime
    file_name: str
    download_url: str
    summary: ReportSummary


class ReportListItem(BaseModel):
    report_id: int
    report_type: str
    start_date: DateType
    end_date: DateType
    generated_at: datetime
    file_name: str
    download_url: str
    summary: Optional[dict[str, Any]] = None


__all__ = [
    "ReportRequest",
    "ReportPreviewResponse",
    "ReportGenerateResponse",
    "ReportListItem",
]
