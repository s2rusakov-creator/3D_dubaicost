"""Пересчёт привязки транзакций к зданиям на уже загруженных данных.

Нужен после добавления новых зданий (появились новые кандидаты-алиасы) или
изменения логики matching — без повторного скачивания больших CSV.
Статус 'manual' (ручная валидация) не трогаем.

Запуск: python -m etl.jobs.rematch_all
"""
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.pipeline.matching import BuildingMatcher

log = get_logger(__name__)

COMMIT_EVERY = 20_000


def rematch(db, table: str) -> dict[str, int]:
    matcher = BuildingMatcher(db)
    rows = db.execute(
        text(f"SELECT id, raw->>'match_name' AS match_name, match_status FROM {table}")  # noqa: S608
    ).all()
    counts: dict[str, int] = {}
    n = 0
    for row in rows:
        if row.match_status == "manual":
            counts["manual"] = counts.get("manual", 0) + 1
            continue
        m = matcher.match(row.match_name)
        db.execute(
            text(  # noqa: S608
                f"UPDATE {table} SET building_id=:b, match_status=:s, match_score=:sc WHERE id=:id"
            ),
            {"b": m.building_id, "s": m.status, "sc": m.score, "id": row.id},
        )
        counts[m.status] = counts.get(m.status, 0) + 1
        n += 1
        if n % COMMIT_EVERY == 0:
            db.commit()
            log.info("rematch_progress", table=table, done=n)
    db.commit()
    return counts


def main() -> None:
    setup_logging()
    db = SessionLocal()
    try:
        log.info("rematch_sales", counts=rematch(db, "sales_transactions"))
        log.info("rematch_rent", counts=rematch(db, "rent_contracts"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
