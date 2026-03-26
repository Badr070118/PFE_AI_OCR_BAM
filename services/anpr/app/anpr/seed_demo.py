from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func, insert, select

from app.anpr.database import employees, init_db, parking_logs, unknown_detections, vehicles
from app.db import engine


def seed_demo_data() -> None:
    init_db()
    now = datetime.now()
    start_day = now.date() - timedelta(days=6)

    demo_employees = [
        {
            "full_name": "Sara El Amrani",
            "plate_number": "12345-A-9",
            "department": "Finance",
            "employee_code": "EMP-001",
            "is_active": True,
        },
        {
            "full_name": "Omar Lahyani",
            "plate_number": "56789-B-2",
            "department": "IT",
            "employee_code": "EMP-002",
            "is_active": True,
        },
        {
            "full_name": "Nadia Toumi",
            "plate_number": "24680-C-7",
            "department": "HR",
            "employee_code": "EMP-003",
            "is_active": True,
        },
    ]

    with engine.begin() as connection:
        existing_employees = connection.execute(select(func.count()).select_from(employees)).scalar() or 0
        if existing_employees:
            return
        connection.execute(insert(employees), demo_employees)

        for employee in demo_employees:
            connection.execute(
                insert(vehicles).values(
                    plate_number=employee["plate_number"],
                    owner_name=employee["full_name"],
                    vehicle_type=employee["department"],
                    status="AUTHORIZED",
                )
            )

        logs = []
        for index, employee in enumerate(demo_employees):
            for day_offset in range(7):
                current_day = start_day + timedelta(days=day_offset)
                entry_base = time(hour=8 + index, minute=30)
                if day_offset == 2 and index == 1:
                    entry_base = time(hour=9, minute=40)
                entry_time = datetime.combine(current_day, entry_base)

                exit_time = datetime.combine(current_day, time(hour=17, minute=30))
                if day_offset == 4 and index == 2:
                    exit_time = None

                logs.append(
                    {
                        "plate_number": employee["plate_number"],
                        "entry_time": entry_time,
                        "exit_time": exit_time,
                        "status": "AUTHORIZED",
                        "image_path": None,
                    }
                )

        connection.execute(insert(parking_logs), logs)
        connection.execute(
            insert(unknown_detections).values(
                plate_number="99999-Z-1",
                image_path=None,
                detected_at=datetime.combine(start_day + timedelta(days=1), time(hour=11, minute=12)),
            )
        )


if __name__ == "__main__":
    seed_demo_data()
