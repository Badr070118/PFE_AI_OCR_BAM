from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: tuple[str, ...]


SCHEMA: Mapping[str, TableSchema] = {
    "vehicles": TableSchema(
        name="vehicles",
        columns=("id", "plate_number", "owner_name", "vehicle_type", "status", "created_at"),
    ),
    "employees": TableSchema(
        name="employees",
        columns=("id", "full_name", "plate_number", "department", "employee_code", "is_active", "created_at"),
    ),
    "parking_logs": TableSchema(
        name="parking_logs",
        columns=("id", "plate_number", "entry_time", "exit_time", "status", "image_path"),
    ),
    "unknown_detections": TableSchema(
        name="unknown_detections",
        columns=("id", "plate_number", "image_path", "detected_at"),
    ),
}


def allowed_tables() -> set[str]:
    return set(SCHEMA.keys())


def allowed_columns(table: str) -> set[str]:
    schema = SCHEMA.get(table)
    return set(schema.columns) if schema else set()


def is_allowed_table(table: str) -> bool:
    return table in SCHEMA


def is_allowed_column(table: str, column: str) -> bool:
    return column in allowed_columns(table)


__all__ = ["SCHEMA", "TableSchema", "allowed_tables", "allowed_columns", "is_allowed_table", "is_allowed_column"]
