"""district demographics overlay + points of interest

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09

"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Демографический слой по районам. Количественные поля (population, density,
    # emirati/expat) — реальные агрегаты DSC. dominant_community/communities —
    # ОРИЕНТИРОВОЧНЫЕ тенденции из открытых источников (is_indicative=true),
    # не официальная статистика; в UI подписывается соответствующе.
    op.create_table(
        "district_demographics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name_en", sa.Text, nullable=False, unique=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("population", sa.Integer),
        sa.Column("density_per_km2", sa.Numeric),
        sa.Column("emirati_pct", sa.Numeric),
        sa.Column("expat_pct", sa.Numeric),
        sa.Column("dominant_community", sa.Text),  # категория для окраски
        sa.Column("communities", sa.Text),          # список ориентировочных диаспор
        sa.Column("note", sa.Text),
        sa.Column("sources", sa.Text),
        sa.Column("is_indicative", sa.Boolean, server_default="true", nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Достопримечательности/POI из OSM для маркеров-«шариков» на карте.
    op.create_table(
        "pois",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("osm_ref", sa.Text, nullable=False, unique=True),
        sa.Column("name_en", sa.Text),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("source", sa.Text),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX ix_pois_geom ON pois USING gist (geom)")
    op.execute("CREATE INDEX ix_demographics_geom ON district_demographics USING gist (geom)")


def downgrade() -> None:
    op.drop_table("pois")
    op.drop_table("district_demographics")
