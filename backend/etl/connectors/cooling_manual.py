"""Ручной ingestion-слой district cooling из data/cooling_tariffs.yaml.

Файл версионируется в git; каждая запись обязана иметь source_note и entered_by.
Обновление тарифа = новая запись с новым effective_from, старую не менять.
"""
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from etl.connectors.base import Connector, SkipJob

REQUIRED = ("provider", "scope", "effective_from", "source_note", "entered_by")
VALID_SCOPES = ("building", "district", "provider_default")


def validate_entry(entry: dict) -> list[str]:
    """Возвращает список ошибок записи (пустой = валидна). Чистая функция для тестов."""
    errors = [f"missing field '{f}'" for f in REQUIRED if not entry.get(f)]
    if entry.get("scope") not in VALID_SCOPES:
        errors.append(f"scope must be one of {VALID_SCOPES}")
    if entry.get("scope") == "building" and not entry.get("building_name"):
        errors.append("scope=building requires building_name")
    if entry.get("scope") == "district" and not entry.get("district_name"):
        errors.append("scope=district requires district_name")
    return errors


class CoolingManualConnector(Connector):
    name = "cooling_manual"

    def fetch(self) -> list[dict]:
        path = Path(settings.data_dir) / "cooling_tariffs.yaml"
        if not path.exists():
            raise SkipJob(f"{path} не найден")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("tariffs", [])

    def normalize(self, raw: list[dict]) -> list[dict]:
        records = []
        for i, entry in enumerate(raw):
            errors = validate_entry(entry)
            if errors:
                raise ValueError(f"cooling_tariffs.yaml, запись #{i}: {'; '.join(errors)}")
            records.append(entry)
        return records

    def load(self, db: Session, records: list[dict]) -> int:
        count = 0
        for r in records:
            building_id = None
            district_id = None
            if r["scope"] == "building":
                building_id = db.execute(
                    text("SELECT building_id FROM building_aliases WHERE lower(alias) = lower(:n) LIMIT 1"),
                    {"n": r["building_name"]},
                ).scalar()
                if building_id is None:
                    continue  # здание ещё не в гео-слое — подхватится при следующем запуске
            elif r["scope"] == "district":
                district_id = db.execute(
                    text("SELECT id FROM districts WHERE lower(name_en) = lower(:n) LIMIT 1"),
                    {"n": r["district_name"]},
                ).scalar()
                if district_id is None:
                    continue

            exists = db.execute(
                text(
                    """
                    SELECT 1 FROM cooling_tariffs
                    WHERE provider = :provider AND scope = :scope
                      AND effective_from = :effective_from
                      AND building_id IS NOT DISTINCT FROM :building_id
                      AND district_id IS NOT DISTINCT FROM :district_id
                    """
                ),
                {
                    "provider": r["provider"],
                    "scope": r["scope"],
                    "effective_from": r["effective_from"],
                    "building_id": building_id,
                    "district_id": district_id,
                },
            ).scalar()
            if exists:
                continue

            db.execute(
                text(
                    """
                    INSERT INTO cooling_tariffs
                        (provider, scope, building_id, district_id, consumption_fils_per_rth,
                         demand_aed_per_rt_year, fuel_surcharge_pct, effective_from,
                         effective_to, source_note, entered_by)
                    VALUES
                        (:provider, :scope, :building_id, :district_id, :consumption,
                         :demand, :fuel, :effective_from, :effective_to, :source_note, :entered_by)
                    """
                ),
                {
                    "provider": r["provider"],
                    "scope": r["scope"],
                    "building_id": building_id,
                    "district_id": district_id,
                    "consumption": r.get("consumption_fils_per_rth"),
                    "demand": r.get("demand_aed_per_rt_year"),
                    "fuel": r.get("fuel_surcharge_pct"),
                    "effective_from": r["effective_from"],
                    "effective_to": r.get("effective_to"),
                    "source_note": r["source_note"],
                    "entered_by": r["entered_by"],
                },
            )
            count += 1
        db.commit()
        return count
