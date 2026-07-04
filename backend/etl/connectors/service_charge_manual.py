"""Service charge из data/service_charges.csv (ручная выгрузка).

Официальный источник — Service Charge Index DLD (система Mollak):
https://dubailand.gov.ae/en/eservices/service-charge-index-overview/
Это интерактивный сервис без открытого CSV, поэтому данные вносятся вручную
(или будущим скрапером) в CSV с колонками: building_name, year, rate_aed_sqft, source.
Привязка к зданию — только уверенный matching (auto), сомнительные строки пропускаются.
"""
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from etl.connectors.base import Connector, SkipJob
from etl.connectors.util import clean
from etl.pipeline.matching import BuildingMatcher

log = get_logger(__name__)

REQUIRED_CSV_COLUMNS = {"building_name", "year", "rate_aed_sqft"}


class ServiceChargeManualConnector(Connector):
    name = "service_charge_manual"
    required_fields = ("building_name", "year", "rate_aed_sqft")

    def fetch(self) -> Path:
        path = Path(settings.data_dir) / "service_charges.csv"
        if not path.exists():
            raise SkipJob(f"{path} не найден")
        return path

    def normalize(self, raw: Path) -> list[dict]:
        df = pd.read_csv(raw)
        missing = REQUIRED_CSV_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"service_charges.csv: нет колонок {sorted(missing)}")
        return [
            {
                "building_name": clean(row.get("building_name")),
                "year": clean(row.get("year")),
                "rate_aed_sqft": clean(row.get("rate_aed_sqft")),
                "source": clean(row.get("source")) or "manual",
            }
            for _, row in df.iterrows()
        ]

    def load(self, db: Session, records: Iterable[dict]) -> int:
        matcher = BuildingMatcher(db)
        count = 0
        for r in records:
            m = matcher.match(r["building_name"])
            if m.status != "auto":
                log.warning("service_charge_unmatched",
                            building=r["building_name"], score=m.score)
                continue
            db.execute(
                text(
                    """
                    INSERT INTO service_charges
                        (building_id, year, rate_aed_sqft, source, scraped_at)
                    VALUES (:bid, :year, :rate, :source, now())
                    ON CONFLICT (building_id, year) DO UPDATE SET
                        rate_aed_sqft = EXCLUDED.rate_aed_sqft,
                        source = EXCLUDED.source,
                        scraped_at = EXCLUDED.scraped_at
                    """
                ),
                {"bid": m.building_id, "year": int(r["year"]),
                 "rate": r["rate_aed_sqft"], "source": r["source"]},
            )
            count += 1
        db.commit()
        return count
