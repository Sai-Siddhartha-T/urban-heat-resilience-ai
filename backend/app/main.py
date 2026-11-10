"""FastAPI application root assembly: lifecycle, security, CORS, exception handlers, and routes."""

import asyncio, os, secrets, sys, time, httpx, logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import init_db, engine, POSTGIS, ROOT
from app.migrations import current_revision
from app.schemas import HealthResponse
from app.services.state import STATE, LOCK, state, zone, analyze, analysis_cached, resolve_mode, get_city_overview as overview
from app.schemas.evidence import CityName
from typing import Literal
from app.routes import (
    heat_router, models_router, simulation_router, optimization_router,
    risk_router, data_router, ai_router, reports_router, workspace_router,
)

# Structured logging with timestamps, levels, logger name, and message format
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("heatwise")
RATE = defaultdict(deque)
TILES = {}
tile_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    fast = os.getenv("FAST_STARTUP", "0") == "1" or os.getenv("PREWARM_STATE", "1").lower() in ("0", "false", "no")
    if not fast and os.getenv("HEATWISE_DEMO_MODE") == "1":
        log.info("Pre-warming ML models and state for Ahmedabad...")
        await asyncio.to_thread(state, "Ahmedabad")
    else:
        log.info("Normal mode starts without a synthetic analysis dataset.")
    yield


app = FastAPI(
    title="Heatwise · Urban Heat Intelligence",
    version="0.1.0",
    lifespan=lifespan,
    description="Urban climate evidence, source provenance and separately labelled analytical scenarios.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security(request: Request, call_next):
    # Normalize accidental double-prefix (e.g. frontend apiClient prefixing an already-prefixed path)
    if request.url.path.startswith("/api/api/"):
        request.scope["path"] = request.url.path[4:]

    start_time = time.monotonic()
    client_host = request.client.host if request.client else "local"

    if request.url.path.startswith("/api"):
        token = os.getenv("API_TOKEN", "")
        if token and request.method != "OPTIONS" and not request.url.path.startswith("/api/tiles/") and not secrets.compare_digest(
            request.headers.get("Authorization", ""), f"Bearer {token}"
        ):
            log.warning("Unauthorized access to [%s %s] from %s", request.method, request.url.path, client_host)
            return JSONResponse({"detail": "API token required."}, 401)
        if os.getenv("FAST_STARTUP") == "1" or os.getenv("TESTING") == "1":
            pass
        else:
            now = time.monotonic()
            q = RATE[client_host]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) > 180:
                log.warning("Rate limit reached for %s on [%s %s]", client_host, request.method, request.url.path)
                return JSONResponse({"detail": "Rate limit reached. Retry in one minute."}, 429)
            q.append(now)

    response = await call_next(request)
    duration_ms = (time.monotonic() - start_time) * 1000
    if not request.url.path.startswith("/api/tiles/"):
        log.info("[%s] %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


CREDENTIAL_INDICATORS = (
    "openaq_api_key",
    "earth_engine_project",
    "google application credentials",
    "credentials are required",
    "credentials unconfigured",
    "not configured",
)


def _is_credential_error(msg: str) -> bool:
    msg_lower = msg.lower()
    return any(ind in msg_lower for ind in CREDENTIAL_INDICATORS) and (
        "credential" in msg_lower
        or "api_key" in msg_lower
        or "configured" in msg_lower
        or "project" in msg_lower
    )


def _credential_unavailable_response(exc: Exception, request: Request) -> JSONResponse:
    msg = str(exc)
    msg_lower = msg.lower()
    if "openaq" in msg_lower:
        source = "OpenAQ"
        setup = "Configure the OPENAQ_API_KEY environment variable. Free API keys can be requested at https://openaq.org."
    elif "earth_engine" in msg_lower or "google" in msg_lower:
        source = "Google Earth Engine"
        setup = "Configure EARTH_ENGINE_PROJECT and ensure Google Cloud Application Default Credentials (ADC) are initialized via 'gcloud auth application-default login'."
    else:
        source = "External Provider"
        setup = "Configure required external service credentials in environment variables."

    log.warning(
        "Gracefully degraded unconfigured external service on [%s %s] for %s: %s",
        request.method,
        request.url.path,
        source,
        msg,
    )
    return JSONResponse(
        {
            "status": "unavailable",
            "source": source,
            "detail": msg,
            "reason": f"External service credentials not configured for {source}.",
            "setup_instructions": setup,
        },
        status_code=503,
    )


@app.exception_handler(ValueError)
async def bad_value(request: Request, exc: ValueError):
    if _is_credential_error(str(exc)):
        return _credential_unavailable_response(exc, request)
    log.warning("Validation error on [%s %s]: %s", request.method, request.url.path, exc)
    return JSONResponse({"detail": str(exc)}, 422)


@app.exception_handler(httpx.HTTPError)
async def upstream_error(request: Request, exc: httpx.HTTPError):
    log.warning("Upstream request failed on [%s %s]: %s (%s)", request.method, request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        {
            "status": "unavailable",
            "detail": "External source unavailable. No substitute data was inserted. Retry later.",
            "error_type": type(exc).__name__,
        },
        status_code=502,
    )


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    if _is_credential_error(str(exc)):
        return _credential_unavailable_response(exc, request)
    log.error("Internal error on [%s %s]: %s (%s)", request.method, request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        {"detail": "Operation failed. Check server configuration and logs; existing results were preserved."},
        status_code=500,
    )


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health(city: CityName = "Ahmedabad", mode: Literal["normal", "demo"] | None = None):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    demo_mode = resolve_mode(mode) == "demo"
    return {
        "status": "ok",
        "database": "PostgreSQL/PostGIS" if POSTGIS else "SQLite local fallback",
        "synthetic_predictions": demo_mode,
        "analysis_ready": analysis_cached(city, mode),
        "mode": "demo" if demo_mode else "normal",
        "schema_revision": current_revision(),
        "city": city,
    }


@app.get("/health", response_model=HealthResponse, include_in_schema=False)
def direct_health():
    """Direct alias for /api/health."""
    return health()


@app.get("/cities", include_in_schema=False)
def direct_cities():
    """Direct alias for /api/cities for clients requesting non-prefixed endpoints."""
    from app.routes.heat import cities
    return cities()


@app.get("/overview", include_in_schema=False)
def direct_overview(city: str = "Ahmedabad"):
    """Direct alias for /api/overview for clients requesting non-prefixed endpoints."""
    from app.routes.heat import overview
    return overview(city)  # type: ignore[arg-type]


@app.get("/api/tiles/{z}/{x}/{y}.png", tags=["tiles"])
async def map_tile(z: int, x: int, y: int):
    if not (0 <= z <= 18 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(422, "Invalid tile coordinate.")
    key = (z, x, y)
    async with tile_lock:
        content = TILES.get(key)
    if content is None:
        async with httpx.AsyncClient(timeout=15) as c:
            response = await c.get(
                f"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                headers={"User-Agent": "HeatwiseResearchPrototype/0.1 (local research dashboard)"},
            )
            response.raise_for_status()
            content = response.content
        async with tile_lock:
            if len(TILES) >= 256:
                TILES.pop(next(iter(TILES)))
            TILES[key] = content
    return Response(content, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


for r in (heat_router, models_router, simulation_router, optimization_router, risk_router, data_router, ai_router, reports_router, workspace_router):
    app.include_router(r)

DIST = ROOT.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def frontend():
        return FileResponse(DIST / "index.html")
