"""Агрегация: транзакции -> помесячные метрики по зданиям + refresh materialized view.

Защита от выбросов: жёсткие границы правдоподобия для Дубая, вне их значения
не попадают в агрегат (мусор в данных DLD встречается).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.alerts import send_alert
from app.core.logging import get_logger
from etl.pipeline.cooling import CoolingAssumptions, estimate_cooling_aed_per_sqft_year

log = get_logger(__name__)

MEDIAN_JUMP_THRESHOLD = 0.30  # скачок общегородской медианы месяц-к-месяцу > 30% — алерт


def is_median_jump(prev: float | None, new: float | None,
                   threshold: float = MEDIAN_JUMP_THRESHOLD) -> bool:
    if not prev or not new:
        return False
    return abs(new - prev) / prev > threshold

PRICE_SQFT_BOUNDS = (100, 20_000)   # AED/sqft
RENT_SQFT_BOUNDS = (10, 1_000)      # AED/sqft/год

UPSERT_SALES = text(
    """
    INSERT INTO building_metrics
        (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
    SELECT building_id,
           date_trunc('month', tx_date)::date,
           'price_sqft',
           percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_sqft),
           avg(price_per_sqft),
           count(*),
           now()
    FROM sales_transactions
    WHERE building_id IS NOT NULL
      AND match_status IN ('auto', 'manual')
      AND price_per_sqft BETWEEN :lo AND :hi
      AND tx_date IS NOT NULL
    GROUP BY building_id, 2
    ON CONFLICT (building_id, period, metric) DO UPDATE SET
        value_median = EXCLUDED.value_median,
        value_mean = EXCLUDED.value_mean,
        sample_size = EXCLUDED.sample_size,
        computed_at = EXCLUDED.computed_at
    """
)

UPSERT_RENT = text(
    """
    INSERT INTO building_metrics
        (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
    SELECT building_id,
           date_trunc('month', start_date)::date,
           'rent_sqft',
           percentile_cont(0.5) WITHIN GROUP (ORDER BY rent_per_sqft_year),
           avg(rent_per_sqft_year),
           count(*),
           now()
    FROM rent_contracts
    WHERE building_id IS NOT NULL
      AND match_status IN ('auto', 'manual')
      AND rent_per_sqft_year BETWEEN :lo AND :hi
      AND start_date IS NOT NULL
    GROUP BY building_id, 2
    ON CONFLICT (building_id, period, metric) DO UPDATE SET
        value_median = EXCLUDED.value_median,
        value_mean = EXCLUDED.value_mean,
        sample_size = EXCLUDED.sample_size,
        computed_at = EXCLUDED.computed_at
    """
)

UPSERT_SERVICE_CHARGE = text(
    """
    INSERT INTO building_metrics
        (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
    SELECT building_id,
           make_date(year, 1, 1),
           'service_charge',
           rate_aed_sqft, rate_aed_sqft, 1, now()
    FROM service_charges
    ON CONFLICT (building_id, period, metric) DO UPDATE SET
        value_median = EXCLUDED.value_median,
        value_mean = EXCLUDED.value_mean,
        computed_at = EXCLUDED.computed_at
    """
)


# Разрешение тарифа на здание: точность по убыванию building -> district -> provider_default
RESOLVE_COOLING_TARIFFS = text(
    """
    SELECT b.id AS building_id, t.consumption_fils_per_rth,
           t.demand_aed_per_rt_year, t.fuel_surcharge_pct
    FROM buildings b
    JOIN LATERAL (
        SELECT * FROM cooling_tariffs ct
        WHERE (ct.effective_to IS NULL OR ct.effective_to >= CURRENT_DATE)
          AND (
                (ct.scope = 'building' AND ct.building_id = b.id)
             OR (ct.scope = 'district' AND ct.district_id = b.district_id)
             OR (ct.scope = 'provider_default' AND b.cooling_provider IS NOT NULL
                 AND ct.provider = b.cooling_provider)
          )
        ORDER BY CASE ct.scope
                   WHEN 'building' THEN 1 WHEN 'district' THEN 2 ELSE 3
                 END,
                 ct.effective_from DESC
        LIMIT 1
    ) t ON true
    """
)

# Агрегация должна быть АВТОРИТЕТНОЙ: UPSERT добавляет/обновляет актуальные
# метрики, но при пере-матчинге (изменилась логика, ушла привязка) старые строки
# остаются "осиротевшими" — здание продолжает светиться неверной ценой. Поэтому
# перед upsert чистим метрики, под которыми больше нет исходных данных.
DELETE_STALE_SALES = text(
    """
    DELETE FROM building_metrics bm
    WHERE bm.metric = 'price_sqft'
      AND NOT EXISTS (
        SELECT 1 FROM sales_transactions s
        WHERE s.building_id = bm.building_id
          AND s.match_status IN ('auto', 'manual')
          AND s.price_per_sqft BETWEEN :lo AND :hi
          AND s.tx_date IS NOT NULL
          AND date_trunc('month', s.tx_date)::date = bm.period
      )
    """
)

DELETE_STALE_RENT = text(
    """
    DELETE FROM building_metrics bm
    WHERE bm.metric = 'rent_sqft'
      AND NOT EXISTS (
        SELECT 1 FROM rent_contracts r
        WHERE r.building_id = bm.building_id
          AND r.match_status IN ('auto', 'manual')
          AND r.rent_per_sqft_year BETWEEN :lo AND :hi
          AND r.start_date IS NOT NULL
          AND date_trunc('month', r.start_date)::date = bm.period
      )
    """
)

DELETE_STALE_SERVICE_CHARGE = text(
    """
    DELETE FROM building_metrics bm
    WHERE bm.metric = 'service_charge'
      AND NOT EXISTS (
        SELECT 1 FROM service_charges sc
        WHERE sc.building_id = bm.building_id
          AND make_date(sc.year, 1, 1) = bm.period
      )
    """
)

UPSERT_METRIC = text(
    """
    INSERT INTO building_metrics
        (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
    VALUES (:bid, date_trunc('month', CURRENT_DATE)::date, :metric, :value, :value, 1, now())
    ON CONFLICT (building_id, period, metric) DO UPDATE SET
        value_median = EXCLUDED.value_median,
        value_mean = EXCLUDED.value_mean,
        computed_at = EXCLUDED.computed_at
    """
)


def upsert_cooling_estimates(db: Session, assumptions: CoolingAssumptions) -> int:
    rows = db.execute(RESOLVE_COOLING_TARIFFS).mappings().all()
    params = [
        {
            "bid": r["building_id"],
            "metric": "cooling_est",
            "value": estimate_cooling_aed_per_sqft_year(
                float(r["consumption_fils_per_rth"] or 0),
                float(r["demand_aed_per_rt_year"] or 0),
                float(r["fuel_surcharge_pct"] or 0),
                assumptions,
            ),
        }
        for r in rows
    ]
    if params:
        db.execute(UPSERT_METRIC, params)
    log.info("cooling_estimates_upserted", buildings=len(params))
    return len(params)


def check_median_shift(db: Session) -> None:
    """Алерт (без блокировки), если общегородская медиана price_sqft скакнула м/м."""
    rows = db.execute(
        text(
            """
            SELECT period,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY value_median) AS med
            FROM building_metrics
            WHERE metric = 'price_sqft'
            GROUP BY period ORDER BY period DESC LIMIT 2
            """
        )
    ).all()
    if len(rows) == 2:
        (new_period, new_med), (_, prev_med) = rows[0], rows[1]
        if is_median_jump(
            float(prev_med) if prev_med else None, float(new_med) if new_med else None
        ):
            send_alert(
                f"Аномалия данных: медиана price_sqft за {new_period} = {new_med:.0f} "
                f"против {prev_med:.0f} месяцем ранее (>{MEDIAN_JUMP_THRESHOLD:.0%})"
            )


def run_aggregation(db: Session, assumptions: CoolingAssumptions | None = None) -> None:
    # Сначала убираем осиротевшие метрики (потеряли исходные данные), затем upsert.
    db.execute(DELETE_STALE_SALES, {"lo": PRICE_SQFT_BOUNDS[0], "hi": PRICE_SQFT_BOUNDS[1]})
    db.execute(DELETE_STALE_RENT, {"lo": RENT_SQFT_BOUNDS[0], "hi": RENT_SQFT_BOUNDS[1]})
    db.execute(DELETE_STALE_SERVICE_CHARGE)
    db.execute(UPSERT_SALES, {"lo": PRICE_SQFT_BOUNDS[0], "hi": PRICE_SQFT_BOUNDS[1]})
    db.execute(UPSERT_RENT, {"lo": RENT_SQFT_BOUNDS[0], "hi": RENT_SQFT_BOUNDS[1]})
    db.execute(UPSERT_SERVICE_CHARGE)
    upsert_cooling_estimates(db, assumptions or CoolingAssumptions())
    db.commit()
    check_median_shift(db)
    try:
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_building_metrics"))
    except Exception:
        # CONCURRENTLY падает на пустом view — обычный refresh
        db.rollback()
        db.execute(text("REFRESH MATERIALIZED VIEW latest_building_metrics"))
    db.commit()
    log.info("aggregation_done")
