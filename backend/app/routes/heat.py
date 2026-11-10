"""Spatial heat, overview metrics, hotspots, and SUHII prediction endpoints."""

from typing import Literal
from fastapi import APIRouter
from app.schemas import ZoneRequest, PredictionResponse, PredictionBatchResponse
from app.services.data import CITIES
from app.services.state import state, zone, get_city_overview

router = APIRouter(prefix="/api", tags=["heat"])


@router.get("/cities")
def cities():
    """List supported cities and geographic center coordinates."""
    return [{"name": name, "center": center} for name, center in CITIES.items()]


@router.get("/overview")
def overview(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    mode: Literal["normal", "demo"] | None = None,
):
    """Aggregate urban heat, exposed population, and priority risk zones for a city."""
    return get_city_overview(city, mode)


@router.get("/heat/map")
def heat_map(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    mode: Literal["normal", "demo"] | None = None,
):
    """GeoJSON FeatureCollection with spatial predictions, SHAP, and risk scores."""
    return state(city, mode)["data"]


@router.get("/heat/hotspots")
def hotspots(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    mode: Literal["normal", "demo"] | None = None,
):
    """Filtered list of zone properties classified as extreme heat hotspots."""
    return [
        f["properties"]
        for f in state(city, mode)["data"]["features"]
        if f["properties"]["hotspot"]
    ]


@router.post(
    "/heat/predict", response_model=PredictionResponse | PredictionBatchResponse
)
def predict(req: ZoneRequest):
    """Predict SUHII and intervals for a single zone or batch across the city via POST."""
    if req.zone_id:
        return zone(req.city, req.zone_id, req.mode)
    selected = state(req.city, req.mode)
    return {
        "predictions": [f["properties"] for f in selected["data"]["features"]],
        "model": selected["model"],
    }


@router.get(
    "/heat/predict", response_model=PredictionResponse | PredictionBatchResponse
)
def predict_get(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    zone_id: str | None = None,
    mode: Literal["normal", "demo"] | None = None,
):
    """Predict SUHII and intervals for a single zone or batch across the city via GET."""
    if zone_id:
        return zone(city, zone_id, mode)
    selected = state(city, mode)
    return {
        "predictions": [f["properties"] for f in selected["data"]["features"]],
        "model": selected["model"],
    }
