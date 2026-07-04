from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True)
    source: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL")
    )
    name_en: Mapped[str | None] = mapped_column(Text)
    master_project: Mapped[str | None] = mapped_column(Text)
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True)
    centroid = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    height_m: Mapped[float | None] = mapped_column(Numeric)
    floors: Mapped[int | None] = mapped_column(Integer)
    built_year: Mapped[int | None] = mapped_column(Integer)
    units_count: Mapped[int | None] = mapped_column(Integer)
    parking_spaces: Mapped[int | None] = mapped_column(Integer)
    parking_ratio: Mapped[float | None] = mapped_column(Numeric)  # spaces/units, NULL = нет данных
    cooling_provider: Mapped[str | None] = mapped_column(Text)  # empower | tabreed | none
    source: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BuildingAlias(Base):
    """Как здание называется в разных источниках (DLD, RERA, вручную) — сердце matching'а."""

    __tablename__ = "building_aliases"
    __table_args__ = (UniqueConstraint("alias", "source", name="uq_alias_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, server_default="false")
