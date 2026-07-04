from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["coverage"])


@router.get("/coverage")
def get_coverage(db: Session = Depends(get_db)) -> dict:
    """Статус покрытия данных: последние запуски ETL по источникам + доля смэтченных транзакций."""
    runs = db.execute(
        text(
            """
            SELECT DISTINCT ON (source)
                   source, started_at, finished_at, status, rows_in, rows_upserted, error
            FROM ingestion_runs
            ORDER BY source, started_at DESC
            """
        )
    ).mappings().all()

    match_stats = db.execute(
        text(
            """
            SELECT 'sales' AS entity, match_status, count(*) AS cnt
            FROM sales_transactions GROUP BY match_status
            UNION ALL
            SELECT 'rent', match_status, count(*)
            FROM rent_contracts GROUP BY match_status
            """
        )
    ).mappings().all()

    review_pending = db.execute(
        text("SELECT count(*) FROM match_review_queue WHERE status = 'pending'")
    ).scalar()

    matching: dict[str, dict[str, int]] = {}
    for r in match_stats:
        matching.setdefault(r["entity"], {})[r["match_status"]] = r["cnt"]

    return {
        "sources": [
            {
                "source": r["source"],
                "last_run": str(r["started_at"]),
                "finished_at": str(r["finished_at"]) if r["finished_at"] else None,
                "status": r["status"],
                "rows_in": r["rows_in"],
                "rows_upserted": r["rows_upserted"],
                "error": r["error"],
            }
            for r in runs
        ],
        "matching": matching,
        "review_pending": review_pending,
    }
