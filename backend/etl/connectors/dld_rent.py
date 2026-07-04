"""Коннектор арендных контрактов Ejari (Dubai Pulse open data, bulk CSV).

Датасет: https://www.dubaipulse.gov.ae/data/dld-registration/dld_rent_contracts-open
Тот же паттерн, что dld_sales: чанки, батчи, matching с кэшем.
"""
import hashlib
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from etl.connectors.base import Connector, SkipJob
from etl.connectors.dld_sales import CHUNK_SIZE, SQM_TO_SQFT, fetch_with_fallback
from etl.connectors.util import clean, pick_column
from etl.pipeline.matching import BuildingMatcher

log = get_logger(__name__)

BATCH_SIZE = 5_000

COLUMN_CANDIDATES = {
    "dld_contract_id": ("contract_id", "ejari_contract_number", "contract_number"),
    "start_date": ("contract_start_date", "start_date"),
    "end_date": ("contract_end_date", "end_date"),
    "annual_rent_aed": ("annual_amount", "contract_amount"),
    "area_sqm": ("actual_area", "property_size"),
    "building_name": ("ejari_property_name", "building_name_en"),
    "project_name": ("project_name_en", "project_en", "master_project_en"),
    "area_name": ("area_name_en", "area_en"),
    # Только для синтетического ID, если dld_contract_id отсутствует (ручная выгрузка)
    "registration_date": ("registration_date",),
}
# dld_contract_id нет в ручной выгрузке dubailand.gov.ae — синтезируем ID из строки
REQUIRED_COLUMNS = ("start_date", "annual_rent_aed")


def _synthetic_contract_id(row: pd.Series, cols: dict[str, str | None]) -> str:
    """Стабильный ID из содержимого строки — источник без своего contract_id.

    Детерминированный хэш даёт идемпотентность при повторном импорте того же
    файла (ON CONFLICT сработает), но не гарантирует уникальность в теории —
    приемлемо для ручного разового бутстрапа без официального bulk CSV.
    """
    key_cols = ("registration_date", "start_date", "end_date", "annual_rent_aed",
                "area_sqm", "project_name", "area_name")
    raw_key = "|".join(str(row.get(cols[c], "")) for c in key_cols if cols.get(c))
    return "synthetic:" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

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
        raw_dir = Path(settings.raw_dir)
        fallback = raw_dir / "dld_rent_fallback.csv"
        if not settings.dld_rent_csv_url:
            if fallback.exists():
                log.warning("dld_rent_csv_url_not_set_using_fallback", fallback=str(fallback))
                return fallback
            raise SkipJob("DLD_RENT_CSV_URL не задан и fallback-файл отсутствует")
        return fetch_with_fallback(settings.dld_rent_csv_url, raw_dir / "dld_rent.csv", fallback)

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
                contract_id = (
                    str(clean(row.get(cols["dld_contract_id"])) or "") or None
                    if cols["dld_contract_id"] else _synthetic_contract_id(row, cols)
                )
                yield {
                    "dld_contract_id": contract_id,
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
