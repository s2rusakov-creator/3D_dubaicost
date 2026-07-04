from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import METRICS

router = APIRouter(tags=["layers"])

LAYER_UNITS = {
    "price_sqft": "AED/sqft",
    "rent_sqft": "AED/sqft/год",
    "service_charge": "AED/sqft/год",
    "cooling_est": "AED/sqft/год",
    "built_year": "год",
    "parking_ratio": "мест/квартиру",
}


@router.get("/layers")
def get_layers(db: Session = Depends(get_db)) -> dict:
    """Доступные слои + покрытие (сколько зданий имеют значение)."""
    total = db.execute(text("SELECT count(*) FROM buildings")).scalar() or 0

    counts = {
        r["metric"]: r["cnt"]
        for r in db.execute(
            text("SELECT metric, count(*) AS cnt FROM latest_building_metrics GROUP BY metric")
        ).mappings()
    }
    for col in ("built_year", "parking_ratio"):
        counts[col] = db.execute(
            text(f"SELECT count(*) FROM buildings WHERE {col} IS NOT NULL")  # noqa: S608
        ).scalar()

    layers = [
        {
            "id": layer_id,
            "unit": LAYER_UNITS.get(layer_id, ""),
            "buildings_covered": counts.get(layer_id, 0),
            "buildings_total": total,
        }
        for layer_id in [*METRICS, "built_year", "parking_ratio"]
    ]
    return {"layers": layers}
