"""Генерация дополнительных алиасов зданий из уже загруженных имён OSM.

Проблема: OSM часто дописывает к названию хвост застройщика/района через " - ",
которого нет в названиях DLD:
    "Standpoint Residences - Downtown - Emaar"  (OSM)
    "Standpoint Residences"                       (DLD)
Лишние токены роняют скор матчинга, и здание остаётся без цены, хотя полигон есть.

Джоб режет название по " - " и отбрасывает хвостовые/головные сегменты, которые
являются шумом (имя застройщика или района). Ядро названия сохраняется как
дополнительный алиас (source='derived'). Оригинальный алиас не трогаем.

Безопасность: не генерируем короткие/общие алиасы (is_low_quality_alias),
не «переобобщаем» — режем только известный шум, а не произвольные слова.
Идемпотентно: ON CONFLICT (alias, source) DO NOTHING.

Запуск: python -m etl.jobs.enrich_aliases
"""
import re

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.pipeline.matching import is_low_quality_alias, normalize_name

log = get_logger(__name__)

# Известные застройщики Дубая — как хвост названия это шум для матчинга с DLD.
_DEVELOPERS = {
    "emaar", "emaar properties", "damac", "damac properties", "nakheel",
    "meraas", "sobha", "sobha realty", "nshama", "azizi", "azizi developments",
    "omniyat", "select group", "dubai properties", "deyaar", "danube",
    "danube properties", "mag", "ellington", "ellington properties", "aldar",
    "arada", "wasl", "dubai holding", "meydan", "samana", "binghatti",
    "union properties", "iman", "iman developers", "tiger", "tiger properties",
    "seven tides", "reportage", "object 1", "leos", "prescott",
}
# Районы/сообщества — как хвост тоже шум (DLD хранит район отдельным полем).
_AREAS = {
    "downtown", "downtown dubai", "dubai marina", "marina", "business bay",
    "jlt", "jumeirah lakes towers", "jbr", "jumeirah beach residence",
    "palm jumeirah", "palm", "jvc", "jumeirah village circle", "jvt",
    "jumeirah village triangle", "dubai hills", "dubai hills estate",
    "dubailand", "mbr city", "mohammed bin rashid city", "city walk",
    "bluewaters", "difc", "deira", "bur dubai", "al barsha", "barsha",
    "international city", "dubai", "dubai creek harbour", "creek harbour",
    "dubai south", "arjan", "town square", "the greens", "the views",
    "emirates hills", "meydan", "al furjan", "discovery gardens",
}
_NOISE = _DEVELOPERS | _AREAS

_SPLIT = re.compile(r"\s+[-–—]\s+")  # только дефис/тире, окружённые пробелами


def derived_alias(name: str) -> str | None:
    """Ядро названия без хвостовых/головных шумовых сегментов, либо None."""
    parts = _SPLIT.split(name)
    if len(parts) < 2:
        return None
    kept = list(parts)
    # отбрасываем шум с конца и с начала
    while len(kept) > 1 and normalize_name(kept[-1]) in _NOISE:
        kept.pop()
    while len(kept) > 1 and normalize_name(kept[0]) in _NOISE:
        kept.pop(0)
    cleaned = " - ".join(kept).strip()
    if not cleaned or normalize_name(cleaned) == normalize_name(name):
        return None  # ничего не отрезали — новый алиас не нужен
    if is_low_quality_alias(cleaned):
        return None  # не плодим общие/короткие
    return cleaned


def main() -> None:
    setup_logging()
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, name_en FROM buildings WHERE name_en IS NOT NULL")
        ).all()
        added = 0
        for bid, name in rows:
            alias = derived_alias(name)
            if alias is None:
                continue
            res = db.execute(
                text(
                    """
                    INSERT INTO building_aliases (building_id, alias, source)
                    VALUES (:bid, :alias, 'derived')
                    ON CONFLICT (alias, source) DO NOTHING
                    """
                ),
                {"bid": bid, "alias": alias},
            )
            added += res.rowcount or 0
        db.commit()
        log.info("aliases_enriched", derived_added=added, buildings_scanned=len(rows))
        print(f"Добавлено derived-алиасов: {added} (из {len(rows)} названных зданий)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
