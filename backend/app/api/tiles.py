"""Векторные тайлы MVT через встроенный в PostGIS ST_AsMVT.

Альтернатива GeoJSON-эндпоинту /api/map для большого числа зданий:
тайлы кэшируются браузером/CDN, нагрузка на БД не растёт с зумом.
Frontend сейчас использует GeoJSON; переключение — смена source в MapView.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import METRICS

router = APIRouter(tags=["tiles"])

BUILDING_COLUMN_LAYERS = {"built_year": "built_year", "parking_ratio": "parking_ratio"}

MVT_METRIC_SQL = text(
    """
    WITH mvtgeom AS (
        SELECT ST_AsMVTGeom(ST_Transform(b.geom, 3857),
                            ST_TileEnvelope(:z, :x, :y)) AS geom,
               b.id, b.name_en AS name, b.height_m,
               m.value_median AS value, m.sample_size
        FROM buildings b
        LEFT JOIN latest_building_metrics m
          ON m.building_id = b.id AND m.metric = :metric
        WHERE b.geom && ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326)
    )
    SELECT ST_AsMVT(mvtgeom.*, 'buildings') FROM mvtgeom
    """
)


@router.get("/tiles/{layer}/{z}/{x}/{y}.pbf")
def get_tile(
    layer: str, z: int, x: int, y: int, db: Session = Depends(get_db)
) -> Response:
    if z < 0 or z > 22 or x < 0 or y < 0 or x >= 2**z or y >= 2**z:
        raise HTTPException(400, "invalid tile coordinates")

    if layer in METRICS:
        sql = MVT_METRIC_SQL
        params = {"z": z, "x": x, "y": y, "metric": layer}
    elif layer in BUILDING_COLUMN_LAYERS:
        col = BUILDING_COLUMN_LAYERS[layer]
        sql = text(
            f"""
            WITH mvtgeom AS (
                SELECT ST_AsMVTGeom(ST_Transform(b.geom, 3857),
                                    ST_TileEnvelope(:z, :x, :y)) AS geom,
                       b.id, b.name_en AS name, b.height_m,
                       b.{col} AS value, NULL::int AS sample_size
                FROM buildings b
                WHERE b.geom && ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326)
            )
            SELECT ST_AsMVT(mvtgeom.*, 'buildings') FROM mvtgeom
            """
        )
        params = {"z": z, "x": x, "y": y}
    else:
        raise HTTPException(400, f"unknown layer '{layer}'")

    tile = db.execute(sql, params).scalar()
    return Response(
        content=bytes(tile) if tile else b"",
        media_type="application/vnd.mapbox-vector-tile",
        headers={"Cache-Control": "public, max-age=3600"},
    )
