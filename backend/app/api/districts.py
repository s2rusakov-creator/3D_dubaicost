import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["districts"])


@router.get("/districts")
def get_districts(db: Session = Depends(get_db)) -> dict:
    """Демографические зоны (GeoJSON).

    dominant_community/communities — ОРИЕНТИРОВОЧНЫЕ тенденции из открытых
    источников (is_indicative), не официальная статистика.
    """
    rows = db.execute(
        text(
            """
            SELECT name_en, dominant_community, communities, note, sources,
                   is_indicative, population, density_per_km2, emirati_pct, expat_pct,
                   ST_AsGeoJSON(geom) AS geometry
            FROM district_demographics
            WHERE geom IS NOT NULL
            """
        )
    ).mappings().all()

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(r["geometry"]),
            "properties": {
                "name": r["name_en"],
                "dominant_community": r["dominant_community"],
                "communities": r["communities"],
                "note": r["note"],
                "sources": r["sources"],
                "is_indicative": r["is_indicative"],
                "population": r["population"],
                "density_per_km2": float(r["density_per_km2"])
                if r["density_per_km2"] is not None else None,
                "emirati_pct": float(r["emirati_pct"]) if r["emirati_pct"] is not None else None,
                "expat_pct": float(r["expat_pct"]) if r["expat_pct"] is not None else None,
            },
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}
