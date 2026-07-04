"""Admin-эндпоинты очереди ручной валидации matching'а.

Auth: заголовок X-Admin-Token == settings.admin_token (пустой токен = закрыто).
Approve: транзакция получает match_status='manual', алиас становится verified —
следующие прогоны DLD мэтчат такие названия автоматически.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

router = APIRouter(tags=["review"])

ENTITY_TABLES = {
    "sales_transaction": "sales_transactions",
    "rent_contract": "rent_contracts",
}


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not settings.admin_token:
        raise HTTPException(403, "admin endpoints disabled (ADMIN_TOKEN not set)")
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "invalid admin token")


@router.get("/review", dependencies=[Depends(require_admin)])
def list_pending(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        text(
            """
            SELECT q.id, q.entity_type, q.entity_id, q.score,
                   q.candidate_building_id, b.name_en AS candidate_name,
                   CASE q.entity_type
                     WHEN 'sales_transaction' THEN
                       (SELECT raw->>'match_name' FROM sales_transactions
                        WHERE id = q.entity_id)
                     ELSE
                       (SELECT raw->>'match_name' FROM rent_contracts
                        WHERE id = q.entity_id)
                   END AS source_name
            FROM match_review_queue q
            LEFT JOIN buildings b ON b.id = q.candidate_building_id
            WHERE q.status = 'pending'
            ORDER BY q.score DESC NULLS LAST, q.id
            LIMIT 200
            """
        )
    ).mappings().all()
    return {
        "pending": [
            {
                "id": r["id"],
                "entity_type": r["entity_type"],
                "source_name": r["source_name"],
                "candidate_building_id": r["candidate_building_id"],
                "candidate_name": r["candidate_name"],
                "score": float(r["score"]) if r["score"] is not None else None,
            }
            for r in rows
        ]
    }


class ResolveBody(BaseModel):
    action: str  # approve | reject
    resolved_by: str = "admin"


@router.post("/review/{queue_id}", dependencies=[Depends(require_admin)])
def resolve(queue_id: int, body: ResolveBody, db: Session = Depends(get_db)) -> dict:
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")

    q = db.execute(
        text("SELECT * FROM match_review_queue WHERE id = :id AND status = 'pending'"),
        {"id": queue_id},
    ).mappings().first()
    if q is None:
        raise HTTPException(404, "pending queue item not found")

    table = ENTITY_TABLES.get(q["entity_type"])
    if table is None:
        raise HTTPException(500, f"unknown entity_type {q['entity_type']}")

    if body.action == "approve":
        db.execute(
            text(
                f"UPDATE {table} SET match_status = 'manual' WHERE id = :eid"  # noqa: S608
            ),
            {"eid": q["entity_id"]},
        )
        # алиас становится verified — дальше exact match без ручной работы
        source_name = db.execute(
            text(f"SELECT raw->>'match_name' FROM {table} WHERE id = :eid"),  # noqa: S608
            {"eid": q["entity_id"]},
        ).scalar()
        if source_name and q["candidate_building_id"]:
            db.execute(
                text(
                    """
                    INSERT INTO building_aliases (building_id, alias, source, verified)
                    VALUES (:bid, :alias, 'review', true)
                    ON CONFLICT (alias, source) DO UPDATE SET
                        building_id = EXCLUDED.building_id, verified = true
                    """
                ),
                {"bid": q["candidate_building_id"], "alias": source_name},
            )
    else:
        db.execute(
            text(
                f"""
                UPDATE {table} SET match_status = 'unmatched', building_id = NULL
                WHERE id = :eid
                """  # noqa: S608
            ),
            {"eid": q["entity_id"]},
        )

    db.execute(
        text(
            """
            UPDATE match_review_queue
            SET status = :status, resolved_by = :by, resolved_at = now()
            WHERE id = :id
            """
        ),
        {
            "status": "approved" if body.action == "approve" else "rejected",
            "by": body.resolved_by,
            "id": queue_id,
        },
    )
    db.commit()
    return {"id": queue_id, "status": body.action}
