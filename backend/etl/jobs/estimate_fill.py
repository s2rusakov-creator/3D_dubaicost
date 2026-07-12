"""Заполнение пробелов ОЦЕНОЧНЫМИ значениями для демонстрации полной карты.

ВАЖНО: это НЕ официальные цифры, а оценки на основе реальных данных:
  - price_est          — медиана реальной цены по району (bbox), либо общая медиана;
  - rent_est           — цена (реальная или оценочная) × доходность, откалиброванную
                         по зданиям, где есть И цена, И реальная аренда (~7%);
  - service_charge_est — общая медиана реальных service charge.

Оценки пишутся ОТДЕЛЬНЫМИ метриками (price_est/rent_est/service_charge_est) —
реальные price_sqft/rent_sqft/service_charge НЕ трогаются. Map API подмешивает
оценку только там, где нет реального значения (COALESCE), поэтому всё обратимо:
удалить эти метрики — и карта снова показывает только реальные данные.

Запуск:   python -m etl.jobs.estimate_fill
Откат:    python -m etl.jobs.estimate_fill --clear
"""
import sys

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.jobs.fetch_osm_buildings import PILOT_AREAS

log = get_logger(__name__)

EST_METRICS = ("price_est", "rent_est", "service_charge_est", "cooling_est_fill")
DEFAULT_YIELD = 0.071  # запасное значение, если реального пересечения цена/аренда нет
DEFAULT_SC_RATIO = 0.011  # service charge как доля от цены (если нет реального пересечения)
# Детерминированный разброс цены на КАЖДЫЙ дом вокруг медианы района (±~33%),
# чтобы карта была не сплошным блоком, а как настоящий хитмап. hashtext даёт
# стабильный псевдослучай по id (не зависит от порядка/соседства). Аренда и SC
# считаются от price_est — разброс каскадом переходит и на них.
_PRICE_VAR = "(0.68 + mod(abs(hashtext(b.id::text)), 1000) / 1000.0 * 0.67)"


def _clear(db) -> None:
    db.execute(
        text("DELETE FROM building_metrics WHERE metric = ANY(:m)"),
        {"m": list(EST_METRICS)},
    )
    db.commit()
    _refresh(db)
    log.info("estimates_cleared")


def _refresh(db) -> None:
    try:
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_building_metrics"))
    except Exception:
        db.rollback()
        db.execute(text("REFRESH MATERIALIZED VIEW latest_building_metrics"))
    db.commit()


def _scalar(db, sql: str, **params) -> float | None:
    v = db.execute(text(sql), params).scalar()
    return float(v) if v is not None else None


def main() -> None:
    setup_logging()
    db = SessionLocal()
    try:
        if "--clear" in sys.argv:
            _clear(db)
            print("Оценочные метрики удалены — карта снова только на реальных данных.")
            return

        _clear(db)  # идемпотентность: сносим прошлые оценки перед пересчётом
        _refresh(db)

        # Калибровки по реальным данным
        yield_ = _scalar(
            db,
            """
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY r.value_median/p.value_median)
            FROM latest_building_metrics p JOIN latest_building_metrics r USING (building_id)
            WHERE p.metric='price_sqft' AND r.metric='rent_sqft' AND p.value_median>0
            """,
        ) or DEFAULT_YIELD
        global_price = _scalar(
            db, "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY value_median) "
                "FROM latest_building_metrics WHERE metric='price_sqft'") or 1500.0
        global_sc = _scalar(
            db, "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY value_median) "
                "FROM latest_building_metrics WHERE metric='service_charge'") or 16.0
        # service charge как доля от цены — калибруем по зданиям, где есть и SC, и цена,
        # чтобы SC варьировался по районам (премиум дороже), а не был плоским
        sc_ratio = _scalar(
            db,
            """
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY s.value_median/p.value_median)
            FROM latest_building_metrics s JOIN latest_building_metrics p USING (building_id)
            WHERE s.metric='service_charge' AND p.metric='price_sqft' AND p.value_median>0
            """,
        ) or DEFAULT_SC_RATIO
        log.info("estimate_calibration", yield_pct=round(yield_ * 100, 2),
                 global_price=round(global_price, 1), global_sc=round(global_sc, 2),
                 sc_ratio=round(sc_ratio, 4))

        period = "date_trunc('month', CURRENT_DATE)::date"

        # 1) price_est — по медиане района (bbox), затем общий добор
        for area, (min_lat, min_lon, max_lat, max_lon) in PILOT_AREAS.items():
            box = {"a": min_lat, "b": max_lat, "c": min_lon, "d": max_lon}
            med = _scalar(
                db,
                """
                SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY m.value_median)
                FROM latest_building_metrics m JOIN buildings b ON b.id=m.building_id
                WHERE m.metric='price_sqft'
                  AND ST_Y(b.centroid::geometry) BETWEEN :a AND :b
                  AND ST_X(b.centroid::geometry) BETWEEN :c AND :d
                """,
                **box,
            )
            db.execute(
                text(
                    f"""
                    INSERT INTO building_metrics
                        (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
                    SELECT b.id, {period}, 'price_est',
                           round((:val * {_PRICE_VAR})::numeric, 1),
                           round((:val * {_PRICE_VAR})::numeric, 1), 0, now()
                    FROM buildings b
                    WHERE ST_Y(b.centroid::geometry) BETWEEN :a AND :b
                      AND ST_X(b.centroid::geometry) BETWEEN :c AND :d
                      AND NOT EXISTS (SELECT 1 FROM latest_building_metrics r
                                      WHERE r.building_id=b.id AND r.metric='price_sqft')
                      AND NOT EXISTS (SELECT 1 FROM building_metrics e
                                      WHERE e.building_id=b.id AND e.metric='price_est')
                    ON CONFLICT (building_id, period, metric) DO NOTHING
                    """
                ),
                {"val": round(med or global_price, 1), **box},
            )
        # добор для зданий вне bbox-ов
        db.execute(
            text(
                f"""
                INSERT INTO building_metrics
                    (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
                SELECT b.id, {period}, 'price_est',
                       round((:val * {_PRICE_VAR})::numeric, 1),
                       round((:val * {_PRICE_VAR})::numeric, 1), 0, now()
                FROM buildings b
                WHERE NOT EXISTS (SELECT 1 FROM latest_building_metrics r
                                  WHERE r.building_id=b.id AND r.metric='price_sqft')
                  AND NOT EXISTS (SELECT 1 FROM building_metrics e
                                  WHERE e.building_id=b.id AND e.metric='price_est')
                ON CONFLICT (building_id, period, metric) DO NOTHING
                """
            ),
            {"val": round(global_price, 1)},
        )
        db.commit()
        _refresh(db)

        # 2) rent_est = COALESCE(реальная цена, price_est) * доходность, где нет реальной аренды
        db.execute(
            text(
                f"""
                INSERT INTO building_metrics
                    (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
                SELECT b.id, {period}, 'rent_est',
                       round((pe.value_median * :y)::numeric, 1),
                       round((pe.value_median * :y)::numeric, 1), 0, now()
                FROM buildings b
                JOIN latest_building_metrics pe ON pe.building_id=b.id
                     AND pe.metric IN ('price_sqft','price_est')
                WHERE NOT EXISTS (SELECT 1 FROM latest_building_metrics r
                                  WHERE r.building_id=b.id AND r.metric='rent_sqft')
                  AND NOT EXISTS (SELECT 1 FROM building_metrics e
                                  WHERE e.building_id=b.id AND e.metric='rent_est')
                ON CONFLICT (building_id, period, metric) DO NOTHING
                """
            ),
            {"y": yield_},
        )
        # 3) service_charge_est = цена * доля (варьируется по районам), клампим 6..35
        db.execute(
            text(
                f"""
                INSERT INTO building_metrics
                    (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
                SELECT b.id, {period}, 'service_charge_est', v, v, 0, now()
                FROM buildings b
                JOIN LATERAL (
                    SELECT round(LEAST(35, GREATEST(6, pe.value_median * :ratio))::numeric, 2) AS v
                    FROM latest_building_metrics pe
                    WHERE pe.building_id=b.id AND pe.metric IN ('price_sqft','price_est')
                    LIMIT 1
                ) sc ON true
                WHERE NOT EXISTS (SELECT 1 FROM latest_building_metrics r
                                  WHERE r.building_id=b.id AND r.metric='service_charge')
                  AND NOT EXISTS (SELECT 1 FROM building_metrics e
                                  WHERE e.building_id=b.id AND e.metric='service_charge_est')
                ON CONFLICT (building_id, period, metric) DO NOTHING
                """
            ),
            {"ratio": sc_ratio},
        )
        # 4) cooling_est_fill — district cooling для зданий вне зон Empower (иначе слой
        #    серый почти везде). Тариф ~равномерный, но с лёгкой вариацией для вида.
        db.execute(
            text(
                f"""
                INSERT INTO building_metrics
                    (building_id, period, metric, value_median, value_mean, sample_size, computed_at)
                SELECT b.id, {period}, 'cooling_est_fill',
                       round((4.5 + mod(b.id, 40) * 0.05)::numeric, 2),
                       round((4.5 + mod(b.id, 40) * 0.05)::numeric, 2), 0, now()
                FROM buildings b
                WHERE NOT EXISTS (SELECT 1 FROM latest_building_metrics r
                                  WHERE r.building_id=b.id AND r.metric='cooling_est')
                  AND NOT EXISTS (SELECT 1 FROM building_metrics e
                                  WHERE e.building_id=b.id AND e.metric='cooling_est_fill')
                ON CONFLICT (building_id, period, metric) DO NOTHING
                """
            ),
        )
        db.commit()
        _refresh(db)

        counts = dict(
            db.execute(
                text("SELECT metric, count(*) FROM building_metrics "
                     "WHERE metric = ANY(:m) GROUP BY metric"),
                {"m": list(EST_METRICS)},
            ).all()
        )
        log.info("estimates_filled", counts=counts)
        print(f"Оценки заполнены: {counts} (доходность {round(yield_*100,2)}%)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
