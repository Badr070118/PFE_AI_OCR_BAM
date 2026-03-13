from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from app.anpr.database import (
    get_vehicle,
    insert_unknown_detection,
    log_detection,
    log_no_plate,
)


@dataclass
class DecisionResult:
    status: str
    action: str
    gate: str
    owner_name: str | None
    vehicle_type: str | None
    reason: str | None
    log_id: int
    event: str


def evaluate_plate(plate_text: str, image_path: str | None, detected_at: datetime) -> DecisionResult:
    normalized = plate_text.strip()
    normalized = normalized.replace(" | ", "-").replace("|", "-").replace(" ", "")
    arabic_range = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
    fallback = arabic_range.sub("?", normalized)
    if not normalized:
        log = log_no_plate(image_path, detected_at)
        return DecisionResult(
            status="NO_PLATE",
            action="No plate detected",
            gate="CLOSED",
            owner_name=None,
            vehicle_type=None,
            reason=None,
            log_id=log["log_id"],
            event=log["event"],
        )

    lookup_plate = normalized
    vehicle = get_vehicle(lookup_plate)
    if not vehicle and fallback != normalized:
        lookup_plate = fallback
        vehicle = get_vehicle(lookup_plate)
    log_plate = normalized if arabic_range.search(normalized) else lookup_plate
    if vehicle and vehicle.get("status") == "AUTHORIZED":
        log = log_detection(log_plate, "AUTHORIZED", image_path, detected_at)
        return DecisionResult(
            status="AUTHORIZED",
            action="Gate Opened",
            gate="OPEN",
            owner_name=vehicle.get("owner_name"),
            vehicle_type=vehicle.get("vehicle_type"),
            reason=None,
            log_id=log["log_id"],
            event=log["event"],
        )

    if vehicle and vehicle.get("status") == "BLACKLISTED":
        log = log_detection(log_plate, "BLACKLISTED", image_path, detected_at)
        return DecisionResult(
            status="BLACKLISTED",
            action="SECURITY ALERT",
            gate="CLOSED",
            owner_name=vehicle.get("owner_name"),
            vehicle_type=vehicle.get("vehicle_type"),
            reason="Suspicious vehicle",
            log_id=log["log_id"],
            event=log["event"],
        )

    insert_unknown_detection(normalized, image_path, detected_at)
    log = log_detection(normalized, "UNKNOWN", image_path, detected_at)
    return DecisionResult(
        status="UNKNOWN",
        action="Capture stored",
        gate="CLOSED",
        owner_name=None,
        vehicle_type=None,
        reason=None,
        log_id=log["log_id"],
        event=log["event"],
    )
