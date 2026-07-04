"""Коннектор транзакций продаж DLD (Dubai Pulse open data, bulk CSV ~1.5M строк).

Датасет: https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open
Читаем чанками (генератор), грузим батчами: весь CSV в память не помещается на VPS.
Берём только группу Sales (в датасете ещё Mortgages и Gifts).
"""
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from etl.connectors.base import Connector, SkipJob
from etl.connectors.util import clean, pick_column
from etl.pipeline.matching import BuildingMatcher

log = get_logger(__name__)

SQM_TO_SQFT = 10.7639
CHUNK_SIZE = 50_000
BATCH_SIZE = 5_000

# Схема DLD слегка плавает между выгрузками — на каждое наше поле список кандидатов
COLUMN_CANDIDATES = {
    "dld_tx_id": ("transaction_id", "transaction_number"),
    "tx_date": ("instance_date", "transaction_date"),
    "price_aed": ("actual_worth", "trans_value"),
    "area_sqm": ("procedure_area", "actual_area"),
    "property_type": ("property_type_en", "prop_type_en"),
    "rooms": ("rooms_en", "rooms"),
    "reg_type": ("reg_type_en",),
    # Ручная выгрузка с dubailand.gov.ae даёт это поле напрямую, без reg_type
    "is_offplan": ("is_offplan_en",),
    "group": ("trans_group_en", "group_en"),
    "building_name": ("building_name_en",),
    "project_name": ("project_name_en", "project_en"),
    "area_name": ("area_name_en", "area_en"),
}
REQUIRED_COLUMNS = ("dld_tx_id", "tx_date", "price_aed")

UPSERT = text(
    """
    INSERT INTO sales_transactions
        (dld_tx_id, building_id, match_status, match_score, tx_date,
         price_aed, area_sqft, property_type, rooms, is_offplan, raw)
    VALUES
        (:dld_tx_id, :building_id, :match_status, :match_score, :tx_date,
         :price_aed, :area_sqft, :property_type, :rooms, :is_offplan, CAST(:raw AS jsonb))
    ON CONFLICT (dld_tx_id) DO UPDATE SET
        building_id = EXCLUDED.building_id,
        match_status = CASE WHEN sales_transactions.match_status = 'manual'
                            THEN 'manual' ELSE EXCLUDED.match_status END,
        match_score = EXCLUDED.match_score
    """
)

# Кандидаты со статусом review попадают в очередь ручной валидации (без дублей)
ENQUEUE_REVIEW = text(
    """
    INSERT INTO match_review_queue (entity_type, entity_id, candidate_building_id, score)
    SELECT 'sales_transaction', st.id, st.building_id, st.match_score
    FROM sales_transactions st
    WHERE st.dld_tx_id = ANY(:ids)
      AND st.match_status = 'review'
      AND NOT EXISTS (
          SELECT 1 FROM match_review_queue q
          WHERE q.entity_type = 'sales_transaction'
            AND q.entity_id = st.id AND q.status = 'pending'
      )
    """
)


def download_csv(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    log.info("csv_downloaded", url=url, size_mb=round(dest.stat().st_size / 1e6, 1))
    return dest


def fetch_with_fallback(url: str, dest: Path, fallback: Path) -> Path:
    """Качаем актуальный CSV с официального источника; если он недоступен
    (портал лёг/переехал) — используем заранее подготовленный fallback-файл
    (например, вручную скачанный снапшот с Kaggle). Fallback никогда не
    маскирует рабочий источник — при живом URL всегда качаем свежее.
    """
    try:
        return download_csv(url, dest)
    except (httpx.HTTPError, OSError) as exc:
        if fallback.exists():
            log.warning(
                "csv_download_failed_using_fallback",
                url=url, error=str(exc), fallback=str(fallback),
            )
            return fallback
        raise


def _parse_is_offplan(row: pd.Series, cols: dict[str, str | None]) -> bool | None:
    """Предпочитаем прямое поле is_offplan_en (ручная выгрузка dubailand.gov.ae),
    иначе выводим из reg_type (bulk CSV Dubai Pulse)."""
    if cols["is_offplan"]:
        return "off" in str(clean(row.get(cols["is_offplan"])) or "").lower()
    if cols["reg_type"]:
        return "off" in str(clean(row.get(cols["reg_type"])) or "").lower()
    return None


class DldSalesConnector(Connector):
    name = "dld_sales"
    required_fields = ("dld_tx_id", "tx_date", "price_aed")

    def fetch(self) -> list[Path]:
        # Несколько fallback-файлов допустимо (например, ручная выгрузка
        # dubailand.gov.ae за текущий год + исторический снапшот с Kaggle) —
        # у каждого файла своя схема колонок, normalize() разбирает поштучно.
        raw_dir = Path(settings.raw_dir)
        fallbacks = sorted(raw_dir.glob("dld_sales_fallback*.csv"))
        if not settings.dld_sales_csv_url:
            if fallbacks:
                log.warning(
                    "dld_sales_csv_url_not_set_using_fallback",
                    fallbacks=[str(f) for f in fallbacks],
                )
                return fallbacks
            raise SkipJob("DLD_SALES_CSV_URL не задан и fallback-файлы отсутствуют")
        try:
            return [download_csv(settings.dld_sales_csv_url, raw_dir / "dld_sales.csv")]
        except (httpx.HTTPError, OSError) as exc:
            if fallbacks:
                log.warning(
                    "csv_download_failed_using_fallback",
                    url=settings.dld_sales_csv_url, error=str(exc),
                    fallbacks=[str(f) for f in fallbacks],
                )
                return fallbacks
            raise

    def normalize(self, raw: list[Path]) -> Iterator[dict]:
        for path in raw:
            yield from self._normalize_file(path)

    def _normalize_file(self, raw: Path) -> Iterator[dict]:
        for chunk in pd.read_csv(raw, chunksize=CHUNK_SIZE, low_memory=False):
            cols = {k: pick_column(chunk, *v) for k, v in COLUMN_CANDIDATES.items()}
            missing = [k for k in REQUIRED_COLUMNS if cols[k] is None]
            if missing:
                raise ValueError(
                    f"CSV не содержит ожидаемых колонок {missing}; "
                    f"есть: {list(chunk.columns)[:25]}"
                )

            if cols["group"]:
                chunk = chunk[
                    chunk[cols["group"]].astype(str).str.strip().str.lower() == "sales"
                ]
            # даты DLD в формате DD-MM-YYYY
            dates = pd.to_datetime(chunk[cols["tx_date"]], errors="coerce", dayfirst=True)
            chunk = chunk[dates.dt.year >= settings.sales_since_year]
            dates = dates[dates.dt.year >= settings.sales_since_year]

            for (_, row), tx_date in zip(chunk.iterrows(), dates, strict=False):
                area_sqm = clean(row.get(cols["area_sqm"])) if cols["area_sqm"] else None
                price = clean(row.get(cols["price_aed"]))
                match_name = None
                for src in ("building_name", "project_name"):
                    if cols[src]:
                        match_name = clean(row.get(cols[src]))
                        if match_name:
                            break
                yield {
                    "dld_tx_id": str(clean(row.get(cols["dld_tx_id"])) or "") or None,
                    "tx_date": None if pd.isna(tx_date) else tx_date.date(),
                    "price_aed": price if price and price > 0 else None,
                    "area_sqft": round(area_sqm * SQM_TO_SQFT, 2) if area_sqm else None,
                    "property_type": clean(row.get(cols["property_type"]))
                    if cols["property_type"] else None,
                    "rooms": clean(row.get(cols["rooms"])) if cols["rooms"] else None,
                    "is_offplan": _parse_is_offplan(row, cols),
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
                # минимальный контекст для review-очереди
                raw=json.dumps({"match_name": match_name, "area": area_name}),
            )
            batch.append(r)
            if m.status == "review":
                review_ids.append(r["dld_tx_id"])
            if len(batch) >= BATCH_SIZE:
                flush()
        flush()
        return count
