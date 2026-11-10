"""Shared state management, analysis pipeline invocation, and thread-safe city caching."""

import os
import logging
import threading
import copy
import math
from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.db import records, save
from app.services.data import sample_data
from app.services.ml import load_or_train, infer, describe, train
from app.services.risk import risk

log = logging.getLogger("heatwise")

STATE: Dict[str, Dict[str, Any]] = {}
# STATE is retained as the legacy demo cache for compatibility with test tools.
DEMO_STATE = STATE
REAL_STATE: Dict[str, Dict[str, Any]] = {}
LOCK = threading.RLock()


def resolve_mode(mode: str | None = None) -> str:
    if mode in ("demo", "normal"):
        return mode
    if mode is not None:
        m = str(mode).strip().lower()
        if m in ("demo", "normal"):
            return m
    for env_var in ("HEATWISE_DEMO_MODE", "HEATWISE_MODE", "TESTING"):
        val = os.getenv(env_var, "").strip().lower()
        if val in ("1", "true", "demo"):
            return "demo"
    return "normal"


def state_cache(mode: str | None = None):
    return DEMO_STATE if resolve_mode(mode) == "demo" else REAL_STATE


def real_dataset_ready(data: Dict[str, Any]) -> bool:
    """Require explicit measured labels and lineage, not an absent demo flag."""
    meta = data.get("metadata") or {}
    if not (meta.get("synthetic") is False and meta.get("analysis_ready") is True
            and meta.get("source") and meta.get("acquisition_date")
            and meta.get("rural_method") and meta.get("crs") == "EPSG:4326"):
        return False
    features = data.get("features") or []
    return bool(features) and all(
        all(isinstance(f.get("properties", {}).get(k), (int, float))
            and not isinstance(f["properties"][k], bool) and math.isfinite(f["properties"][k])
            for k in ("lst", "rural_reference"))
        for f in features
    )


def analysis_cached(city: str, mode: str | None = None) -> bool:
    selected_mode = resolve_mode(mode)
    cached = state_cache(selected_mode).get(city)
    if not cached:
        return False
    data = cached.get("data") or {}
    return bool(data.get("metadata", {}).get("synthetic")) if selected_mode == "demo" else real_dataset_ready(data)


def analyze(data: Dict[str, Any], retrain: bool = False) -> Dict[str, Any]:
    """Execute model training or cached load, run inference & SHAP, and compute base risk."""
    data = copy.deepcopy(data)
    city = data.get("metadata", {}).get("city")
    # Existing ML persistence is city-named. Namespace demo artifacts until the
    # model-registry phase supplies versioned content hashes for every model.
    if data.get("metadata", {}).get("synthetic") is True and city:
        data["metadata"]["city"] = f"{city}-demo"
        data["metadata"]["display_city"] = city
    a = train(data) if retrain else load_or_train(data)
    data, importance = infer(data, a)
    if city:
        data["metadata"]["city"] = city
    for f in data["features"]:
        f["properties"].update(risk(f["properties"]))
    return {"data": data, "model": describe(a), "importance": importance, "artifact": a}


def state(city: str, mode: str | None = None) -> Dict[str, Any]:
    """Return a persisted analysis dataset; normal mode never creates one.

    Synthetic data may only be materialized after an explicit Demo Mode
    selection. Live evidence remains an asset until the Phase 2 processing
    pipeline marks it analysis-ready.
    """
    selected_mode = resolve_mode(mode)
    cache = state_cache(selected_mode)
    with LOCK:
        if city in cache and not analysis_cached(city, selected_mode):
            cache.pop(city)
        if city not in cache and selected_mode == "demo":
            stored = next(
                (d for d in records("demo_dataset", 20) if d.get("metadata", {}).get("city") == city
                 and d.get("metadata", {}).get("synthetic") is True),
                None,
            )
            if stored:
                stored.pop("id", None)
                stored.pop("created_at", None)
            if stored:
                cache[city] = analyze(stored)
            else:
                demo = sample_data(city)
                demo["metadata"]["mode"] = "demo"
                demo["metadata"]["analysis_ready"] = True
                save("demo_dataset", demo, record_id=f"demo-dataset-{city}")
                cache[city] = analyze(demo, retrain=True)
        if city not in cache:
            raise HTTPException(
                409,
                "No validated analytical model is active for this city. Explore acquired evidence in the city workspace; Demo Mode requires explicit selection.",
            )
        return cache[city]


def activate_demo(city: str, boundary=None, rural_reference: float = 33.0) -> Dict[str, Any]:
    """Build the labelled demonstration analysis only after explicit selection."""
    data = sample_data(city, boundary=boundary, rural_reference=rural_reference)
    if not data["features"]:
        raise ValueError("Boundary does not contain demonstration cells around the selected center.")
    data["metadata"].update({"mode": "demo", "analysis_ready": True})
    prepared = analyze(data, retrain=True)
    save("demo_dataset", data, record_id=f"demo-dataset-{city}")
    with LOCK:
        DEMO_STATE[city] = prepared
    return prepared


def retrain_state(city: str, mode: str | None = None) -> Dict[str, Any]:
    selected_mode = resolve_mode(mode)
    with LOCK:
        if selected_mode == "demo":
            data = state(city, selected_mode)["data"]
        else:
            data = next((d for d in records("dataset", 100)
                         if d.get("metadata", {}).get("city") == city and real_dataset_ready(d)), None)
            if data is None:
                raise HTTPException(409, "No measured, provenance-verified training dataset is available for this city.")
            data = {k: v for k, v in data.items() if k not in {"id", "created_at"}}
        result = analyze(data, retrain=True)
        state_cache(selected_mode)[city] = result
        return result


def zone(city: str, zone_id: Optional[str] = None, mode: str | None = None) -> Dict[str, Any]:
    """Retrieve a specific zone property dictionary or highest-risk zone for a city."""
    items = state(city, mode)["data"]["features"]
    if not items:
        raise HTTPException(404, "No analysis zones in this boundary.")
    if zone_id is None:
        return max((f["properties"] for f in items), key=lambda p: p["risk_score"])
    p = next((f["properties"] for f in items if f["properties"]["id"] == zone_id), None)
    if p is None:
        raise HTTPException(404, "Zone not found in this city.")
    return p


def get_city_overview(city: str, mode: str | None = None) -> Dict[str, Any]:
    """Compute high-level aggregate heat and risk metrics across all zones in a city."""
    s = state(city, mode)
    p = [f["properties"] for f in s["data"]["features"]]
    n = len(p)
    return {
        "city": city,
        "zone_count": n,
        "area_km2": sum(z["area_km2"] for z in p),
        "average_suhii": sum(z["predicted_suhii"] for z in p) / n if n else 0.0,
        "average_lst": sum(z["predicted_lst"] for z in p) / n if n else 0.0,
        "hotspots": sum(z["hotspot"] for z in p),
        "high_risk_zones": sum(z["risk_level"] == "High" for z in p),
        "population_exposed": sum(
            z["population"] for z in p if z["risk_level"] == "High"
        ),
        "metadata": s["data"]["metadata"],
        "model": s["model"],
        "importance": s["importance"],
        "priority_zones": sorted(p, key=lambda p: -p["risk_score"])[:8],
    }


def clear_state(city: Optional[str] = None) -> None:
    """Clear cached state for testing or retraining."""
    with LOCK:
        if city:
            DEMO_STATE.pop(city, None)
            REAL_STATE.pop(city, None)
        else:
            DEMO_STATE.clear()
            REAL_STATE.clear()
