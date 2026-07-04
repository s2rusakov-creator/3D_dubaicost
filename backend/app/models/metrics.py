from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Метрики, которые считает ETL. built_year/parking_ratio живут в buildings.
METRICS = ("price_sqft", "rent_sqft", "service_charge", "cooling_est")


class BuildingMetric(Base):
    """Предрассчитанные агрегаты по зданию за месяц. Отсутствие строки = нет данных."""

    __tablename__ = "building_metrics"
    __table_args__ = (Index("ix_metrics_metric_period", "metric", "period"),)

    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), primary_key=True
    )
    period: Mapped[date] = mapped_column(Date, primary_key=True)  # первый день месяца
    metric: Mapped[str] = mapped_column(Text, primary_key=True)
    value_median: Mapped[float | None] = mapped_column(Numeric)
    value_mean: Mapped[float | None] = mapped_column(Numeric)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IngestionRun(Base):
    """Журнал ETL-джобов: питает coverage-страницу и алерты."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(Text, server_default="running")  # running/success/failed
    rows_in: Mapped[int | None] = mapped_column(Integer)
    rows_upserted: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)


class MatchReviewQueue(Base):
    """Очередь ручной валидации гео-маппинга транзакция -> здание."""

    __tablename__ = "match_review_queue"
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(Text)  # sales_transaction | rent_contract
    entity_id: Mapped[int] = mapped_column(BigInteger)
    candidate_building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE")
    )
    score: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    resolved_by: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column()
