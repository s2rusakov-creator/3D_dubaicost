"""Коннектор арендных контрактов Ejari (Dubai Pulse open data, bulk CSV).

Датасет: https://www.dubaipulse.gov.ae/data/dld-registration/dld_rent_contracts-open
Тот же паттерн, что dld_sales: чанки, батчи, matching с кэшем.
"""
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from etl.connectors.base import Connector, SkipJob
from etl.connectors.dld_sales import CHUNK_SIZE, SQM_TO_SQFT, download_csv
from etl.connectors.util import clean, pick_column
from etl.pipeline.matching import BuildingMatcher

BATCH_SIZE = 5_000

COLUMN_CANDIDATES = {
    "dld_contract_id": ("contract_id", "ejari_contract_number", "contract_number"),
    "start_date": ("contract_start_date", "start_date"),
    "end_date": ("contract_end_date", "end_date"),
    "annual_rent_aed": ("annual_amount", "contract_amount"),
    "area_sqm": ("actual_area", "property_size"),
    "building_name": ("ejari_property_name", "building_name_en"),
    "project_name": ("project_name_en", "master_project_en"),
    "area_name": ("area_name_en",),
}
REQUIRED_COLUMNS = ("dld_contract_id", "start_date", "annual_rent_aed")

UPSERT = text(
    """
    INSERT INTO rent_contracts
        (dld_contract_id, building_id, match_status, match_score,
         start_date, end_date, annual_rent_aed, area_sqft, raw)
    VALUES
        (:dld_contract_id, :building_id, :match_status, :match_score,
         :start_date, :end_date, :annual_rent_aed, :area_sqft, CAST(:raw AS jsonb))
    ON CONFLICT (dld_contract_id) DO UPDATE SET
        building_id = EXCLUDED.building_id,
        match_status = CASE WHEN rent_contracts.match_status = 'manual'
                            THEN 'manual' ELSE EXCLUDED.match_status END,
        match_score = EXCLUDED.match_score
    """
)

ENQUEUE_REVIEW = text(
    """
    INSERT INTO match_review_queue (entity_type, entity_id, candidate_building_id, score)
    SELECT 'rent_contract', rc.id, rc.building_id, rc.match_score
    FROM rent_contracts rc
    WHERE rc.dld_contract_id = ANY(:ids)
      AND rc.match_status = 'review'
      AND NOT EXISTS (
          SELECT 1 FROM match_review_queue q
          WHERE q.entity_type = 'rent_contract'
            AND q.entity_id = rc.id AND q.status = 'pending'
      )
    """
)


class DldRentConnector(Connector):
    name = "dld_rent"
    required_fields = ("dld_contract_id", "start_date", "annual_rent_aed")

    def fetch(self) -> Path:
        if not settings.dld_rent_csv_url:
            raise SkipJob("DLD_RENT_CSV_URL не задан")
        return download_csv(settings.dld_rent_csv_url, Path(settings.raw_dir) / "dld_rent.csv")

    def normalize(self, raw: Path) -> Iterator[dict]:
        for chunk in pd.read_csv(raw, chunksize=CHUNK_SIZE, low_memory=False):
            cols = {k: pick_column(chunk, *v) for k, v in COLUMN_CANDIDATES.items()}
            missing = [k for k in REQUIRED_COLUMNS if cols[k] is None]
            if missing:
                raise ValueError(
                    f"CSV не содержит ожидаемых колонок {missing}; "
                    f"есть: {list(chunk.columns)[:25]}"
                )

            starts = pd.to_datetime(chunk[cols["start_date"]], errors="coerce", dayfirst=True)
            chunk = chunk[starts.dt.year >= settings.sales_since_year]
            starts = starts[starts.dt.year >= settings.sales_since_year]
            ends = (
                pd.to_datetime(chunk[cols["end_date"]], errors="coerce", dayfirst=True)
                if cols["end_date"] else None
            )

            for i, ((_, row), start) in enumerate(zip(chunk.iterrows(), starts, strict=False)):
                area_sqm = clean(row.get(cols["area_sqm"])) if cols["area_sqm"] else None
                rent = clean(row.get(cols["annual_rent_aed"]))
                match_name = None
                for src in ("building_name", "project_name"):
                    if cols[src]:
                        match_name = clean(row.get(cols[src]))
                        if match_name:
                            break
                end = ends.iloc[i] if ends is not None else None
                yield {
                    "dld_contract_id": str(clean(row.get(cols["dld_contract_id"])) or "") or None,
                    "start_date": None if pd.isna(start) else start.date(),
                    "end_date": None if end is None or pd.isna(end) else end.date(),
                    "annual_rent_aed": rent if rent and rent > 0 else None,
                    "area_sqft": round(area_sqm * SQM_TO_SQFT, 2) if area_sqm else None,
                    "_match_name": match_name,
                    "_area_name": clean(row.get(cols["area_name"])) if cols["area_name"] else None,
                }

    def load(self, db: Session, records: Iterable[dict]) -> int:
        matcher = BuildingMatcher(db)
        batch: list[dict] = []
        review_ids: list[str] = []
        count = 0

        def flush() -> None:
            nonlocal count
            if not batch:
                return
            db.execute(UPSERT, batch)
            if review_ids:
                db.execute(ENQUEUE_REVIEW, {"ids": review_ids})
            db.commit()
            count += len(batch)
            batch.clear()
            review_ids.clear()

        for r in records:
            match_name = r.pop("_match_name", None)
            area_name = r.pop("_area_name", None)
            m = matcher.match(match_name)
            r.update(
                building_id=m.building_id,
                match_status=m.status,
                match_score=m.score,
                raw=json.dumps({"match_name": match_name, "area": area_name}),
            )
            batch.append(r)
            if m.status == "review":
                review_ids.append(r["dld_contract_id"])
            if len(batch) >= BATCH_SIZE:
                flush()
        flush()
        return count
