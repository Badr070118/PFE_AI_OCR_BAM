from __future__ import annotations

from app.anpr.database import init_db, upsert_authorized_employee


def seed_badr() -> None:
    init_db()
    upsert_authorized_employee(
        full_name="Badr El Khadir",
        department="DSI",
        plate_number="\u206638119\u2069 - \u2067\ufeed\u2069 - \u20661\u2069",
        is_authorized=True,
    )


if __name__ == "__main__":
    seed_badr()
