"""Ручные соответствия названий из data/alias_overrides.yaml -> building_aliases.

Заполняется по результатам разбора review-очереди: алиас становится verified,
и следующий прогон DLD-коннекторов смэтчит такие транзакции автоматически (exact).
"""
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from etl.connectors.base import Connector, SkipJob

log = get_logger(__name__)


class AliasOverridesConnector(Connector):
    name = "alias_overrides"
    required_fields = ("alias", "building_name")

    def fetch(self) -> list[dict]:
        path = Path(settings.data_dir) / "alias_overrides.yaml"
        if not path.exists():
            raise SkipJob(f"{path} не найден")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("aliases", [])

    def normalize(self, raw: list[dict]) -> list[dict]:
        return [
            {
                "alias": e.get("alias"),
                "building_name": e.get("building_name"),
                "source": e.get("source", "manual"),
            }
            for e in raw
        ]

    def load(self, db: Session, records: list[dict]) -> int:
        count = 0
        for r in records:
            building_id = db.execute(
                text(
                    """
                    SELECT building_id FROM building_aliases
                    WHERE lower(alias) = lower(:name)
                    UNION
                    SELECT id FROM buildings WHERE lower(name_en) = lower(:name)
                    LIMIT 1
                    """
                ),
                {"name": r["building_name"]},
            ).scalar()
            if building_id is None:
                log.warning("alias_target_not_found", building_name=r["building_name"])
                continue
            db.execute(
                text(
                    """
                    INSERT INTO building_aliases (building_id, alias, source, verified)
                    VALUES (:bid, :alias, :source, true)
                    ON CONFLICT (alias, source) DO UPDATE SET
                        building_id = EXCLUDED.building_id, verified = true
                    """
                ),
                {"bid": building_id, "alias": r["alias"], "source": r["source"]},
            )
            count += 1
        db.commit()
        return count
