"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-03

"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "districts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("name_ar", sa.Text),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
        ),
        sa.Column("source", sa.Text),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_districts_geom", "districts", ["geom"], postgresql_using="gist")

    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("district_id", sa.Integer, sa.ForeignKey("districts.id", ondelete="SET NULL")),
        sa.Column("name_en", sa.Text),
        sa.Column("master_project", sa.Text),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
        ),
        sa.Column(
            "centroid",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
        ),
        sa.Column("height_m", sa.Numeric),
        sa.Column("floors", sa.Integer),
        sa.Column("built_year", sa.Integer),
        sa.Column("units_count", sa.Integer),
        sa.Column("parking_spaces", sa.Integer),
        sa.Column("parking_ratio", sa.Numeric),
        sa.Column("cooling_provider", sa.Text),
        sa.Column("source", sa.Text),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_buildings_geom", "buildings", ["geom"], postgresql_using="gist")
    op.create_index(
        "ix_buildings_name_trgm",
        "buildings",
        ["name_en"],
        postgresql_using="gin",
        postgresql_ops={"name_en": "gin_trgm_ops"},
    )
    op.create_index("ix_buildings_district", "buildings", ["district_id"])

    op.create_table(
        "building_aliases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "building_id",
            sa.Integer,
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("verified", sa.Boolean, server_default="false", nullable=False),
        sa.UniqueConstraint("alias", "source", name="uq_alias_source"),
    )
    op.create_index(
        "ix_aliases_trgm",
        "building_aliases",
        ["alias"],
        postgresql_using="gin",
        postgresql_ops={"alias": "gin_trgm_ops"},
    )

    op.create_table(
        "sales_transactions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("dld_tx_id", sa.Text, nullable=False, unique=True),
        sa.Column("building_id", sa.Integer, sa.ForeignKey("buildings.id", ondelete="SET NULL")),
        sa.Column("match_status", sa.Text, server_default="unmatched", nullable=False),
        sa.Column("match_score", sa.Numeric),
        sa.Column("tx_date", sa.Date),
        sa.Column("price_aed", sa.Numeric),
        sa.Column("area_sqft", sa.Numeric),
        sa.Column(
            "price_per_sqft",
            sa.Numeric,
            sa.Computed(
                "CASE WHEN area_sqft > 0 THEN price_aed / area_sqft ELSE NULL END",
                persisted=True,
            ),
        ),
        sa.Column("property_type", sa.Text),
        sa.Column("rooms", sa.Text),
        sa.Column("is_offplan", sa.Boolean),
        sa.Column("raw", JSONB),
        sa.CheckConstraint(
            "match_status IN ('auto','manual','review','unmatched')",
            name="ck_sales_match_status",
        ),
    )
    op.create_index("ix_sales_building_date", "sales_transactions", ["building_id", "tx_date"])
    op.create_index(
        "ix_sales_tx_date_brin", "sales_transactions", ["tx_date"], postgresql_using="brin"
    )

    op.create_table(
        "rent_contracts",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("dld_contract_id", sa.Text, nullable=False, unique=True),
        sa.Column("building_id", sa.Integer, sa.ForeignKey("buildings.id", ondelete="SET NULL")),
        sa.Column("match_status", sa.Text, server_default="unmatched", nullable=False),
        sa.Column("match_score", sa.Numeric),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("annual_rent_aed", sa.Numeric),
        sa.Column("area_sqft", sa.Numeric),
        sa.Column(
            "rent_per_sqft_year",
            sa.Numeric,
            sa.Computed(
                "CASE WHEN area_sqft > 0 THEN annual_rent_aed / area_sqft ELSE NULL END",
                persisted=True,
            ),
        ),
        sa.Column("raw", JSONB),
        sa.CheckConstraint(
            "match_status IN ('auto','manual','review','unmatched')",
            name="ck_rent_match_status",
        ),
    )
    op.create_index("ix_rent_building_date", "rent_contracts", ["building_id", "start_date"])
    op.create_index(
        "ix_rent_start_date_brin", "rent_contracts", ["start_date"], postgresql_using="brin"
    )

    op.create_table(
        "service_charges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "building_id",
            sa.Integer,
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("rate_aed_sqft", sa.Numeric, nullable=False),
        sa.Column("source", sa.Text),
        sa.Column("scraped_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("building_id", "year", name="uq_service_charge_year"),
    )

    op.create_table(
        "cooling_tariffs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("building_id", sa.Integer, sa.ForeignKey("buildings.id", ondelete="CASCADE")),
        sa.Column("district_id", sa.Integer, sa.ForeignKey("districts.id", ondelete="CASCADE")),
        sa.Column("consumption_fils_per_rth", sa.Numeric),
        sa.Column("demand_aed_per_rt_year", sa.Numeric),
        sa.Column("fuel_surcharge_pct", sa.Numeric),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date),
        sa.Column("source_note", sa.Text, nullable=False),
        sa.Column("entered_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "scope IN ('building','district','provider_default')", name="ck_cooling_scope"
        ),
    )

    op.create_table(
        "building_metrics",
        sa.Column(
            "building_id",
            sa.Integer,
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("period", sa.Date, primary_key=True),
        sa.Column("metric", sa.Text, primary_key=True),
        sa.Column("value_median", sa.Numeric),
        sa.Column("value_mean", sa.Numeric),
        sa.Column("sample_size", sa.Integer),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_metrics_metric_period", "building_metrics", ["metric", "period"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", sa.Text, server_default="running", nullable=False),
        sa.Column("rows_in", sa.Integer),
        sa.Column("rows_upserted", sa.Integer),
        sa.Column("error", sa.Text),
    )

    op.create_table(
        "match_review_queue",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", sa.BigInteger, nullable=False),
        sa.Column(
            "candidate_building_id", sa.Integer, sa.ForeignKey("buildings.id", ondelete="CASCADE")
        ),
        sa.Column("score", sa.Numeric),
        sa.Column("status", sa.Text, server_default="pending", nullable=False),
        sa.Column("resolved_by", sa.Text),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint("status IN ('pending','approved','rejected')", name="ck_review_status"),
    )

    # Единственное, что читает bbox-эндпоинт карты: последний период каждой метрики
    op.execute(
        """
        CREATE MATERIALIZED VIEW latest_building_metrics AS
        SELECT DISTINCT ON (building_id, metric)
               building_id, metric, period, value_median, value_mean, sample_size, computed_at
        FROM building_metrics
        ORDER BY building_id, metric, period DESC
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_latest_metrics_pk ON latest_building_metrics (building_id, metric)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS latest_building_metrics")
    op.drop_table("match_review_queue")
    op.drop_table("ingestion_runs")
    op.drop_table("building_metrics")
    op.drop_table("cooling_tariffs")
    op.drop_table("service_charges")
    op.drop_table("rent_contracts")
    op.drop_table("sales_transactions")
    op.drop_table("building_aliases")
    op.drop_table("buildings")
    op.drop_table("districts")
