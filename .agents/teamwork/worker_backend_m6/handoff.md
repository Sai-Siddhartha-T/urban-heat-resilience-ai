# Handoff Report — Milestone 6: Backend Architecture, API Consistency, and Database Reliability

## 1. Observation
- **Router Prefix Inconsistency**:
  - `backend/app/routes/heat.py`, `backend/app/routes/models.py`, and `backend/app/routes/simulation.py` were instantiated with `APIRouter(tags=[...])` and had `/api/...` hardcoded on every endpoint decorator (e.g. `@router.get("/api/cities")`, `@router.get("/api/models")`, `@router.get("/api/interventions")`).
  - Meanwhile, 5 routers (`optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`) declared explicit prefixes such as `APIRouter(prefix="/api/optimization")` with route-relative decorators (e.g. `@router.post("/run")`).
  - Frontend `apiClient.ts` executes `fetch("/api" + path)`. Direct calls to paths like `/cities` would fail if only `/api/cities` were mounted without non-prefixed aliases, and an accidental prefix like `/api/cities` would generate `/api/api/cities`.
- **Missing Risk Service**:
  - The risk calculation was residing inside `backend/app/services/planning.py` rather than a dedicated module.
  - Consumers such as `backend/app/routes/risk.py` and `backend/app/services/state.py` imported `risk` from `app.services.planning`.
  - No `backend/app/services/risk.py` module existed prior to this milestone.
- **Database Connection & PostGIS Initialization**:
  - `backend/app/db.py` used `URL = os.getenv("DATABASE_URL") or f"sqlite:///{ROOT}/data/heatwise.db"`.
  - Heroku/Render/AWS PostgreSQL connection URLs frequently provide `postgres://` which modern SQLAlchemy rejects (requiring `postgresql://`).
  - `init_db()` unconditionally executed `CREATE EXTENSION IF NOT EXISTS postgis` without catching permission exceptions on cloud-managed Postgres databases lacking superuser privileges.
  - SQLite lacked an explicit `timeout: 30` parameter in `connect_args`, creating vulnerability to `database is locked` under concurrent testing.
- **Test Baseline**:
  - Prior test run passed 177 tests. Full test suite execution required verification with 0 regressions.

## 2. Logic Chain
- **Harmonizing Router Declarations**:
  - In `heat.py`, `models.py`, and `simulation.py`, changed the router definitions to use `APIRouter(prefix="/api", tags=[...])` and removed `/api` from individual route decorators (`@router.get("/cities")`, `@router.get("/models")`, `@router.get("/interventions")`, etc.).
  - Because `prefix="/api"` is declared on the routers, the runtime URLs are identical (`/api/cities`, `/api/models`, `/api/interventions`, etc.), ensuring complete backward compatibility with frontend contracts and existing tests.
  - Added direct aliases in `backend/app/main.py` for `/cities`, `/overview`, and `/health`, allowing direct client requests without `/api` to succeed.
  - Added transparent normalization in `security` middleware in `main.py` for any accidental double-prefix (`/api/api/*` rewritten to `/api/*`), making the API completely resilient against double prefixing.
- **Extracting Risk Service**:
  - Created `backend/app/services/risk.py` containing the IPCC AR5/AR6 Hazard × Exposure × Vulnerability implementation:
    - Hazard: Surface Urban Heat Island Intensity (SUHII) / 8.0 °C clipped to `[0, 1]`.
    - Exposure: Population density / 25,000 people/km² clipped to `[0, 1]`.
    - Vulnerability: Elderly share (age 65+) / 0.25 clipped to `[0, 1]`.
    - Risk score: `100 * (hazard ** w_h) * (exposure ** w_e) * (vulnerability ** w_v)`.
    - Classification: High (>= 20.0), Moderate (>= 8.0), Low (< 8.0).
    - Metadata: `missing_indicators` list and explicit `method` description.
  - In `backend/app/services/planning.py`, imported and re-exported `risk`: `from app.services.risk import risk`, ensuring full backward compatibility for any consumers importing from `planning`.
  - Updated imports in `backend/app/routes/risk.py` and `backend/app/services/state.py` to import from `app.services.risk`.
- **Database & Environment Reliability**:
  - In `backend/app/db.py`, added automatic replacement of legacy `postgres://` with `postgresql://`.
  - Added `timeout: 30` to SQLite `connect_args` alongside `check_same_thread: False`.
  - Wrapped `CREATE EXTENSION IF NOT EXISTS postgis` in a `try...except` block in `init_db()` to log a warning rather than crash when run under non-superuser database roles.
  - Verified that optional environment variables (`EARTH_ENGINE_PROJECT`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAQ_API_KEY`) do not execute network calls on module import and fail gracefully at query time with clean errors or fallbacks.
- **Test Implementation & Validation**:
  - Created `backend/tests/test_backend_m6_architecture.py` containing 15 comprehensive unit and integration tests covering:
    - Risk calculation, threshold classification, bound clipping, weight sensitivity, and backward-compatible re-export from `planning`.
    - API route prefixing, direct request handling (`/cities`, `/overview`, `/health`), and `/api/api` normalization.
    - End-to-end execution of `/api/risk/analyze`.
    - Database CRUD and connection string normalization.

## 3. Caveats
- Production deployment on PostgreSQL with PostGIS still requires the PostGIS spatial extension to be installed on the host database system; when run against SQLite, spatial boundary storage continues to fall back seamlessly to GeoJSON text representation as designed in `Zone.boundary`.
- The `/api/api/*` ASGI path normalization operates strictly in memory on `request.scope["path"]` without issuing an external HTTP 301/307 redirect, preserving request method and body payloads.

## 4. Conclusion
All objectives of Milestone 6 have been fully achieved:
1. API router prefix declarations are harmonized across all 8 router files without altering runtime URLs or breaking frontend expectations.
2. Direct endpoints (`/cities`, `/overview`, `/health`) and double-prefixed paths (`/api/api/*`) operate reliably.
3. `backend/app/services/risk.py` is modularized with the full IPCC framework and re-exported in `planning.py` for 100% backward compatibility.
4. `backend/app/db.py` is hardened for both SQLite and PostgreSQL/PostGIS.
5. All 215 backend tests passed with 0 failures and 0 regressions.

## 5. Verification Method
Run the complete backend test suite:
```powershell
python -m pytest -q
```
**Exact Test Execution Result**:
```
........................................................................ [ 33%]
........................................................................ [ 66%]
.......................................................................  [100%]
============================== warnings summary ===============================
...
215 passed, 15 warnings in 65.17s (0:01:05)
```

Run only the new Milestone 6 architecture tests:
```powershell
python -m pytest backend/tests/test_backend_m6_architecture.py
```
**Result**: `15 passed in 24.70s`
