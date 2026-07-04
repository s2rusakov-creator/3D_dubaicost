"""Простой ETL-планировщик: прогон при старте, затем ежедневно в 03:00 UTC.

Осознанно без Dagster/Prefect на MVP — джобов мало, зависимости линейные.
Идемпотентность обеспечивают upsert'ы, повторный запуск безопасен.
Порядок важен: сначала алиасы (улучшают matching), потом транзакции, потом агрегация.
"""
import time
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging
from etl.connectors.alias_overrides import AliasOverridesConnector
from etl.connectors.base import run_connector
from etl.connectors.cooling_manual import CoolingManualConnector
from etl.connectors.dld_rent import DldRentConnector
from etl.connectors.dld_sales import DldSalesConnector
from etl.connectors.service_charge_manual import ServiceChargeManualConnector
from etl.pipeline.aggregate import run_aggregation
from etl.pipeline.cooling import load_assumptions

log = get_logger(__name__)

RUN_AT_UTC_HOUR = 3

CONNECTORS = [
    AliasOverridesConnector,
    DldSalesConnector,
    DldRentConnector,
    ServiceChargeManualConnector,
    CoolingManualConnector,
]


def run_all() -> None:
    db = SessionLocal()
    try:
        for connector_cls in CONNECTORS:
            run_connector(connector_cls(), db)
        run_aggregation(db, load_assumptions(settings.data_dir))
    finally:
        db.close()


def seconds_until_next_run(now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    target = now.replace(hour=RUN_AT_UTC_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def main() -> None:
    setup_logging()
    while True:
        log.info("etl_cycle_start")
        try:
            run_all()
        except Exception as exc:
            log.error("etl_cycle_failed", error=str(exc))
        sleep_s = seconds_until_next_run()
        log.info("etl_cycle_done", next_run_in_hours=round(sleep_s / 3600, 1))
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
