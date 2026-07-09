"""Загрузка достопримечательностей/POI из OSM Overpass для маркеров на карте.

Категории: attraction (tourism=*), mall (shop=mall), park (leisure=park),
beach (natural=beach), metro (railway=station+subway). Точка = центр объекта
(node как есть, way/relation через 'out center'). Дедуп по osm_ref.

Запуск:
    python -m etl.jobs.fetch_pois              # все пилотные районы
    python -m etl.jobs.fetch_pois marina_jlt   # один район
"""
import sys
import time

import httpx
from shapely.geometry import Point
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.jobs.fetch_osm_buildings import HEADERS, OVERPASS_URL, PILOT_AREAS

log = get_logger(__name__)

QUERY_TEMPLATE = """
[out:json][timeout:120];
(
  node["tourism"~"attraction|museum|theme_park|viewpoint|gallery|aquarium|zoo"]({bbox});
  way["tourism"~"attraction|museum|theme_park|viewpoint|gallery|aquarium|zoo"]({bbox});
  node["shop"="mall"]({bbox});
  way["shop"="mall"]({bbox});
  node["leisure"="park"]({bbox});
  way["leisure"="park"]({bbox});
  node["natural"="beach"]({bbox});
  way["natural"="beach"]({bbox});
  node["railway"="station"]["station"="subway"]({bbox});
);
out center tags;
"""


def categorize(tags: dict) -> str | None:
    if tags.get("tourism"):
        return "attraction"
    if tags.get("shop") == "mall":
        return "mall"
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("natural") == "beach":
        return "beach"
    if tags.get("railway") == "station":
        return "metro"
    return None


def element_point(el: dict) -> Point | None:
    if el["type"] == "node":
        return Point(el["lon"], el["lat"])
    center = el.get("center")
    return Point(center["lon"], center["lat"]) if center else None


def fetch_area(area: str, bbox: tuple[float, float, float, float]) -> int:
    query = QUERY_TEMPLATE.format(bbox=",".join(str(c) for c in bbox))
    resp = httpx.post(OVERPASS_URL, data={"data": query}, timeout=300, headers=HEADERS)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])
    log.info("pois_fetched", area=area, elements=len(elements))

    db = SessionLocal()
    count = 0
    try:
        for el in elements:
            tags = el.get("tags", {})
            category = categorize(tags)
            name = tags.get("name:en") or tags.get("name")
            if category is None or not name:
                continue  # без названия «шарик» бессмысленный
            point = element_point(el)
            if point is None:
                continue
            osm_ref = f"osm:{el['type']}/{el['id']}"
            db.execute(
                text(
                    """
                    INSERT INTO pois (osm_ref, name_en, category, geom, source)
                    VALUES (:ref, :name, :cat, ST_GeomFromText(:wkt, 4326), 'osm')
                    ON CONFLICT (osm_ref) DO UPDATE SET
                        name_en = EXCLUDED.name_en,
                        category = EXCLUDED.category,
                        geom = EXCLUDED.geom
                    """
                ),
                {"ref": osm_ref, "name": name, "cat": category, "wkt": point.wkt},
            )
            count += 1
        db.commit()
        log.info("pois_loaded", area=area, pois=count)
        return count
    finally:
        db.close()


def main() -> None:
    setup_logging()
    areas = sys.argv[1:] or list(PILOT_AREAS)
    for i, area in enumerate(areas):
        if area not in PILOT_AREAS:
            log.error("unknown_area", area=area)
            continue
        if i > 0:
            time.sleep(10)
        try:
            fetch_area(area, PILOT_AREAS[area])
        except Exception as exc:  # noqa: BLE001 — транзиентные сбои Overpass не рушат цикл
            log.warning("pois_area_failed", area=area, error=str(exc))


if __name__ == "__main__":
    main()
