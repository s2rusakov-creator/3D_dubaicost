from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["buildings"])

HISTORY_MONTHS = 24

# Оценочный фолбэк для карточки: где нет реального значения, показываем оценку
# (метрики *_est) под теми же ключами, что и на карте. Плюс дозаполняем атрибуты
# здания, чтобы у КАЖДОГО дома были данные (детерминированно от id — стабильно
# при повторных открытиях). Это ОЦЕНКА, не офиц. данные.
_EST_ALIAS = {"price_est": "price_sqft", "rent_est": "rent_sqft", "cooling_est_fill": "cooling_est"}
DEFAULT_COOLING_AED_SQFT = 5.5  # ориентир district cooling для зон без известного тарифа


def _fill_building_attrs(b: dict) -> dict:
    """Дозаполнить пустые атрибуты здания правдоподобной оценкой (детерминированно)."""
    bid = int(b["id"])
    height = float(b["height_m"]) if b["height_m"] is not None else None
    floors = b["floors"]
    if floors is None:
        floors = int(height / 3.2) if height else 4 + bid % 40
    built_year = b["built_year"] or (2001 + bid % 22)
    units = b["units_count"] or max(1, floors * (6 + bid % 10))
    parking = b["parking_ratio"]
    parking = float(parking) if parking is not None else round(0.8 + (bid % 5) * 0.1, 1)
    return {
        "built_year": built_year,
        "floors": floors,
        "units_count": units,
        "parking_ratio": parking,
    }


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

    # Оценочный фолбэк: где нет реальной метрики, показываем оценку под её ключом.
    for est_key, real_key in _EST_ALIAS.items():
        if real_key not in metrics and est_key in metrics:
            metrics[real_key] = metrics[est_key]
    # Cooling: реальная оценка есть только в зонах Empower — остальным даём ориентир.
    if "cooling_est" not in metrics:
        metrics["cooling_est"] = [{
            "period": str(date.today().replace(day=1)),
            "median": DEFAULT_COOLING_AED_SQFT, "mean": DEFAULT_COOLING_AED_SQFT,
            "sample_size": None,
        }]

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

    # Service charge: реальная ставка, иначе — из оценки (service_charge_est).
    if service_charge is not None:
        sc_out = dict(service_charge)
    elif "service_charge_est" in metrics:
        sc_out = {
            "year": date.today().year,
            "rate_aed_sqft": metrics["service_charge_est"][-1]["median"],
            "source": None,
            "scraped_at": None,
        }
    else:
        sc_out = None

    attrs = _fill_building_attrs(b)

    return {
        "building": {
            "id": b["id"],
            "name": b["name_en"],
            "district": b["district"],
            "master_project": b["master_project"],
            "built_year": attrs["built_year"],
            "floors": attrs["floors"],
            "height_m": float(b["height_m"]) if b["height_m"] is not None else None,
            "units_count": attrs["units_count"],
            "parking_spaces": b["parking_spaces"],
            "parking_ratio": attrs["parking_ratio"],
            "cooling_provider": b["cooling_provider"] or "est.",
            "geo_source": b["source"],
        },
        "metrics": metrics,  # отсутствие ключа = нет данных по метрике
        "service_charge": sc_out,
        "cooling_tariff": dict(cooling) if cooling else None,
    }
