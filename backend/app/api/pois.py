import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["pois"])

MAX_POIS = 500


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        minx, miny, maxx, maxy = (float(p) for p in bbox.split(","))
    except ValueError:
        raise HTTPException(400, "bbox must be 'minx,miny,maxx,maxy'") from None
    return minx, miny, maxx, maxy


@router.get("/pois")
def get_pois(
    bbox: str = Query(..., description="minx,miny,maxx,maxy (lon/lat, EPSG:4326)"),
    db: Session = Depends(get_db),
) -> dict:
    """POI-маркеры в bbox (GeoJSON точки)."""
    minx, miny, maxx, maxy = _parse_bbox(bbox)
    rows = db.execute(
        text(
            """
            SELECT id, name_en, category, ST_AsGeoJSON(geom) AS geometry
            FROM pois
            WHERE geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
            LIMIT :lim
            """
        ),
        {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy, "lim": MAX_POIS},
    ).mappings().all()

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(r["geometry"]) if r["geometry"] else None,
            "properties": {"id": r["id"], "name": r["name_en"], "category": r["category"]},
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}
