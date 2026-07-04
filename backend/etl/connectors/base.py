from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.alerts import send_alert
from app.core.logging import get_logger
from app.models import IngestionRun
from etl.connectors.util import check_volume_anomaly

log = get_logger(__name__)


class SkipJob(Exception):
    """Джоб пропущен (например, не настроены креды) — это не ошибка."""


class Connector(ABC):
    """Общий интерфейс источника данных: fetch() -> normalize() -> validate() -> load().

    normalize() может вернуть list (маленькие источники) или генератор
    (bulk CSV на миллионы строк — не держим всё в памяти).
    """

    name: str = "base"
    required_fields: tuple[str, ...] = ()

    @abstractmethod
    def fetch(self) -> Any:
        """Забрать сырые данные (файл, HTML, YAML...)."""

    @abstractmethod
    def normalize(self, raw: Any) -> Iterable[dict]:
        """Привести к записям с едиными единицами измерения (list или генератор)."""

    def validate(self, records: Iterable[dict]) -> Iterable[dict]:
        """Отбросить записи без обязательных полей."""
        if not self.required_fields:
            return records
        if isinstance(records, list):
            valid = [r for r in records if all(r.get(f) is not None for f in self.required_fields)]
            dropped = len(records) - len(valid)
            if dropped:
                log.warning("records_dropped", connector=self.name, dropped=dropped)
            return valid
        return (r for r in records if all(r.get(f) is not None for f in self.required_fields))

    @abstractmethod
    def load(self, db: Session, records: Iterable[dict]) -> int:
        """Идемпотентный upsert в БД. Возвращает число записанных строк."""


def _previous_rows(db: Session, source: str, current_run_id: int) -> int | None:
    return db.execute(
        text(
            """
            SELECT rows_upserted FROM ingestion_runs
            WHERE source = :source AND status = 'success'
              AND rows_upserted IS NOT NULL AND id != :run_id
            ORDER BY id DESC LIMIT 1
            """
        ),
        {"source": source, "run_id": current_run_id},
    ).scalar()


def run_connector(connector: Connector, db: Session) -> None:
    """Запуск с журналированием в ingestion_runs и алертами (падение, аномалия объёма)."""
    run = IngestionRun(source=connector.name)
    db.add(run)
    db.commit()
    try:
        raw = connector.fetch()
        records = connector.normalize(raw)
        if isinstance(records, list):
            run.rows_in = len(records)
        records = connector.validate(records)
        run.rows_upserted = connector.load(db, records)
        run.status = "success"
        log.info("connector_done", connector=connector.name,
                 rows_in=run.rows_in, upserted=run.rows_upserted)

        anomaly = check_volume_anomaly(
            _previous_rows(db, connector.name, run.id), run.rows_upserted or 0
        )
        if anomaly:
            send_alert(f"ETL '{connector.name}': аномалия — {anomaly}")
    except SkipJob as exc:
        run.status = "success"
        run.error = f"skipped: {exc}"
        log.info("connector_skipped", connector=connector.name, reason=str(exc))
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error = str(exc)[:2000]
        send_alert(f"ETL job '{connector.name}' failed: {exc}")
        log.error("connector_failed", connector=connector.name, error=str(exc))
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
