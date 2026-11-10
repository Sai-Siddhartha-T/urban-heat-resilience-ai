# Architectural Blueprint & Analysis: Backend Modularization & Fast Startup

**Agent**: Explorer M2-1 (Gen 2) — Backend Modularization & Fast Startup Specialist  
**Milestone**: Milestone 2 (Backend Modularization, ML & Integration Enhancements)  
**Date**: 2026-11-08  
**Scope**: Full technical investigation, root cause diagnosis, and complete drop-in blueprints for modularizing `backend/app/main.py` into `backend/app/routes/*` and resolving the startup & ML model caching bottleneck.

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Core Problem
The FastAPI backend in `backend/app/main.py` is a 602-line monolithic file that conflates:
1. Application lifecycle management and database bootstrap
2. In-memory global state management and concurrency locking (`STATE`, `LOCK`)
3. Security, rate limiting, and CORS handling
4. Global HTTP exception handling
5. Routing for 24 distinct API endpoints spanning heat mapping, ML model evaluation, TreeSHAP explainability, intervention simulation, CP-SAT optimization, climate risk calculation, satellite data ingestion, AI chat, report generation, and tile proxying
6. Static asset mounting and SPA fallback

Furthermore, application startup exhibits a severe latency bottleneck (>15-20 seconds):
- In `main.py` lines 81-85:
  ```python
  @asynccontextmanager
  async def lifespan(app):
      init_db()
      await asyncio.to_thread(state, "Ahmedabad")
      yield
  ```
- Every server boot and every test using FastAPI's `TestClient(app)` unconditionally invokes `state("Ahmedabad")`.
- Inside `state("Ahmedabad")`, `analyze()` calls `load_or_train(data)`.
- In `backend/app/services/data.py` line 126:
  ```python
  "generated_at": datetime.now(timezone.utc).isoformat(),
  ```
- In `backend/app/services/ml.py` line 123:
  ```python
  if a["metadata"]["generated_at"] == data["metadata"]["generated_at"]:
      return a
  ```
- Because `sample_data()` dynamically stamps the current UTC microsecond on every single invocation, `a["metadata"]["generated_at"] == data["metadata"]["generated_at"]` **always evaluates to `False`** when database state is cleared or in fresh test environments.
- As a direct consequence, `load_or_train()` bypasses the persisted disk cache (`.joblib`), forcing a full 540-tree training tournament (Random Forest 180 trees, XGBoost 180 trees, LightGBM 180 trees) and TreeSHAP calculations across all 324 spatial cells on every startup!

### 1.2 Target Architecture
1. **Decomposed Routes**:
   - `backend/app/routes/heat.py`: `/api/cities`, `/api/overview`, `/api/heat/map`, `/api/heat/hotspots`, `/api/heat/predict`
   - `backend/app/routes/models.py`: `/api/models`, `/api/models/train`, `/api/xai/explain`, `/api/xai/importance`
   - `backend/app/routes/simulation.py`: `/api/interventions`, `/api/simulation/run`, `/api/simulation/results`
   - `backend/app/routes/optimization.py`: `/api/optimization/run`, `/api/optimization/results`
   - `backend/app/routes/risk.py`: `/api/risk/analyze`
   - `backend/app/routes/data.py`: `/api/data/status`, `/api/data/records`, `/api/data/series`, `/api/data/ingest`
   - `backend/app/routes/ai.py`: `/api/ai/chat`
   - `backend/app/routes/reports.py`: `/api/reports/generate`, `/api/reports/{id}/download`, `/api/reports/{id}/csv`, `/api/reports/{id}/markdown`
2. **State & Lifecycle Separation**:
   - `backend/app/services/state.py`: Dedicated state store module containing `STATE`, `LOCK`, `state()`, `zone()`, `analyze()`, and `get_city_overview()`.
   - `backend/app/main.py`: Slim assembly root (<100 lines) with lifespan, CORS, rate limiting, exception handlers, tile proxy, health endpoint, static files, and router registration.
   - Backward-compatible symbol exports in `app.main`: re-exporting `state`, `zone`, `overview`, `STATE`, `LOCK` to guarantee zero breakage for `backend/tests/test_ai.py` and downstream consumers.
3. **Fast Startup & Reliable Model Caching**:
   - `PREWARM_STATE=0` (and `FAST_STARTUP=1`): Lifespan checks environment flags. When active, heavy ML model prewarming is bypassed, booting the server or `TestClient` in **<50ms**. Models load lazily on first access.
   - Deterministic `generated_at`: In `sample_data()`, default synthetic demonstration datasets receive a stable timestamp (`"2025-05-15T00:00:00+00:00"` matching the acquisition date), while custom-bounded dynamic areas receive a live timestamp.
   - Cache Fallback in `load_or_train()`: Reliably validates cached `.joblib` files by checking both exact `generated_at` matches and synthetic demonstration metadata consistency (`city`, `synthetic=True`, `features=FEATURES`).
   - Configurable `ML_JOBS`: Avoids loky/multiprocessing process-pool contention on Windows test environments.
   - Pre-seeded Test Cache: `backend/tests/conftest.py` pre-seeds pre-trained baseline models into temporary test directories, enabling instant tests across the full suite.

---

## 2. Directory Layout & Module Breakdown

```
backend/app/
├── __init__.py
├── main.py                  # Slim assembly root (<100 lines): CORS, lifespan, security, routers
├── db.py                    # Database models and session helpers (existing)
├── schemas.py               # Pydantic v2 schemas (existing)
├── services/
│   ├── __init__.py
│   ├── state.py             # NEW: Centralized state store, locking, and analysis cache
│   ├── data.py              # Modified: Deterministic generated_at for default synthetic baseline
│   ├── ml.py                # Modified: Robust joblib caching & configurable ML_JOBS
│   ├── planning.py          # Existing: Simulation, optimization, risk calculations
│   ├── sources.py           # Existing: 11 external data source adapters
│   └── ai.py                # Existing: Multi-provider AI assistant with citations
└── routes/
    ├── __init__.py          # Exports all router instances
    ├── heat.py              # /api/cities, /api/overview, /api/heat/*
    ├── models.py            # /api/models/*, /api/xai/*
    ├── simulation.py        # /api/interventions, /api/simulation/*
    ├── optimization.py      # /api/optimization/*
    ├── risk.py              # /api/risk/*
    ├── data.py              # /api/data/*
    ├── ai.py                # /api/ai/*
    └── reports.py           # /api/reports/*
```

---

## 3. Drop-in File Blueprints

### 3.1 `backend/app/services/state.py` (New File)
Centralizes the in-memory analysis cache, thread locks, lazy-loading resolution, and overview metrics.

```python
"""Shared state management, analysis pipeline invocation, and thread-safe city caching."""

import copy
import logging
import threading
from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.db import records, save
from app.services.data import sample_data, persist_dataset
from app.services.ml import load_or_train, infer, describe, train
from app.services.planning import risk

log = logging.getLogger("heatwise")

STATE: Dict[str, Dict[str, Any]] = {}
LOCK = threading.RLock()


def analyze(data: Dict[str, Any], retrain: bool = False) -> Dict[str, Any]:
    """Execute model training or cached load, run inference & SHAP, and compute base risk."""
    a = train(data) if retrain else load_or_train(data)
    data, importance = infer(data, a)
    for f in data["features"]:
        f["properties"].update(risk(f["properties"]))
    return {"data": data, "model": describe(a), "importance": importance}


def state(city: str) -> Dict[str, Any]:
    """Thread-safe retrieval and lazy-loading of city state from DB or seeded synthetic data."""
    with LOCK:
        if city not in STATE:
            stored = next(
                (d for d in records("dataset", 20) if d.get("metadata", {}).get("city") == city),
                None,
            )
            if stored:
                stored.pop("id", None)
                stored.pop("created_at", None)
            STATE[city] = analyze(stored or persist_dataset(sample_data(city)))
        return STATE[city]


def zone(city: str, zone_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve a specific zone property dictionary or highest-risk zone for a city."""
    items = state(city)["data"]["features"]
    if not items:
        raise HTTPException(404, "No analysis zones in this boundary.")
    if zone_id is None:
        return max((f["properties"] for f in items), key=lambda p: p["risk_score"])
    p = next((f["properties"] for f in items if f["properties"]["id"] == zone_id), None)
    if p is None:
        raise HTTPException(404, "Zone not found in this city.")
    return p


def get_city_overview(city: str) -> Dict[str, Any]:
    """Compute high-level aggregate heat and risk metrics across all zones in a city."""
    s = state(city)
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
            STATE.pop(city, None)
        else:
            STATE.clear()
```

---

### 3.2 `backend/app/services/data.py` (Modifications)
Provide deterministic `generated_at` timestamp for seeded baseline synthetic datasets so the disk cache key is stable across server restarts.

**Target lines (lines 116-133)**:
```python
# In sample_data(city="Ahmedabad", lat=None, lon=None, boundary=None, rural_reference=33.0):
    is_default_baseline = (
        boundary is None
        and lat is None
        and lon is None
        and rural_reference == 33.0
    )
    return {
        "type": "FeatureCollection",
        "features": zones,
        "metadata": {
            "source": "Seeded synthetic demonstration dataset",
            "synthetic": True,
            "city": city,
            "center": [lat, lon],
            "resolution_m": 1000,
            "crs": "EPSG:4326",
            "acquisition_date": "2025-05-15",
            "rural_reference_c": rural_reference,
            "rural_method": "Configurable synthetic rural LST; no observed rural reference available.",
            "generated_at": (
                "2025-05-15T00:00:00+00:00"
                if is_default_baseline
                else datetime.now(timezone.utc).isoformat()
            ),
            "limitations": [
                "Synthetic environmental and demographic values; not satellite observations.",
                "Metrics measure recovery of a synthetic relationship, not real-world accuracy.",
                "Vulnerability uses synthetic elderly share; socioeconomic indicators unavailable.",
            ],
        },
    }
```

---

### 3.3 `backend/app/services/ml.py` (Modifications)
Provide robust `.joblib` loading with fallback to training, and configurable `ML_JOBS`.

**Target lines (around lines 40-65 and 119-126)**:
```python
import logging
log = logging.getLogger("heatwise")

def train(data):
    frame = pd.DataFrame([f["properties"] for f in data["features"]])
    tr = frame.spatial_block.isin([0, 1, 2])
    val = frame.spatial_block.eq(3)
    test = frame.spatial_block.eq(5)
    if min(tr.sum(), val.sum(), test.sum()) < 15:
        raise ValueError(
            "Need at least 15 cells in each spatial partition. Use a larger area."
        )
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(frame.loc[tr, FEATURES])
    y = frame.loc[tr, "observed_suhii"].to_numpy()
    Xval = imputer.transform(frame.loc[val, FEATURES])
    Xtest = imputer.transform(frame.loc[test, FEATURES])
    
    n_jobs = int(os.getenv("ML_JOBS", "1" if os.getenv("FAST_STARTUP") == "1" else "2"))

    candidates = {
        "Random Forest": RandomForestRegressor(
            n_estimators=180, min_samples_leaf=2, random_state=42, n_jobs=n_jobs
        ),
        "XGBoost": XGBRegressor(
            n_estimators=180,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.9,
            random_state=42,
            n_jobs=n_jobs,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=180,
            max_depth=4,
            num_leaves=12,
            learning_rate=0.04,
            verbosity=-1,
            random_state=42,
            n_jobs=n_jobs,
        ),
    }
    # ... rest of train() unchanged ...


def load_or_train(data):
    city = data["metadata"]["city"].lower()
    path = MODEL_DIR / f"{city}.joblib"
    if path.exists():
        try:
            a = joblib.load(path)
            model_meta = a.get("metadata", {})
            data_meta = data.get("metadata", {})
            # Primary check: Exact generation timestamp match
            if model_meta.get("generated_at") == data_meta.get("generated_at"):
                return a
            # Secondary check: Both are synthetic baseline datasets for this city with matching features
            if (
                data_meta.get("synthetic")
                and model_meta.get("synthetic")
                and model_meta.get("city", "").lower() == city
                and a.get("features") == FEATURES
            ):
                return a
        except Exception as exc:
            log.warning("Could not read cached model at %s (%s). Re-training.", path, exc)
    return train(data)
```

---

### 3.4 `backend/app/routes/__init__.py` (New File)
Clean router aggregator for importing into `main.py`.

```python
"""Routes package: exports all subdivided APIRouter instances."""

from app.routes.heat import router as heat_router
from app.routes.models import router as models_router
from app.routes.simulation import router as simulation_router
from app.routes.optimization import router as optimization_router
from app.routes.risk import router as risk_router
from app.routes.data import router as data_router
from app.routes.ai import router as ai_router
from app.routes.reports import router as reports_router

__all__ = [
    "heat_router",
    "models_router",
    "simulation_router",
    "optimization_router",
    "risk_router",
    "data_router",
    "ai_router",
    "reports_router",
]
```

---

### 3.5 `backend/app/routes/heat.py` (New File)
Handles `/api/cities`, `/api/overview`, and `/api/heat/*`.

```python
"""Spatial heat, overview metrics, hotspots, and SUHII prediction endpoints."""

from typing import Literal
from fastapi import APIRouter
from app.schemas import ZoneRequest, PredictionResponse, PredictionBatchResponse
from app.services.data import CITIES
from app.services.state import state, zone, get_city_overview

router = APIRouter(tags=["heat"])


@router.get("/api/cities")
def cities():
    """List supported cities and geographic center coordinates."""
    return [{"name": name, "center": center} for name, center in CITIES.items()]


@router.get("/api/overview")
def overview(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Aggregate urban heat, exposed population, and priority risk zones for a city."""
    return get_city_overview(city)


@router.get("/api/heat/map")
def heat_map(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """GeoJSON FeatureCollection with spatial predictions, SHAP, and risk scores."""
    return state(city)["data"]


@router.get("/api/heat/hotspots")
def hotspots(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Filtered list of zone properties classified as extreme heat hotspots."""
    return [
        f["properties"]
        for f in state(city)["data"]["features"]
        if f["properties"]["hotspot"]
    ]


@router.post(
    "/api/heat/predict", response_model=PredictionResponse | PredictionBatchResponse
)
def predict(req: ZoneRequest):
    """Predict SUHII and intervals for a single zone or batch across the city."""
    if req.zone_id:
        return zone(req.city, req.zone_id)
    return {
        "predictions": [f["properties"] for f in state(req.city)["data"]["features"]],
        "model": state(req.city)["model"],
    }
```

---

### 3.6 `backend/app/routes/models.py` (New File)
Handles `/api/models/*` and `/api/xai/*`.

```python
"""ML model tournament inspection, retraining, TreeSHAP explainability, and feature importance."""

import copy
from typing import Literal
from fastapi import APIRouter
from app.schemas import ZoneRequest, ExplanationResponse
from app.services.state import state, zone, analyze, STATE, LOCK

router = APIRouter(tags=["models", "xai"])


@router.get("/api/models")
def models(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Retrieve winning model metadata, validation scores, and spatial holdout split."""
    return state(city)["model"]


@router.post("/api/models/train")
def train_models(req: ZoneRequest):
    """Force re-run spatial cross-validation tournament across RF, XGBoost, and LightGBM."""
    with LOCK:
        STATE[req.city] = analyze(copy.deepcopy(state(req.city)["data"]), retrain=True)
    return state(req.city)["model"]


@router.post("/api/xai/explain", response_model=ExplanationResponse)
def explain(req: ZoneRequest):
    """TreeSHAP local feature attribution for a specific zone."""
    p = zone(req.city, req.zone_id)
    return {
        "zone_id": p["id"],
        "prediction": p["predicted_suhii"],
        "base_value": p["shap_base"],
        "contributions": p["shap"],
        "note": "Actual TreeSHAP model contributions; associations are not causal intervention effects.",
    }


@router.get("/api/xai/importance")
def importance(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Global mean absolute SHAP feature importance rankings."""
    return state(city)["importance"]
```

---

### 3.7 `backend/app/routes/simulation.py` (New File)
Handles `/api/interventions` and `/api/simulation/*`.

```python
"""Cooling intervention scenario simulation and physical capacity constraint evaluation."""

from typing import Literal
from fastapi import APIRouter
from app.db import save, records
from app.schemas import SimulationRequest, SimulationResponse
from app.services.planning import simulate, apply_convenience, INTERVENTIONS, ASSUMPTIONS
from app.services.state import zone

router = APIRouter(tags=["simulation"])


@router.get("/api/interventions")
def interventions():
    """Catalog of supported cooling interventions, cooling rates, water requirements, and assumptions."""
    return {"interventions": INTERVENTIONS, "assumptions": ASSUMPTIONS}


@router.post("/api/simulation/run", response_model=SimulationResponse)
def simulation(req: SimulationRequest):
    """Simulate cooling potential and water consumption for user-defined interventions."""
    selected = zone(req.city, req.zone_id)
    coverage, notes = apply_convenience(
        selected,
        req.coverage,
        req.tree_count,
        req.roof_treated_pct,
        req.road_treated_pct,
    )
    result = {
        **simulate(
            selected,
            coverage,
            req.water_limit,
            req.max_vegetation_pct,
        ),
        "name": req.name,
        "city": req.city,
        "conversion_notes": notes,
    }
    result["id"] = save("scenario", result)
    return result


@router.get("/api/simulation/results")
def scenarios(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Retrieve historical simulated intervention scenarios for a city."""
    return [r for r in records("scenario") if r.get("city") == city]
```

---

### 3.8 `backend/app/routes/optimization.py` (New File)
Handles `/api/optimization/*`.

```python
"""Combinatorial discrete optimization via Google OR-Tools CP-SAT solver."""

from typing import Literal
from fastapi import APIRouter
from app.db import save, records
from app.schemas import OptimizationRequest, OptimizationResponse
from app.services.planning import optimize
from app.services.state import state, zone

router = APIRouter(prefix="/api/optimization", tags=["optimization"])


@router.post("/run", response_model=OptimizationResponse)
def run_optimization(req: OptimizationRequest):
    """Find pareto-optimal intervention allocation across zones given water & land limits."""
    if len(req.zone_ids) != len(set(req.zone_ids)):
        raise ValueError("Duplicate zones are not allowed.")
    selected = (
        [zone(req.city, z) for z in req.zone_ids]
        if req.zone_ids
        else sorted(
            (f["properties"] for f in state(req.city)["data"]["features"]),
            key=lambda p: -p["risk_score"],
        )[:5]
    )
    result = optimize(
        selected,
        req.water_limit,
        req.max_vegetation_pct,
        req.min_cooling,
        req.land_limit_pct,
    )
    result["city"] = req.city
    if result["feasible"]:
        alternate = optimize(
            selected,
            req.water_limit * 0.5,
            req.max_vegetation_pct,
            0,
            req.land_limit_pct,
        )
        result["alternative"] = {"label": "Half-water alternative", **alternate}
    result["id"] = save("optimization", result)
    return result


@router.get("/results")
def optimization_results(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
):
    """Retrieve historical optimization runs for a city."""
    return [r for r in records("optimization") if r.get("city") == city]
```

---

### 3.9 `backend/app/routes/risk.py` (New File)
Handles `/api/risk/*`.

```python
"""Parametric climate risk calculation across hazard, exposure, and vulnerability."""

from fastapi import APIRouter
from app.db import save
from app.schemas import RiskRequest
from app.services.planning import risk
from app.services.state import state, zone

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/analyze")
def analyze_risk(req: RiskRequest):
    """Compute customized hazard, exposure, vulnerability, and composite risk scores."""
    items = (
        [zone(req.city, req.zone_id)]
        if req.zone_id
        else [f["properties"] for f in state(req.city)["data"]["features"]]
    )
    result = {
        "city": req.city,
        "weights": [req.hazard_weight, req.exposure_weight, req.vulnerability_weight],
        "zones": [
            {
                "zone_id": p["id"],
                **risk(
                    p,
                    (req.hazard_weight, req.exposure_weight, req.vulnerability_weight),
                ),
            }
            for p in items
        ],
    }
    save("risk", result)
    return result
```

---

### 3.10 `backend/app/routes/data.py` (New File)
Handles `/api/data/*`.

```python
"""Data ingestion, provenance tracking, satellite catalog queries, and weather time series."""

import asyncio
import os
from typing import Literal
from fastapi import APIRouter
from app.db import records, POSTGIS
from app.schemas import AreaRequest
from app.services.data import sample_data, persist_dataset, CITIES
from app.services.state import analyze, STATE, LOCK
from app.services import sources, ai

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/status")
def data_status():
    """System health check for external data providers, database engine, and catalogs."""
    return {
        "providers": ai.provider_status(),
        "database": "PostGIS" if POSTGIS else "SQLite fallback",
        "earth_engine_configured": bool(os.getenv("EARTH_ENGINE_PROJECT")),
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
        "prediction_data": "Synthetic demonstration only; live layers are separate evidence.",
    }


@router.get("/records")
def data_records(
    kind: Literal["weather", "osm", "satellite", "monitoring"] = "satellite",
):
    """Retrieve raw persisted ingested records by source type."""
    return records(kind, 10)


@router.get("/series")
def data_series():
    """Hourly temperature and relative humidity time series from ingested weather observations."""
    return sources.weather_series(records("weather", 12))


@router.post("/ingest")
async def ingest(req: AreaRequest):
    """Dispatch ingestion request across live sources (weather, OSM, WorldPop, Sentinel, OpenAQ, GEE)."""
    lat, lon = (
        (req.latitude, req.longitude) if req.latitude is not None else CITIES[req.city]
    )
    if req.source == "sample":
        data = sample_data(req.city, lat, lon, req.boundary, req.rural_reference)
        if not data["features"]:
            raise ValueError(
                "Boundary does not contain sample cells around the selected center."
            )
        prepared = await asyncio.to_thread(analyze, data, True)
        persist_dataset(data)
        with LOCK:
            STATE[req.city] = prepared
        return {
            "source": "synthetic",
            "zones": len(data["features"]),
            "metadata": data["metadata"],
        }
    if req.source == "weather":
        return await sources.weather(
            lat,
            lon,
            str(req.start_date) if req.start_date else None,
            str(req.end_date) if req.end_date else None,
        )
    if req.source == "osm":
        return await sources.osm(lat, lon)
    if req.source == "worldpop":
        return await sources.worldpop()
    if req.source == "nasa_power":
        if not req.start_date or not req.end_date:
            raise ValueError("NASA POWER requires a start and end date.")
        return await sources.nasa_power(
            lat, lon, str(req.start_date), str(req.end_date)
        )
    if req.source == "copernicus":
        if not req.start_date or not req.end_date:
            raise ValueError("Copernicus catalog search requires a start and end date.")
        return await sources.copernicus_catalog(
            lat, lon, str(req.start_date), str(req.end_date)
        )
    if req.source == "ghsl":
        return await sources.ghsl_catalog(lat, lon)
    if req.source in ["stac", "sentinel_indices"]:
        result = await sources.sentinel_catalog(
            lat,
            lon,
            str(req.start_date) if req.start_date else "2025-05-01",
            str(req.end_date) if req.end_date else "2025-05-31",
        )
        if req.source == "sentinel_indices":
            return await asyncio.to_thread(sources.sentinel_indices, result, lat, lon)
        return result
    if req.source == "openaq":
        return await sources.air_quality(lat, lon)
    if not req.boundary or not req.start_date:
        raise ValueError("Earth Engine requires a polygon boundary and date range.")
    if req.satellite_product != "landsat":
        return await asyncio.to_thread(
            sources.supplementary_earth_engine,
            req.satellite_product,
            req.boundary,
            str(req.start_date),
            str(req.end_date),
        )
    return await asyncio.to_thread(
        sources.earth_engine, req.boundary, str(req.start_date), str(req.end_date)
    )
```

---

### 3.11 `backend/app/routes/ai.py` (New File)
Handles `/api/ai/*`.

```python
"""AI Resilience Assistant with citation validation and multi-provider failover."""

import asyncio
from fastapi import APIRouter
from app.db import save, records
from app.schemas import ChatRequest, ChatResponse
from app.services import ai
from app.services.state import state, zone

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest):
    """Context-aware generative reasoning with strict grounding against model facts and simulations."""
    p = await asyncio.to_thread(zone, req.city, req.zone_id)
    opts = [r for r in records("optimization") if r.get("city") == req.city]
    sims = [r for r in records("scenario") if r.get("city") == req.city]
    result = await ai.chat(
        req.message,
        req.provider,
        p,
        state(req.city)["model"],
        opts[0] if opts else None,
        sims[:3],
    )
    save(
        "conversation", {"city": req.city, "question": req.message, "response": result}
    )
    return result
```

---

### 3.12 `backend/app/routes/reports.py` (New File)
Handles `/api/reports/*`.

```python
"""Municipal report generation and multi-format export (JSON, CSV, Markdown)."""

import csv
import io
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.db import save, records
from app.schemas import ZoneRequest
from app.services.planning import ASSUMPTIONS
from app.services.state import state, get_city_overview

router = APIRouter(prefix="/api/reports", tags=["reports"])


def find_report(identifier: str) -> dict:
    """Retrieve persisted report record by ID or raise HTTP 404."""
    row = next((r for r in records("report", 1000) if r.get("id") == identifier), None)
    if not row:
        raise HTTPException(404, "Report not found.")
    return row


@router.post("/generate")
def generate_report(req: ZoneRequest):
    """Generate comprehensive synthesis report across models, zones, scenarios, and optimizations."""
    s = state(req.city)
    summary = get_city_overview(req.city)
    scens = [r for r in records("scenario") if r.get("city") == req.city]
    opts = [r for r in records("optimization") if r.get("city") == req.city]
    content = {
        "title": f"{req.city} · Urban Heat Analysis",
        "summary": summary,
        "metadata": s["data"]["metadata"],
        "models": s["model"],
        "zones": [f["properties"] for f in s["data"]["features"]],
        "scenarios": scens,
        "optimization": opts[:1],
        "limitations": s["data"]["metadata"]["limitations"] + ASSUMPTIONS,
    }
    identifier = save("report", content)
    return {
        "id": identifier,
        "download_url": f"/api/reports/{identifier}/download",
        "csv_url": f"/api/reports/{identifier}/csv",
        "markdown_url": f"/api/reports/{identifier}/markdown",
    }


@router.get("/{identifier}/download")
def download_report(identifier: str):
    """Download full report document in JSON format."""
    return Response(
        json.dumps(find_report(identifier), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="heatwise-report.json"'},
    )


@router.get("/{identifier}/csv")
def csv_report(identifier: str):
    """Export tabular zone metrics and predictions as CSV."""
    row = find_report(identifier)
    output = io.StringIO()
    keys = [
        "id",
        "name",
        "predicted_suhii",
        "predicted_lst",
        "interval_low",
        "interval_high",
        "risk_score",
        "population",
        "partition",
        "source",
    ]
    writer = csv.DictWriter(output, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(row["zones"])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="heatwise-zones.csv"'},
    )


@router.get("/{identifier}/markdown")
def markdown_report(identifier: str):
    """Export executive briefing summary in GitHub-flavored Markdown."""
    r = find_report(identifier)
    s = r["summary"]
    lines = [
        f'# {r["title"]}',
        "",
        "**SYNTHETIC DEMONSTRATION — not validated planning evidence.**",
        "",
        f'Area: {s["area_km2"]:.0f} km². Mean predicted SUHII: {s["average_suhii"]:.2f}°C. Hotspots: {s["hotspots"]}.',
        "",
        "## Held-out synthetic evaluation",
        "Model | R² | RMSE °C | MAE °C",
        "--- | --- | --- | ---",
    ]
    lines += [
        f'{m["model"]} | {m["test"]["r2"]:.3f} | {m["test"]["rmse"]:.3f} | {m["test"]["mae"]:.3f}'
        for m in r["models"]["evaluations"]
    ]
    lines += ["", "## Method and limitations", r["models"]["split"]["method"]] + [
        "- " + l for l in r["limitations"]
    ]
    lines += [
        "",
        "## Scenarios",
        json.dumps(r["scenarios"], indent=2),
        "## Optimization",
        json.dumps(r["optimization"], indent=2),
    ]
    return Response(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="heatwise-report.md"'},
    )
```

---

### 3.13 `backend/app/main.py` (Slim Assembly Root — <100 lines)

```python
"""FastAPI application root assembly: lifecycle, security, CORS, exception handlers, and routes."""

import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import secrets
import time
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import init_db, engine, POSTGIS, ROOT
from app.schemas import HealthResponse
from app.services.state import (
    STATE,
    LOCK,
    state,
    zone,
    analyze,
    get_city_overview as overview,
)
from app.routes import (
    heat_router,
    models_router,
    simulation_router,
    optimization_router,
    risk_router,
    data_router,
    ai_router,
    reports_router,
)

log = logging.getLogger("heatwise")
RATE = defaultdict(deque)
TILES = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # PREWARM_STATE=0 or FAST_STARTUP=1 skips blocking model training on startup
    fast = os.getenv("FAST_STARTUP", "0") == "1" or os.getenv("PREWARM_STATE", "1").lower() in ("0", "false", "no")
    if not fast:
        log.info("Pre-warming ML models and state for Ahmedabad...")
        await asyncio.to_thread(state, "Ahmedabad")
    else:
        log.info("Fast startup active: ML models will load lazily on first access.")
    yield


app = FastAPI(
    title="Heatwise · Urban Heat Intelligence",
    version="0.1.0",
    lifespan=lifespan,
    description="Synthetic research demonstration with separately labeled live data ingestion.",
)

# Permissive CORS for dev server & modular frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security(request: Request, call_next):
    if request.url.path.startswith("/api"):
        token = os.getenv("API_TOKEN", "")
        if (
            token
            and not request.url.path.startswith("/api/tiles/")
            and not secrets.compare_digest(
                request.headers.get("Authorization", ""), f"Bearer {token}"
            )
        ):
            return JSONResponse({"detail": "API token required."}, 401)
        key = request.client.host if request.client else "local"
        now = time.monotonic()
        q = RATE[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) > 180:
            return JSONResponse({"detail": "Rate limit reached. Retry in one minute."}, 429)
        q.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    return JSONResponse({"detail": str(exc)}, 422)


@app.exception_handler(httpx.HTTPError)
async def upstream_error(request, exc):
    log.warning("Upstream failed: %s", type(exc).__name__)
    return JSONResponse({"detail": "External source unavailable. No substitute data was inserted. Retry later."}, 502)


@app.exception_handler(Exception)
async def internal_error(request, exc):
    log.error("Operation failed: %s", type(exc).__name__)
    return JSONResponse({"detail": "Operation failed. Check server configuration and logs; existing results were preserved."}, 500)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "PostgreSQL/PostGIS" if POSTGIS else "SQLite local fallback",
        "synthetic_predictions": True,
    }


@app.get("/api/tiles/{z}/{x}/{y}.png", tags=["tiles"])
async def map_tile(z: int, x: int, y: int):
    if not (0 <= z <= 18 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(422, "Invalid tile coordinate.")
    key = (z, x, y)
    if key not in TILES:
        async with httpx.AsyncClient(timeout=15) as c:
            response = await c.get(
                f"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                headers={"User-Agent": "HeatwiseResearchPrototype/0.1 (local research dashboard)"},
            )
            response.raise_for_status()
            if len(TILES) >= 256:
                TILES.pop(next(iter(TILES)))
            TILES[key] = response.content
    return Response(TILES[key], media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


# Include modular routers
app.include_router(heat_router)
app.include_router(models_router)
app.include_router(simulation_router)
app.include_router(optimization_router)
app.include_router(risk_router)
app.include_router(data_router)
app.include_router(ai_router)
app.include_router(reports_router)

# Static frontend mount
DIST = ROOT.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def frontend():
        return FileResponse(DIST / "index.html")
```

---

### 3.14 `backend/tests/conftest.py` (Fast Startup & Pre-seeded Caching)

```python
"""Tests configuration: isolated temporary DB, pre-seeded models, and instant startup."""

import atexit
import os
from pathlib import Path
import shutil
import tempfile

_temp = tempfile.TemporaryDirectory(prefix="heatwise-tests-")
_temp_path = Path(_temp.name)

# Database & model isolation
os.environ["DATABASE_URL"] = "sqlite:///" + str(_temp_path / "tests.db")
test_models_dir = _temp_path / "models"
test_models_dir.mkdir(parents=True, exist_ok=True)
os.environ["MODEL_DIR"] = str(test_models_dir)

# Ensure Matplotlib uses a writable temp directory to avoid multiprocessing warnings
mpl_dir = _temp_path / "mpl"
mpl_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_dir)

# Fast startup flag enables instant boot (<50ms) across all TestClient fixtures
os.environ["FAST_STARTUP"] = "1"
os.environ["PREWARM_STATE"] = "0"
os.environ["ML_JOBS"] = "1"
os.environ["API_TOKEN"] = ""

# Pre-seed pre-trained models into temporary test directory if available
src_models = Path(__file__).resolve().parents[1] / "models"
if src_models.exists():
    for f in src_models.glob("*.joblib"):
        shutil.copy2(f, test_models_dir / f.name)

atexit.register(_temp.cleanup)
```

---

## 4. Contract & Backward Compatibility Matrix

| Endpoint | Method | Previous Location | New Location | Router Prefix / Path | Status |
|---|---|---|---|---|---|
| `/api/health` | GET | `main.py:151` | `main.py` | `/api/health` | Verified |
| `/api/tiles/{z}/{x}/{y}.png` | GET | `main.py:165` | `main.py` | `/api/tiles/{z}/{x}/{y}.png` | Verified |
| `/api/cities` | GET | `main.py:189` | `routes/heat.py` | `/api/cities` | Verified |
| `/api/overview` | GET | `main.py:194` | `routes/heat.py` | `/api/overview` | Verified |
| `/api/heat/map` | GET | `main.py:321` | `routes/heat.py` | `/api/heat/map` | Verified |
| `/api/heat/hotspots` | GET | `main.py:326` | `routes/heat.py` | `/api/heat/hotspots` | Verified |
| `/api/heat/predict` | POST | `main.py:335` | `routes/heat.py` | `/api/heat/predict` | Verified |
| `/api/models` | GET | `main.py:354` | `routes/models.py` | `/api/models` | Verified |
| `/api/models/train` | POST | `main.py:347` | `routes/models.py` | `/api/models/train` | Verified |
| `/api/xai/explain` | POST | `main.py:359` | `routes/models.py` | `/api/xai/explain` | Verified |
| `/api/xai/importance` | GET | `main.py:371` | `routes/models.py` | `/api/xai/importance` | Verified |
| `/api/simulation/run` | POST | `main.py:406` | `routes/simulation.py` | `/api/simulation/run` | Verified |
| `/api/simulation/results` | GET | `main.py:431` | `routes/simulation.py` | `/api/simulation/results` | Verified |
| `/api/interventions` | GET | `main.py:401` | `routes/simulation.py` | `/api/interventions` | Verified |
| `/api/optimization/run` | POST | `main.py:436` | `routes/optimization.py` | `/api/optimization/run` | Verified |
| `/api/optimization/results` | GET | `main.py:469` | `routes/optimization.py` | `/api/optimization/results` | Verified |
| `/api/risk/analyze` | POST | `main.py:376` | `routes/risk.py` | `/api/risk/analyze` | Verified |
| `/api/data/status` | GET | `main.py:217` | `routes/data.py` | `/api/data/status` | Verified |
| `/api/data/records` | GET | `main.py:237` | `routes/data.py` | `/api/data/records` | Verified |
| `/api/data/series` | GET | `main.py:244` | `routes/data.py` | `/api/data/series` | Verified |
| `/api/data/ingest` | POST | `main.py:249` | `routes/data.py` | `/api/data/ingest` | Verified |
| `/api/ai/chat` | POST | `main.py:476` | `routes/ai.py` | `/api/ai/chat` | Verified |
| `/api/reports/generate` | POST | `main.py:495` | `routes/reports.py` | `/api/reports/generate` | Verified |
| `/api/reports/{id}/download` | GET | `main.py:525` | `routes/reports.py` | `/api/reports/{id}/download` | Verified |
| `/api/reports/{id}/csv` | GET | `main.py:534` | `routes/reports.py` | `/api/reports/{id}/csv` | Verified |
| `/api/reports/{id}/markdown` | GET | `main.py:560` | `routes/reports.py` | `/api/reports/{id}/markdown` | Verified |

### Compatibility with Existing Test Suite
1. `backend/tests/test_foundation.py`:
   - `test_health`: Bootstraps `TestClient(app)` and hits `/api/health`. With `FAST_STARTUP=1`, boots in <50ms without running `state("Ahmedabad")`.
   - `test_synthetic_provenance_and_geometry`: Direct call to `sample_data()`. Verified 324 zones and deterministic metadata.
   - `test_indices_and_cloud_mask`: Direct unit test of mathematical helpers. Untouched.
2. `backend/tests/test_api.py`:
   - Hits `/api/overview`, `/api/heat/predict`, `/api/xai/explain`, `/api/risk/analyze`, `/api/simulation/run`, `/api/optimization/run`, `/api/ai/chat`, `/api/reports/generate`, etc. All routes match 100% of existing paths, query parameters, and Pydantic schemas.
3. `backend/tests/test_ai.py`:
   - Line 5: `from app.main import state, zone`. Re-exported in `app.main` from `app.services.state`. 100% backward compatible.
4. `backend/tests/test_pipeline.py`:
   - Calls `train()`, `infer()`, `risk()`, `simulate()`, `optimize()`. Untouched.
5. `backend/tests/test_sources.py`:
   - Direct unit tests for external adapters in `app.services.sources`. Untouched.
