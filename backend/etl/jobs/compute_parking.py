"""Заполнение buildings.parking_ratio из парковочных полей DLD-транзакций.

Источники (те же fallback CSV, что у dld_sales):
  - bulk-схема: has_parking (0/1 на юнит)
  - ручная выгрузка dubailand.gov.ae: PARKING ("1", "2", "1  0", "EU 0"...)

parking_ratio = среднее число мест на юнит по транзакциям, привязанным
к зданию (auto/manual). Это оценка: булев has_parking занижает счёт
многоместных юнитов, но порядок величины (0..2) корректен.

Запуск: python -m etl.jobs.compute_parking
"""
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger, setup_logging

log = get_logger(__name__)

CHUNK_SIZE = 100_000
_FIRST_INT = re.compile(r"\d+")


def parse_parking(value) -> float | None:
    """'2' -> 2; '1  0' -> 1 (первое число); 'EU 0' -> 0; NaN/мусор -> None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    m = _FIRST_INT.search(str(value))
    return float(m.group()) if m else None


def load_tx_parking(csv_paths: list[Path]) -> pd.DataFrame:
    """Все транзакции с парковочным полем: DataFrame[tx_id, parking]."""
    frames = []
    for path in csv_paths:
        for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE, low_memory=False):
            cols_lower = {c.lower(): c for c in chunk.columns}
            tx_col = cols_lower.get("transaction_id") or cols_lower.get("transaction_number")
            park_col = cols_lower.get("has_parking") or cols_lower.get("parking")
            if not tx_col or not park_col:
                continue
            df = pd.DataFrame({
                "tx_id": chunk[tx_col].astype(str),
                "parking": chunk[park_col].map(parse_parking),
            }).dropna(subset=["parking"])
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["tx_id", "parking"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["tx_id"])


def main() -> None:
    setup_logging()
    raw_dir = Path(settings.raw_dir)
    csv_paths = sorted(raw_dir.glob("dld_sales_fallback*.csv"))
    if (raw_dir / "dld_sales.csv").exists():
        csv_paths.insert(0, raw_dir / "dld_sales.csv")
    if not csv_paths:
        log.error("no_sales_csv_found", raw_dir=str(raw_dir))
        return

    tx_parking = load_tx_parking(csv_paths)
    log.info("tx_parking_loaded", rows=len(tx_parking))

    db = SessionLocal()
    try:
        matched = pd.read_sql(
            "SELECT dld_tx_id AS tx_id, building_id FROM sales_transactions "
            "WHERE building_id IS NOT NULL AND match_status IN ('auto', 'manual')",
            db.connection(),
        )
        merged = matched.merge(tx_parking, on="tx_id", how="inner")
        ratios = merged.groupby("building_id")["parking"].mean().round(2)
        log.info("parking_ratios_computed", buildings=len(ratios), tx_used=len(merged))

        db.execute(
            text("UPDATE buildings SET parking_ratio = :ratio WHERE id = :bid"),
            [{"bid": int(bid), "ratio": float(r)} for bid, r in ratios.items()],
        )
        db.commit()
        log.info("parking_ratios_saved", buildings=len(ratios))
    finally:
        db.close()


if __name__ == "__main__":
    main()
