import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import METRICS

router = APIRouter(tags=["map"])

# Слои, которые берутся из колонок buildings, а не из building_metrics
BUILDING_COLUMN_LAYERS = {"built_year": "built_year", "parking_ratio": "parking_ratio"}
MAX_FEATURES = 5000


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        minx, miny, maxx, maxy = (float(p) for p in bbox.split(","))
    except ValueError:
        raise HTTPException(400, "bbox must be 'minx,miny,maxx,maxy'") from None
    return minx, miny, maxx, maxy


@router.get("/map")
def get_map(
    bbox: str = Query(..., description="minx,miny,maxx,maxy (lon/lat, EPSG:4326)"),
    layer: str = Query("price_sqft"),
    db: Session = Depends(get_db),
) -> dict:
    """GeoJSON зданий в bbox со значением активного слоя. value=null => нет данных."""
    minx, miny, maxx, maxy = _parse_bbox(bbox)

    if layer in METRICS:
        sql = text(
            """
            SELECT b.id, b.name_en, b.height_m, b.built_year,
                   ST_AsGeoJSON(b.geom) AS geometry,
                   m.value_median AS value, m.sample_size, m.period
            FROM buildings b
            LEFT JOIN latest_building_metrics m
              ON m.building_id = b.id AND m.metric = :metric
            WHERE b.geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
            ORDER BY (m.value_median IS NULL)
            LIMIT :lim
            """
        )
        params = {"metric": layer, "minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy,
                  "lim": MAX_FEATURES}
    elif layer in BUILDING_COLUMN_LAYERS:
        col = BUILDING_COLUMN_LAYERS[layer]
        sql = text(
            f"""
            SELECT b.id, b.name_en, b.height_m, b.built_year,
                   ST_AsGeoJSON(b.geom) AS geometry,
                   b.{col} AS value, NULL AS sample_size, NULL AS period
            FROM buildings b
            WHERE b.geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
            ORDER BY (b.{col} IS NULL)
            LIMIT :lim
            """
        )
        params = {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy, "lim": MAX_FEATURES}
    else:
        raise HTTPException(400, f"unknown layer '{layer}'")

    rows = db.execute(sql, params).mappings().all()
    features = [
        {
            "type": "Feature",
            "geometry": json.loads(r["geometry"]) if r["geometry"] else None,
            "properties": {
                "id": r["id"],
                "name": r["name_en"],
                "height_m": float(r["height_m"]) if r["height_m"] is not None else None,
                "value": float(r["value"]) if r["value"] is not None else None,
                "sample_size": r["sample_size"],
                "period": str(r["period"]) if r["period"] else None,
            },
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}
