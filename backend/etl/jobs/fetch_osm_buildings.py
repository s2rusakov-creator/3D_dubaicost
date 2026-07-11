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

# Основной overpass-api.de часто отдаёт 504 под нагрузкой. Зеркала-фолбэки
# (maps.mail.ru/VK стабильно быстрый). Порядок = приоритет.
OVERPASS_MIRRORS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_URL = OVERPASS_MIRRORS[0]
# Overpass отклоняет запросы без внятного User-Agent (406 Not Acceptable)
HEADERS = {"User-Agent": "DubaiCostETL/0.1 (self-hosted real-estate map, non-commercial MVP)"}

# bbox: (min_lat, min_lon, max_lat, max_lon) — порядок Overpass
PILOT_AREAS: dict[str, tuple[float, float, float, float]] = {
    "marina_jlt": (25.055, 55.125, 25.095, 55.162),        # Dubai Marina + JLT
    "downtown_businessbay": (25.170, 55.245, 25.210, 55.290),
    "jvc": (25.045, 55.195, 25.075, 55.225),               # Jumeirah Village Circle
    # Расширение покрытия: населённые районы (в т.ч. с выраженными диаспорами)
    "palm_jumeirah": (25.100, 55.110, 25.135, 55.160),     # Palm Jumeirah (виллы/апартаменты)
    "jbr": (25.068, 55.128, 25.085, 55.145),               # Jumeirah Beach Residence
    "jumeirah": (25.195, 55.240, 25.245, 55.275),          # Jumeirah (виллы)
    "deira": (25.250, 55.300, 25.290, 55.335),             # Deira (Южная Азия/Иран)
    "bur_dubai": (25.240, 55.280, 25.275, 55.310),         # Bur Dubai (Южная Азия)
    "international_city": (25.155, 55.395, 25.185, 55.425),  # International City
    "al_barsha": (25.100, 55.190, 25.125, 55.220),         # Al Barsha
    "dubai_hills": (25.100, 55.240, 25.135, 55.275),       # Dubai Hills Estate
    # Догрузка плотных жилых районов (заполнить пустоты на общей карте)
    "al_qusais_nahda": (25.255, 55.365, 25.300, 55.420),   # Al Qusais / Al Nahda
    "muhaisnah_mirdif": (25.205, 55.400, 25.260, 55.460),  # Muhaisnah / Mirdif
    "nad_al_sheba": (25.145, 55.300, 25.190, 55.360),      # Nad Al Sheba
    "dubailand_sports": (25.025, 55.205, 25.080, 55.265),  # Sports City / Motor City / Arjan
    "furjan_gardens": (25.015, 55.115, 25.060, 55.180),    # Al Furjan / Discovery Gardens / JVT
    "silicon_oasis": (25.100, 55.365, 25.145, 55.410),     # Dubai Silicon Oasis
    # Центральные дыры между кластерами
    "al_quoz": (25.110, 55.210, 25.165, 55.262),           # Al Quoz (пром + жильё)
    "jumeirah_coast": (25.150, 55.190, 25.212, 55.248),    # Umm Suqeim / Jumeirah / Al Safa (побережье)
    "al_wasl_safa": (25.175, 55.245, 25.220, 55.278),      # Al Wasl / Al Safa / City Walk
    # Оставшиеся жилые зоны (восток, юг, запад-виллы)
    "al_warqa": (25.155, 55.440, 25.205, 55.495),          # Al Warqa
    "nadd_hamar_rashidiya": (25.210, 55.385, 25.258, 55.445),  # Nadd Al Hamar / Al Rashidiya
    "khawaneej_mirdif_e": (25.200, 55.455, 25.252, 55.512),    # Al Khawaneej / вост. Mirdif
    "liwan_academic": (25.095, 55.400, 25.160, 55.472),        # Liwan / Academic City / DSO-юг
    "the_villa_wadisafa": (25.025, 55.285, 25.082, 55.352),    # The Villa / Wadi Al Safa
    "town_square_remraam": (24.985, 55.228, 25.048, 55.302),   # Town Square / Remraam / Ranches
    "springs_meadows": (25.048, 55.178, 25.108, 55.252),       # Springs / Meadows / JLT-юг
    "jge_furjan_n": (25.028, 55.142, 25.088, 55.202),          # Jumeirah Golf Estates / Al Furjan-север
    # Юг (ниже 24.92) и дальние окраины
    "dubai_south_expo": (24.840, 55.120, 24.945, 55.260),      # Dubai South / Expo City / Al Maktoum
    "jebel_ali_west": (24.950, 54.990, 25.055, 55.100),        # Jebel Ali порт/FZ/village
    "al_barsha_s_jvt2": (25.030, 55.190, 25.078, 55.248),      # Al Barsha South / JVT-довесок
    "mizhar_muhaisnah_n": (25.240, 55.440, 25.302, 55.512),    # Mizhar / сев. Muhaisnah
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


def _overpass_post(query: str) -> dict:
    """POST к Overpass с перебором зеркал: первое ответившее 200 выигрывает."""
    last_exc: Exception | None = None
    for url in OVERPASS_MIRRORS:
        try:
            resp = httpx.post(url, data={"data": query}, timeout=300, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 — сетевой сбой/504, пробуем следующее зеркало
            log.warning("overpass_mirror_failed", url=url, error=str(exc))
            last_exc = exc
    raise last_exc or RuntimeError("all overpass mirrors failed")


def fetch_area(area: str, bbox: tuple[float, float, float, float]) -> int:
    query = QUERY_TEMPLATE.format(bbox=",".join(str(c) for c in bbox))
    elements = _overpass_post(query).get("elements", [])
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


def fetch_area_with_retry(area: str, bbox: tuple[float, float, float, float],
                          attempts: int = 3) -> bool:
    """Overpass отдаёт транзиентные 504/SSL под нагрузкой — повторяем с паузой.
    Возвращает True при успехе; False если все попытки провалились (не рушим цикл).
    """
    for attempt in range(1, attempts + 1):
        try:
            fetch_area(area, bbox)
            return True
        except Exception as exc:  # noqa: BLE001 — любой сетевой сбой Overpass
            log.warning("area_fetch_failed", area=area, attempt=attempt, error=str(exc))
            if attempt < attempts:
                time.sleep(20)
    log.error("area_fetch_gave_up", area=area, attempts=attempts)
    return False


def main() -> None:
    setup_logging()
    areas = sys.argv[1:] or list(PILOT_AREAS)
    for i, area in enumerate(areas):
        if area not in PILOT_AREAS:
            log.error("unknown_area", area=area, known=list(PILOT_AREAS))
            continue
        if i > 0:
            time.sleep(10)  # вежливый rate limit к Overpass
        fetch_area_with_retry(area, PILOT_AREAS[area])


if __name__ == "__main__":
    main()
