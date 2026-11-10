"""Data ingestion, provenance tracking, satellite catalog queries, and weather time series."""

import asyncio
import os
from typing import Literal
from fastapi import APIRouter
from app.db import records, POSTGIS, assets, acquisition_scope, persist_acquisition
from app.schemas import AreaRequest
from app.schemas.evidence import CityName, EvidenceAsset, EvidenceAssetSummary, LayersResponse
from app.services.data import CITIES
from app.services.state import activate_demo
from app.services import sources, ai
from app.provenance import asset_provenance
from app.services.evidence import get_asset, live_asset_summaries, map_layers

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/assets", response_model=list[EvidenceAssetSummary])
def evidence_assets(city: CityName = "Ahmedabad"):
    """List normal-mode evidence metadata for one city."""
    return live_asset_summaries(city)


@router.get("/assets/{asset_id}", response_model=EvidenceAsset)
def evidence_asset(asset_id: str, city: CityName = "Ahmedabad"):
    """Retrieve a normal-mode evidence asset and its source payload."""
    return get_asset(asset_id, city)


@router.get("/layers", response_model=LayersResponse)
def evidence_layers(city: CityName = "Ahmedabad"):
    """Return map layers derived only from validated, city-scoped evidence."""
    return {"city": city, "layers": map_layers(city)}


@router.get("/status")
def data_status():
    """System health check for external data providers, database engine, and catalogs."""
    return {
        "providers": ai.provider_status(),
        "database": "PostGIS" if POSTGIS else "SQLite fallback",
        "earth_engine": {
            "configured": bool(os.getenv("EARTH_ENGINE_PROJECT")),
            "credentials_configured": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "latest_success": next(
                (a["provenance"].get("retrieved_at") for a in assets(category="satellite", limit=30)
                 if "Landsat" in a["source"] or a["source"] in {"modis", "sentinel"}),
                None,
            ),
        },
        "catalog": sources.DATASET_CATALOG,
        "ingestions": [
            {
                "id": r["id"],
                "source": r.get("source", r.get("metadata", {}).get("source")),
                "created_at": r["created_at"],
            }
            for kind in ["weather", "osm", "satellite", "monitoring"]
            for r in records(kind, 8)
        ],
        "assets": [
            {key: asset[key] for key in ("id", "city", "category", "source", "mode", "analysis_ready", "provenance", "created_at")}
            for asset in assets(limit=40)
        ],
        "prediction_data": "No default analysis dataset. Live evidence is stored separately until validated processing is available.",
    }


@router.get("/records")
def data_records(
    kind: Literal["weather", "osm", "satellite", "monitoring"] = "satellite",
):
    """Retrieve raw persisted ingested records by source type."""
    return records(kind, 10)


@router.get("/series")
def data_series(city: str | None = None):
    """Hourly temperature and relative humidity time series from ingested weather observations."""
    stored = records("weather", 100)
    if city:
        stored = [record for record in stored if record.get("city") == city]
    return sources.weather_series(stored)


@router.post("/ingest")
async def ingest(req: AreaRequest):
    """Dispatch ingestion request across live sources (weather, OSM, WorldPop, Sentinel, OpenAQ, GEE)."""
    lat, lon = (
        (req.latitude, req.longitude) if req.latitude is not None else CITIES[req.city]
    )
    if req.source == "demo":
        prepared = await asyncio.to_thread(activate_demo, req.city, req.boundary, req.rural_reference)
        return {
            "source": "synthetic_demo",
            "mode": "demo",
            "zones": len(prepared["data"]["features"]),
            "metadata": prepared["data"]["metadata"],
        }
    result = None
    category = req.source
    with acquisition_scope():
        if req.source == "weather":
            result = await sources.weather(
                lat,
                lon,
                str(req.start_date) if req.start_date else None,
                str(req.end_date) if req.end_date else None,
            )
        elif req.source == "osm":
            result = await sources.osm(lat, lon)
        elif req.source == "worldpop":
            result = await sources.worldpop()
        elif req.source == "nasa_power":
            if not req.start_date or not req.end_date:
                raise ValueError("NASA POWER requires a start and end date.")
            result = await sources.nasa_power(
                lat, lon, str(req.start_date), str(req.end_date)
            )
        elif req.source == "copernicus":
            if not req.start_date or not req.end_date:
                raise ValueError("Copernicus catalog search requires a start and end date.")
            result = await sources.copernicus_catalog(
                lat, lon, str(req.start_date), str(req.end_date)
            )
        elif req.source == "ghsl":
            result = await sources.ghsl_catalog(lat, lon)
        elif req.source in ["stac", "sentinel_indices"]:
            result = await sources.sentinel_catalog(
                lat,
                lon,
                str(req.start_date) if req.start_date else "2025-05-01",
                str(req.end_date) if req.end_date else "2025-05-31",
            )
            if req.source == "sentinel_indices":
                result = await asyncio.to_thread(sources.sentinel_indices, result, lat, lon)
        elif req.source == "openaq":
            result = await sources.air_quality(lat, lon)
        elif req.source == "groundwater":
            if hasattr(sources, "groundwater") and callable(getattr(sources, "groundwater")):
                fn = getattr(sources, "groundwater")
                import inspect
                sig = inspect.signature(fn)
                args = [lat, lon]
                if len(sig.parameters) >= 3 or "city" in sig.parameters:
                    args.append(req.city)
                if inspect.iscoroutinefunction(fn):
                    result = await fn(*args)
                else:
                    result = await asyncio.to_thread(fn, *args)
            else:
                result = {
                    "source": "CGWB / India-WRIS groundwater monitoring",
                    "synthetic": False,
                    "city": req.city,
                    "latitude": lat,
                    "longitude": lon,
                    "stations": [],
                    "units": {"depth_below_ground_m": "meters below ground level (mbgl)"},
                    "status": "unavailable",
                    "reason": "CGWB / India-WRIS groundwater monitoring station records unavailable for coordinates.",
                    "setup_instructions": "Configure Central Ground Water Board (CGWB) / India-WRIS monitoring station adapter.",
                }
            if isinstance(result.get("units"), str):
                result["units"] = {"depth_below_ground_m": result["units"]}
        else:
            if not req.boundary or not req.start_date or not req.end_date:
                raise ValueError("Earth Engine requires a polygon boundary and date range.")
            if req.satellite_product != "landsat":
                result = await asyncio.to_thread(
                    sources.supplementary_earth_engine, req.satellite_product, req.boundary,
                    str(req.start_date), str(req.end_date),
                )
            else:
                result = await asyncio.to_thread(sources.earth_engine, req.boundary, str(req.start_date), str(req.end_date))

    assert result is not None
    metadata = asset_provenance(result, city=req.city, category=category)
    metadata["analysis_ready"] = False
    return persist_acquisition(category, result, metadata)
