"""Проставляет buildings.cooling_provider для зон district cooling.

Только там, где провайдер известен достоверно (зоны Empower: Dubai Marina/JLT
и Downtown/Business Bay). Прочие районы оставляем NULL — провайдер там иной
(Emicool/Tabreed/пр.) и его тарифов у нас нет, поэтому cooling_est честно
не считается (не выдумываем).

Запуск: python -m etl.jobs.assign_cooling_provider
"""
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging

log = get_logger(__name__)

# (min_lat, min_lon, max_lat, max_lon) — достоверные зоны Empower
EMPOWER_BBOXES = [
    (25.055, 55.125, 25.095, 55.162),  # Dubai Marina + JLT
    (25.170, 55.245, 25.210, 55.290),  # Downtown + Business Bay
]


def main() -> None:
    setup_logging()
    db = SessionLocal()
    try:
        total = 0
        for min_lat, min_lon, max_lat, max_lon in EMPOWER_BBOXES:
            res = db.execute(
                text(
                    """
                    UPDATE buildings SET cooling_provider = 'empower'
                    WHERE cooling_provider IS NULL
                      AND ST_Y(centroid::geometry) BETWEEN :min_lat AND :max_lat
                      AND ST_X(centroid::geometry) BETWEEN :min_lon AND :max_lon
                    """
                ),
                {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
            )
            total += res.rowcount or 0
        db.commit()
        log.info("cooling_provider_assigned", provider="empower", buildings=total)
    finally:
        db.close()


if __name__ == "__main__":
    main()
