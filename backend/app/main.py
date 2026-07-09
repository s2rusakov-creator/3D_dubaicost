from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    buildings,
    coverage,
    districts,
    layers,
    map as map_api,
    pois,
    review,
    tiles,
)
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="DubaiCost API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.api_cors_origins.split(",")],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(map_api.router, prefix="/api")
app.include_router(buildings.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
app.include_router(coverage.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(tiles.router, prefix="/api")
app.include_router(districts.router, prefix="/api")
app.include_router(pois.router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
