"""Загрузка полигонов зданий пилотных районов из OSM Overpass API (бесплатно).

Запуск:
    python -m etl.jobs.fetch_osm_buildings              # все пилотные районы
    python -m etl.jobs.fetch_osm_buildings marina_jlt   # один район

Дедупликация по source='osm:way/123' — повторный запуск безопасен.
Overture Maps (см. README) — альтернатива с лучшими высотами; этот джоб
даёт рабочий гео-слой без DuckDB.
"""
import re
import sys
import time

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from app.models import Building

log = get_logger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# bbox: (min_lat, min_lon, max_lat, max_lon) — порядок Overpass
PILOT_AREAS: dict[str, tuple[float, float, float, float]] = {
    "marina_jlt": (25.055, 55.125, 25.095, 55.162),        # Dubai Marina + JLT
    "downtown_businessbay": (25.170, 55.245, 25.210, 55.290),
    "jvc": (25.045, 55.195, 25.075, 55.225),               # Jumeirah Village Circle
}

QUERY_TEMPLATE = """
[out:json][timeout:180];
(
  way["building"]({bbox});
  relation["building"]["type"="multipolygon"]({bbox});
);
out body geom;
"""


def parse_height(value: str | None) -> float | None:
    """OSM height: '123', '123.5 m' -> метры."""
    if not value:
        return None
    m = re.match(r"^\s*(\d+(?:\.\d+)?)", str(value))
    return float(m.group(1)) if m else None


def parse_year(value: str | None) -> int | None:
    """OSM start_date: '1998', '1998-05-01' -> год."""
    if not value:
        return None
    m = re.match(r"^\s*(\d{4})", str(value))
    if not m:
        return None
    year = int(m.group(1))
    return year if 1950 <= year <= 2035 else None


def way_to_polygon(geometry: list[dict]) -> Polygon | None:
    """Overpass 'out geom' у way: [{'lat':..,'lon':..}, ...] -> Polygon."""
    if not geometry or len(geometry) < 4:
        return None
    coords = [(p["lon"], p["lat"]) for p in geometry]
    if coords[0] != coords[-1]:
        return None  # не замкнут — не полигон
    poly = Polygon(coords)
    return poly if poly.is_valid and poly.area > 0 else None


def relation_to_polygon(members: list[dict]) -> Polygon | MultiPolygon | None:
    """Multipolygon-relation: склеиваем outer-кольца (inner для карты не критичны)."""
    outers = []
    for m in members:
        if m.get("role") == "outer" and m.get("geometry"):
            poly = way_to_polygon(m["geometry"])
            if poly:
                outers.append(poly)
    if not outers:
        return None
    return outers[0] if len(outers) == 1 else MultiPolygon(outers)


def element_to_feature(el: dict) -> dict | None:
    """Overpass element -> {geom, name, height, floors, year, osm_ref} или None."""
    if el["type"] == "way":
        geom = way_to_polygon(el.get("geometry", []))
    elif el["type"] == "relation":
        geom = relation_to_polygon(el.get("members", []))
    else:
        return None
    if geom is None:
        return None
    tags = el.get("tags", {})
    return {
        "geom": geom,
        "name": tags.get("name:en") or tags.get("name"),
        "height": parse_height(tags.get("height")),
        "floors": tags.get("building:levels"),
        "year": parse_year(tags.get("start_date")),
        "osm_ref": f"osm:{el['type']}/{el['id']}",
    }


def fetch_area(area: str, bbox: tuple[float, float, float, float]) -> int:
    query = QUERY_TEMPLATE.format(bbox=",".join(str(c) for c in bbox))
    resp = httpx.post(OVERPASS_URL, data={"data": query}, timeout=300)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])
    log.info("overpass_fetched", area=area, elements=len(elements))

    db = SessionLocal()
    count = 0
    try:
        for el in elements:
            feat = element_to_feature(el)
            if feat is None:
                continue
            exists = db.execute(
                text("SELECT 1 FROM buildings WHERE source = :s"), {"s": feat["osm_ref"]}
            ).scalar()
            if exists:
                continue
            geom = feat["geom"]
            mp = geom if isinstance(geom, MultiPolygon) else MultiPolygon([geom])
            floors = None
            if feat["floors"]:
                try:
                    floors = int(float(feat["floors"]))
                except ValueError:
                    pass
            building = Building(
                name_en=feat["name"],
                geom=from_shape(mp, srid=4326),
                centroid=from_shape(mp.centroid, srid=4326),
                height_m=feat["height"] or (floors * 3.2 if floors else None),
                floors=floors,
                built_year=feat["year"],
                source=feat["osm_ref"],
            )
            db.add(building)
            db.flush()
            if feat["name"]:
                db.execute(
                    text(
                        """
                        INSERT INTO building_aliases (building_id, alias, source)
                        VALUES (:bid, :alias, 'geo')
                        ON CONFLICT (alias, source) DO NOTHING
                        """
                    ),
                    {"bid": building.id, "alias": feat["name"]},
                )
            count += 1
            if count % 2000 == 0:
                db.commit()
        db.execute(
            text(
                """
                UPDATE buildings b SET district_id = d.id
                FROM districts d
                WHERE b.district_id IS NULL AND ST_Contains(d.geom, b.centroid)
                """
            )
        )
        db.commit()
        log.info("area_loaded", area=area, buildings=count)
        return count
    finally:
        db.close()


def main() -> None:
    setup_logging()
    areas = sys.argv[1:] or list(PILOT_AREAS)
    for i, area in enumerate(areas):
        if area not in PILOT_AREAS:
            log.error("unknown_area", area=area, known=list(PILOT_AREAS))
            continue
        if i > 0:
            time.sleep(10)  # вежливый rate limit к Overpass
        fetch_area(area, PILOT_AREAS[area])


if __name__ == "__main__":
    main()
