"""Сеточная догрузка ВСЕХ зданий застроенной части Дубая из OSM.

Перебирает bbox-сетку над городом и грузит здания каждой ячейки. Дедуп по
source (osm_ref) — уже загруженные здания пропускаются, повтор безопасен.

Оптимизация: ячейки, где уже загружено МНОГО зданий (COVERED_THRESHOLD),
считаем покрытыми и НЕ дёргаем Overpass повторно — это бережёт бесплатный
сервер и резко ускоряет проход (качаем только редкие/пустые ячейки = реальные
дыры + край пустыни). Зеркала Overpass — из fetch_osm_buildings.

Запуск: python -m etl.jobs.fetch_grid
"""
import time

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.jobs.fetch_osm_buildings import fetch_area_with_retry

log = get_logger(__name__)

# Застроенная часть Дубая (широкий охват; за краями — пустыня/море, вернут 0).
LAT_MIN, LAT_MAX = 24.78, 25.36
LON_MIN, LON_MAX = 54.95, 55.56
STEP = 0.05
COVERED_THRESHOLD = 1500  # ячейка с таким числом зданий считается покрытой — пропускаем


def _cell_count(db, lat, lon) -> int:
    return db.execute(
        text(
            """
            SELECT count(*) FROM buildings
            WHERE ST_Y(centroid::geometry) BETWEEN :a AND :b
              AND ST_X(centroid::geometry) BETWEEN :c AND :d
            """
        ),
        {"a": lat, "b": lat + STEP, "c": lon, "d": lon + STEP},
    ).scalar() or 0


def main() -> None:
    setup_logging()
    db = SessionLocal()
    tiles = fetched = skipped = 0
    try:
        lat = LAT_MIN
        while lat < LAT_MAX - 1e-9:
            lon = LON_MIN
            while lon < LON_MAX - 1e-9:
                tiles += 1
                existing = _cell_count(db, lat, lon)
                if existing >= COVERED_THRESHOLD:
                    skipped += 1
                    lon += STEP
                    continue
                bbox = (round(lat, 3), round(lon, 3), round(lat + STEP, 3), round(lon + STEP, 3))
                fetch_area_with_retry(f"grid_{bbox[0]}_{bbox[1]}", bbox)
                fetched += 1
                time.sleep(2)
                lon += STEP
            lat += STEP
        log.info("grid_done", tiles=tiles, fetched=fetched, skipped=skipped)
        print(f"Сетка: всего {tiles}, скачано {fetched}, пропущено покрытых {skipped}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
