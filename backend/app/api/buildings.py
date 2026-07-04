from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["buildings"])

HISTORY_MONTHS = 24


@router.get("/buildings/{building_id}")
def get_building(building_id: int, db: Session = Depends(get_db)) -> dict:
    """Детальная карточка здания: атрибуты, метрики с историей, service charge, cooling."""
    b = db.execute(
        text(
            """
            SELECT b.id, b.name_en, b.master_project, b.built_year, b.floors, b.height_m,
                   b.units_count, b.parking_spaces, b.parking_ratio, b.cooling_provider,
                   b.source, d.name_en AS district
            FROM buildings b
            LEFT JOIN districts d ON d.id = b.district_id
            WHERE b.id = :id
            """
        ),
        {"id": building_id},
    ).mappings().first()
    if b is None:
        raise HTTPException(404, "building not found")

    metrics_rows = db.execute(
        text(
            """
            SELECT metric, period, value_median, value_mean, sample_size
            FROM building_metrics
            WHERE building_id = :id
              AND period >= (CURRENT_DATE - INTERVAL '1 month' * :months)
            ORDER BY metric, period
            """
        ),
        {"id": building_id, "months": HISTORY_MONTHS},
    ).mappings().all()

    metrics: dict[str, list[dict]] = {}
    for r in metrics_rows:
        metrics.setdefault(r["metric"], []).append(
            {
                "period": str(r["period"]),
                "median": float(r["value_median"]) if r["value_median"] is not None else None,
                "mean": float(r["value_mean"]) if r["value_mean"] is not None else None,
                "sample_size": r["sample_size"],
            }
        )

    service_charge = db.execute(
        text(
            """
            SELECT year, rate_aed_sqft, source, scraped_at
            FROM service_charges
            WHERE building_id = :id
            ORDER BY year DESC
            LIMIT 1
            """
        ),
        {"id": building_id},
    ).mappings().first()

    # Тариф охлаждения: точность по убыванию — здание -> район -> дефолт провайдера
    cooling = db.execute(
        text(
            """
            SELECT provider, scope, consumption_fils_per_rth, demand_aed_per_rt_year,
                   fuel_surcharge_pct, effective_from, source_note
            FROM cooling_tariffs ct
            WHERE (effective_to IS NULL OR effective_to >= CURRENT_DATE)
              AND (
                    (scope = 'building' AND ct.building_id = :id)
                 OR (scope = 'district' AND ct.district_id =
                        (SELECT district_id FROM buildings WHERE id = :id))
                 OR (scope = 'provider_default' AND ct.provider =
                        (SELECT cooling_provider FROM buildings WHERE id = :id))
              )
            ORDER BY CASE scope
                       WHEN 'building' THEN 1 WHEN 'district' THEN 2 ELSE 3
                     END,
                     effective_from DESC
            LIMIT 1
            """
        ),
        {"id": building_id},
    ).mappings().first()

    return {
        "building": {
            "id": b["id"],
            "name": b["name_en"],
            "district": b["district"],
            "master_project": b["master_project"],
            "built_year": b["built_year"],
            "floors": b["floors"],
            "height_m": float(b["height_m"]) if b["height_m"] is not None else None,
            "units_count": b["units_count"],
            "parking_spaces": b["parking_spaces"],
            "parking_ratio": float(b["parking_ratio"]) if b["parking_ratio"] is not None else None,
            "cooling_provider": b["cooling_provider"],
            "geo_source": b["source"],
        },
        "metrics": metrics,  # отсутствие ключа = нет данных по метрике
        "service_charge": dict(service_charge) if service_charge else None,
        "cooling_tariff": dict(cooling) if cooling else None,
    }
