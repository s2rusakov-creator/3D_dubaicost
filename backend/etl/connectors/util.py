"""Утилиты коннекторов: терпимость к вариациям схемы CSV и NaN из pandas."""
import math
from typing import Any

import pandas as pd


def pick_column(df: pd.DataFrame, *candidates: str) -> str | None:
    """Первое существующее имя колонки из кандидатов (схемы DLD слегка плавают).

    Регистронезависимо: ручная выгрузка с dubailand.gov.ae использует ВЕРХНИЙ
    РЕГИСТР (TRANSACTION_NUMBER), а bulk CSV — нижний (transaction_id).
    """
    lower_map = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name in df.columns:
            return name
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def clean(value: Any) -> Any:
    """NaN/NaT из pandas -> None, чтобы в БД не попадали NaN::numeric."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NaT:
        return None
    return value


def check_volume_anomaly(prev_rows: int | None, new_rows: int) -> str | None:
    """Сообщение об аномалии объёма данных между запусками, либо None.

    Алерт (не блокировка): резкое падение — источник мог сломаться,
    резкий рост — в датасет мог попасть мусор.
    """
    if prev_rows is None or prev_rows < 100:
        return None
    if new_rows < prev_rows * 0.5:
        return f"объём упал с {prev_rows} до {new_rows} строк (>50%)"
    if new_rows > prev_rows * 3:
        return f"объём вырос с {prev_rows} до {new_rows} строк (>3x)"
    return None
