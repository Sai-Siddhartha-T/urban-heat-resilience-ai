import asyncio, copy, csv, io, json, logging, os, secrets, threading, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.db import init_db, save, records, engine, POSTGIS, ROOT
from app.schemas import (
    AreaRequest,
    ZoneRequest,
    RiskRequest,
    SimulationRequest,
    OptimizationRequest,
    ChatRequest,
)
from app.schemas import (
    HealthResponse,
    PredictionResponse,
    PredictionBatchResponse,
    ExplanationResponse,
    SimulationResponse,
    OptimizationResponse,
    ChatResponse,
)
from app.services.data import sample_data, persist_dataset, CITIES
from app.services.ml import load_or_train, infer, describe, train
from app.services.planning import risk, simulate, optimize, INTERVENTIONS, ASSUMPTIONS
from app.services import sources, ai

log = logging.getLogger("heatwise")
STATE = {}
LOCK = threading.RLock()
RATE = defaultdict(deque)


def analyze(data, retrain=False):
    a = train(data) if retrain else load_or_train(data)
    data, importance = infer(data, a)
    for f in data["features"]:
        f["properties"].update(risk(f["properties"]))
    return {"data": data, "model": describe(a), "importance": importance}


def state(city):
    with LOCK:
        if city not in STATE:
            stored = next(
                (d for d in records("dataset", 20) if d["metadata"]["city"] == city),
                None,
            )
            if stored:
                stored.pop("id", None)
                stored.pop("created_at", None)
            STATE[city] = analyze(stored or persist_dataset(sample_data(city)))
        return STATE[city]


def zone(city, zone_id=None):
    items = state(city)["data"]["features"]
    if not items:
        raise HTTPException(404, "No analysis zones in this boundary.")
    if zone_id is None:
        return max((f["properties"] for f in items), key=lambda p: p["risk_score"])
    p = next((f["properties"] for f in items if f["properties"]["id"] == zone_id), None)
    if p is None:
        raise HTTPException(404, "Zone not found in this city.")
    return p


@asynccontextmanager
async def lifespan(app):
    init_db()
    await asyncio.to_thread(state, "Ahmedabad")
    yield


app = FastAPI(
    title="Heatwise · Urban Heat Intelligence",
    version="0.1.0",
    lifespan=lifespan,
    description="Synthetic research demonstration with separately labeled live data ingestion. Surface heat is not air temperature.",
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
            return JSONResponse(
                {"detail": "Rate limit reached. Retry in one minute."}, 429
            )
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
    return JSONResponse(
        {
            "detail": "External source unavailable. No substitute data was inserted. Retry later."
        },
        502,
    )


@app.exception_handler(Exception)
async def internal_error(request, exc):
    log.error("Operation failed: %s", type(exc).__name__)
    return JSONResponse(
        {
            "detail": "Operation failed. Check server configuration and logs; existing results were preserved."
        },
        500,
    )


@app.get("/api/health", response_model=HealthResponse)
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "PostgreSQL/PostGIS" if POSTGIS else "SQLite local fallback",
        "synthetic_predictions": True,
    }


TILES = {}


@app.get("/api/tiles/{z}/{x}/{y}.png")
async def map_tile(z: int, x: int, y: int):
    if not (0 <= z <= 18 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(422, "Invalid tile coordinate.")
    key = (z, x, y)
    if key not in TILES:
        async with httpx.AsyncClient(timeout=15) as c:
            response = await c.get(
                f"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                headers={
                    "User-Agent": "HeatwiseResearchPrototype/0.1 (local research dashboard)"
                },
            )
            response.raise_for_status()
            if len(TILES) >= 256:
                TILES.pop(next(iter(TILES)))
            TILES[key] = response.content
    return Response(
        TILES[key],
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/cities")
def cities():
    return [{"name": name, "center": center} for name, center in CITIES.items()]


@app.get("/api/overview")
def overview(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    s = state(city)
    p = [f["properties"] for f in s["data"]["features"]]
    n = len(p)
    return {
        "city": city,
        "zone_count": n,
        "area_km2": sum(z["area_km2"] for z in p),
        "average_suhii": sum(z["predicted_suhii"] for z in p) / n,
        "average_lst": sum(z["predicted_lst"] for z in p) / n,
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


@app.get("/api/data/status")
def data_status():
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
            for kind in ["weather", "osm", "satellite"]
            for r in records(kind, 8)
        ],
        "prediction_data": "Synthetic demonstration only; live layers are separate evidence.",
    }


@app.get("/api/data/records")
def data_records(kind: Literal["weather", "osm", "satellite"] = "satellite"):
    return records(kind, 10)


@app.post("/api/data/ingest")
async def ingest(req: AreaRequest):
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


@app.get("/api/heat/map")
def heat_map(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    return state(city)["data"]


@app.get("/api/heat/hotspots")
def hotspots(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    return [
        f["properties"]
        for f in state(city)["data"]["features"]
        if f["properties"]["hotspot"]
    ]


@app.post(
    "/api/heat/predict", response_model=PredictionResponse | PredictionBatchResponse
)
def predict(req: ZoneRequest):
    if req.zone_id:
        return zone(req.city, req.zone_id)
    return {
        "predictions": [f["properties"] for f in state(req.city)["data"]["features"]],
        "model": state(req.city)["model"],
    }


@app.post("/api/models/train")
def train_models(req: ZoneRequest):
    with LOCK:
        STATE[req.city] = analyze(copy.deepcopy(state(req.city)["data"]), True)
    return state(req.city)["model"]


@app.get("/api/models")
def models(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    return state(city)["model"]


@app.post("/api/xai/explain", response_model=ExplanationResponse)
def explain(req: ZoneRequest):
    p = zone(req.city, req.zone_id)
    return {
        "zone_id": p["id"],
        "prediction": p["predicted_suhii"],
        "base_value": p["shap_base"],
        "contributions": p["shap"],
        "note": "Actual TreeSHAP model contributions; associations are not causal intervention effects.",
    }


@app.get("/api/xai/importance")
def importance(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    return state(city)["importance"]


@app.post("/api/risk/analyze")
def analyze_risk(req: RiskRequest):
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


@app.get("/api/interventions")
def interventions():
    return {"interventions": INTERVENTIONS, "assumptions": ASSUMPTIONS}


@app.post("/api/simulation/run", response_model=SimulationResponse)
def simulation(req: SimulationRequest):
    result = {
        **simulate(
            zone(req.city, req.zone_id),
            req.coverage,
            req.water_limit,
            req.max_vegetation_pct,
        ),
        "name": req.name,
        "city": req.city,
    }
    result["id"] = save("scenario", result)
    return result


@app.get("/api/simulation/results")
def scenarios(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    return [r for r in records("scenario") if r["city"] == city]


@app.post("/api/optimization/run", response_model=OptimizationResponse)
def optimization(req: OptimizationRequest):
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


@app.get("/api/optimization/results")
def optimization_results(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
):
    return [r for r in records("optimization") if r["city"] == city]


@app.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest):
    p = await asyncio.to_thread(zone, req.city, req.zone_id)
    opts = optimization_results(req.city)
    sims = scenarios(req.city)
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


@app.post("/api/reports/generate")
def report(req: ZoneRequest):
    s = state(req.city)
    summary = overview(req.city)
    content = {
        "title": f"{req.city} · Urban Heat Analysis",
        "summary": summary,
        "metadata": s["data"]["metadata"],
        "models": s["model"],
        "zones": [f["properties"] for f in s["data"]["features"]],
        "scenarios": scenarios(req.city),
        "optimization": optimization_results(req.city)[:1],
        "limitations": s["data"]["metadata"]["limitations"] + ASSUMPTIONS,
    }
    identifier = save("report", content)
    return {
        "id": identifier,
        "download_url": f"/api/reports/{identifier}/download",
        "csv_url": f"/api/reports/{identifier}/csv",
        "markdown_url": f"/api/reports/{identifier}/markdown",
    }


def find_report(identifier):
    row = next((r for r in records("report", 1000) if r["id"] == identifier), None)
    if not row:
        raise HTTPException(404, "Report not found.")
    return row


@app.get("/api/reports/{identifier}/download")
def download_report(identifier: str):
    return Response(
        json.dumps(find_report(identifier), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="heatwise-report.json"'},
    )


@app.get("/api/reports/{identifier}/csv")
def csv_report(identifier: str):
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


@app.get("/api/reports/{identifier}/markdown")
def markdown_report(identifier: str):
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


DIST = ROOT.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def frontend():
        return FileResponse(DIST / "index.html")
