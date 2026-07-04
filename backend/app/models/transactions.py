from datetime import date

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MATCH_STATUSES = ("auto", "manual", "review", "unmatched")


class SalesTransaction(Base):
    __tablename__ = "sales_transactions"
    __table_args__ = (
        CheckConstraint(
            "match_status IN ('auto','manual','review','unmatched')", name="ck_sales_match_status"
        ),
        Index("ix_sales_building_date", "building_id", "tx_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dld_tx_id: Mapped[str] = mapped_column(Text, unique=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL")
    )
    match_status: Mapped[str] = mapped_column(Text, server_default="unmatched")
    match_score: Mapped[float | None] = mapped_column(Numeric)
    tx_date: Mapped[date | None] = mapped_column(Date)
    price_aed: Mapped[float | None] = mapped_column(Numeric)
    area_sqft: Mapped[float | None] = mapped_column(Numeric)
    price_per_sqft: Mapped[float | None] = mapped_column(
        Numeric,
        Computed("CASE WHEN area_sqft > 0 THEN price_aed / area_sqft ELSE NULL END", persisted=True),
    )
    property_type: Mapped[str | None] = mapped_column(Text)
    rooms: Mapped[str | None] = mapped_column(Text)
    is_offplan: Mapped[bool | None] = mapped_column(Boolean)
    raw: Mapped[dict | None] = mapped_column(JSONB)


class RentContract(Base):
    __tablename__ = "rent_contracts"
    __table_args__ = (
        CheckConstraint(
            "match_status IN ('auto','manual','review','unmatched')", name="ck_rent_match_status"
        ),
        Index("ix_rent_building_date", "building_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dld_contract_id: Mapped[str] = mapped_column(Text, unique=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL")
    )
    match_status: Mapped[str] = mapped_column(Text, server_default="unmatched")
    match_score: Mapped[float | None] = mapped_column(Numeric)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    annual_rent_aed: Mapped[float | None] = mapped_column(Numeric)
    area_sqft: Mapped[float | None] = mapped_column(Numeric)
    rent_per_sqft_year: Mapped[float | None] = mapped_column(
        Numeric,
        Computed(
            "CASE WHEN area_sqft > 0 THEN annual_rent_aed / area_sqft ELSE NULL END",
            persisted=True,
        ),
    )
    raw: Mapped[dict | None] = mapped_column(JSONB)
