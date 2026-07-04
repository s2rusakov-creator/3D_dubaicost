"""Загрузка гео-справочника из GeoJSON (Overture Maps / OSM extract).

Запуск:
    python -m etl.jobs.load_geo districts /data/districts.geojson
    python -m etl.jobs.load_geo buildings /data/buildings.geojson

Ожидаемые properties для buildings: name (или names.primary у Overture),
height, levels (num_floors). Название здания попадает в building_aliases (source='geo').
"""
import json
import sys
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from app.models import Building, BuildingAlias, District

log = get_logger(__name__)


def _prop(props: dict, *keys: str):
    """Достаёт первое непустое свойство: поддерживает и OSM, и Overture схемы."""
    for key in keys:
        val = props
        for part in key.split("."):
            val = val.get(part) if isinstance(val, dict) else None
        if val not in (None, ""):
            return val
    return None


def _to_multipolygon(geom) -> MultiPolygon | None:
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


def load_districts(path: Path) -> None:
    fc = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    count = 0
    try:
        for feat in fc["features"]:
            geom = _to_multipolygon(shape(feat["geometry"]))
            name = _prop(feat.get("properties", {}), "name", "name_en", "names.primary")
            if geom is None or not name:
                continue
            exists = db.execute(
                text("SELECT id FROM districts WHERE name_en = :n"), {"n": name}
            ).scalar()
            if exists:
                continue
            db.add(District(name_en=name, geom=from_shape(geom, srid=4326), source=str(path.name)))
            count += 1
        db.commit()
        log.info("districts_loaded", count=count)
    finally:
        db.close()


def load_buildings(path: Path) -> None:
    fc = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    count = 0
    try:
        for feat in fc["features"]:
            geom = _to_multipolygon(shape(feat["geometry"]))
            if geom is None:
                continue
            props = feat.get("properties", {})
            name = _prop(props, "name", "names.primary", "name_en")
            height = _prop(props, "height", "height_m")
            levels = _prop(props, "levels", "num_floors", "building:levels")

            if name:
                exists = db.execute(
                    text("SELECT 1 FROM building_aliases WHERE alias = :a AND source = 'geo'"),
                    {"a": name},
                ).scalar()
                if exists:
                    continue

            building = Building(
                name_en=name,
                geom=from_shape(geom, srid=4326),
                centroid=from_shape(geom.centroid, srid=4326),
                height_m=float(height) if height else None,
                floors=int(levels) if levels else None,
                source=str(path.name),
            )
            db.add(building)
            db.flush()
            if name:
                db.add(BuildingAlias(building_id=building.id, alias=name, source="geo"))
            count += 1
            if count % 5000 == 0:
                db.commit()
        # привязка к районам по центроиду
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
        log.info("buildings_loaded", count=count)
    finally:
        db.close()


if __name__ == "__main__":
    setup_logging()
    if len(sys.argv) != 3 or sys.argv[1] not in ("districts", "buildings"):
        print(__doc__)
        sys.exit(1)
    target, file_path = sys.argv[1], Path(sys.argv[2])
    if target == "districts":
        load_districts(file_path)
    else:
        load_buildings(file_path)
