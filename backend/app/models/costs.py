from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServiceCharge(Base):
    __tablename__ = "service_charges"
    __table_args__ = (UniqueConstraint("building_id", "year", name="uq_service_charge_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    year: Mapped[int] = mapped_column(Integer)
    rate_aed_sqft: Mapped[float] = mapped_column(Numeric)  # AED/sqft/год
    source: Mapped[str | None] = mapped_column(Text)
    scraped_at: Mapped[datetime | None] = mapped_column()


class CoolingTariff(Base):
    """Ручной ingestion-слой district cooling. История не перезаписывается:
    новая строка = новая версия тарифа, source_note и entered_by обязательны."""

    __tablename__ = "cooling_tariffs"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('building','district','provider_default')", name="ck_cooling_scope"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE")
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="CASCADE")
    )
    consumption_fils_per_rth: Mapped[float | None] = mapped_column(Numeric)
    demand_aed_per_rt_year: Mapped[float | None] = mapped_column(Numeric)
    fuel_surcharge_pct: Mapped[float | None] = mapped_column(Numeric)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source_note: Mapped[str] = mapped_column(Text)  # откуда взято: URL, документ, звонок
    entered_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
