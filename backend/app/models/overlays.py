from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DistrictDemographics(Base):
    """Демографический слой по районам.

    Количественные поля (population, density, emirati/expat) — реальные агрегаты
    Dubai Statistics Center. dominant_community/communities — ОРИЕНТИРОВОЧНЫЕ
    тенденции из открытых источников (is_indicative), не официальная статистика.
    """

    __tablename__ = "district_demographics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text, unique=True)
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer)
    density_per_km2: Mapped[float | None] = mapped_column(Numeric)
    emirati_pct: Mapped[float | None] = mapped_column(Numeric)
    expat_pct: Mapped[float | None] = mapped_column(Numeric)
    dominant_community: Mapped[str | None] = mapped_column(Text)
    communities: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[str | None] = mapped_column(Text)
    is_indicative: Mapped[bool] = mapped_column(Boolean, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Poi(Base):
    """Достопримечательность/точка интереса из OSM для маркеров на карте."""

    __tablename__ = "pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    osm_ref: Mapped[str] = mapped_column(Text, unique=True)
    name_en: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    geom = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    source: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
