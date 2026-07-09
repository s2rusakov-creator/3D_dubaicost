"""Строит демографический слой по районам (ориентировочный).

ВАЖНО про данные: официальная статистика DSC публикуется по официальным
названиям общин ("Marsa Dubai" вместо "Dubai Marina") — сопоставить точные
цифры населения с маркетинговыми районами чисто нельзя, поэтому население
здесь НЕ заполняется (не выдумываем числа). Слой отражает ОРИЕНТИРОВОЧНЫЕ
диаспоры по районам из открытых источников (tenchat.ru, dzen.ru, volna.me,
emirate-dubai.com, kommersant.ru) — это тенденции, не официальная статистика,
и в UI помечается соответствующе (is_indicative=true).

Геометрия зоны = выпуклая оболочка реально загруженных зданий района
(ST_ConvexHull) — без отдельного запроса полигонов.

Запуск: python -m etl.jobs.build_demographics
"""
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging

log = get_logger(__name__)

INDICATIVE_SOURCES = "tenchat.ru, dzen.ru, volna.me, emirate-dubai.com, kommersant.ru (ориентировочно)"

# bbox: (min_lon, min_lat, max_lon, max_lat) — порядок ST_MakeEnvelope
ZONES = [
    {
        "name_en": "Deira",
        "bbox": (55.300, 25.250, 55.335, 25.290),
        "dominant_community": "south_asian",
        "communities": "Индийцы, пакистанцы, иранцы — рынки, этнические магазины, доступное жильё",
        "note": "Исторический торговый район; выражены южноазиатская и иранская диаспоры",
    },
    {
        "name_en": "Bur Dubai",
        "bbox": (55.280, 25.240, 55.310, 25.275),
        "dominant_community": "south_asian",
        "communities": "Индийцы, пакистанцы, бангладешцы — исторический центр, доступное жильё",
        "note": "Старый Дубай; преимущественно южноазиатские общины",
    },
    {
        "name_en": "International City",
        "bbox": (55.395, 25.155, 55.425, 25.185),
        "dominant_community": "filipino_chinese_mixed",
        "communities": "Филиппинцы, китайцы, арабы — недорогое жильё, тематические кластеры",
        "note": "Кластерная застройка; смешанные диаспоры",
    },
    {
        "name_en": "Dubai Marina",
        "bbox": (55.125, 25.070, 55.150, 25.095),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — премиальные апартаменты у воды",
        "note": "Динамичная престижная локация; западные и русскоязычные экспаты",
    },
    {
        "name_en": "Downtown Dubai",
        "bbox": (55.270, 25.185, 55.290, 25.205),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — премиальный центр",
        "note": "Флагманский центр (Burj Khalifa, Dubai Mall); состоятельные экспаты",
    },
    {
        "name_en": "Jumeirah Beach Residence (JBR)",
        "bbox": (55.128, 25.068, 55.145, 25.085),
        "dominant_community": "western_russian_expats",
        "communities": "Британцы, европейцы, русскоязычные экспаты — жильё на пляже",
        "note": "Пляжная престижная локация; западные и русскоязычные экспаты",
    },
    {
        "name_en": "Jumeirah",
        "bbox": (55.240, 25.195, 55.275, 25.245),
        "dominant_community": "emirati_affluent",
        "communities": "Граждане ОАЭ и состоятельные экспаты — вилльная застройка",
        "note": "Престижный вилльный район; граждане ОАЭ и обеспеченные экспаты",
    },
    {
        "name_en": "Palm Jumeirah",
        "bbox": (55.110, 25.100, 55.160, 25.135),
        "dominant_community": "emirati_affluent",
        "communities": "Граждане ОАЭ и состоятельные экспаты — виллы и премиум-апартаменты",
        "note": "Насыпной остров; премиальная недвижимость",
    },
]

UPSERT = text(
    """
    INSERT INTO district_demographics
        (name_en, geom, dominant_community, communities, note, sources, is_indicative)
    VALUES (
        :name, ST_Multi(:hull)::geometry(MultiPolygon, 4326),
        :dominant, :communities, :note, :sources, true
    )
    ON CONFLICT (name_en) DO UPDATE SET
        geom = EXCLUDED.geom,
        dominant_community = EXCLUDED.dominant_community,
        communities = EXCLUDED.communities,
        note = EXCLUDED.note,
        sources = EXCLUDED.sources,
        updated_at = now()
    """
)

# Оболочка зданий района: ST_ConvexHull даёт устойчивый полигон вокруг
# застройки. NULL если в bbox не оказалось зданий.
HULL = text(
    """
    SELECT ST_ConvexHull(ST_Collect(geom)) AS hull
    FROM buildings
    WHERE geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
    """
)


def main() -> None:
    setup_logging()
    db = SessionLocal()
    built = 0
    try:
        for z in ZONES:
            minx, miny, maxx, maxy = z["bbox"]
            row = db.execute(
                HULL, {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
            ).first()
            hull_wkb = row.hull if row else None
            if hull_wkb is None:
                log.warning("zone_no_buildings", zone=z["name_en"])
                continue
            db.execute(
                UPSERT,
                {
                    "name": z["name_en"],
                    "hull": hull_wkb,
                    "dominant": z["dominant_community"],
                    "communities": z["communities"],
                    "note": z["note"],
                    "sources": INDICATIVE_SOURCES,
                },
            )
            built += 1
        db.commit()
        log.info("demographics_built", zones=built)
    finally:
        db.close()


if __name__ == "__main__":
    main()
