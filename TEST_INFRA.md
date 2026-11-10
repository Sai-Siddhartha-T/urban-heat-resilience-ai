# Test Infrastructure Specification: Heatwise Urban Heat Resilience Platform

## 1. Overview & Framework Architecture
The Heatwise testing infrastructure provides deterministic, opaque-box validation across the entire full-stack system without remote external dependencies.

- **Primary Framework**: Pytest 9.2+ with FastAPI `TestClient(app)` / Starlette ASGI transport.
- **Python Runtime**: Python 3.14+ (Windows 64-bit).
- **Execution Invariants**:
  - **100% Offline & Isolated**: All remote APIs (Open-Meteo, Sentinel STAC, NASA POWER, Overpass OSM, OpenAQ, Earth Engine, Groq, Gemini) are mocked or intercepted with synthetic provenance guarantees.
  - **Deterministic Spatial Modeling**: In-memory / temporary SQLite database fixture with spatial GeoJSON polygons.
  - **Fast Startup & Lazy Initialization**: `os.environ["FAST_STARTUP"] = "1"` and `os.environ["PREWARM_STATE"] = "0"` prevent expensive 540-tree training cold starts during client bootstrapping.
  - **Windows IOCP Sandbox Compatibility**: Proactor event loop self-pipe patched with `_overlapped.PostQueuedCompletionStatus` to run reliably inside restricted Windows sandbox without socketpair connect permissions.

---

## 2. Directory Layout & Test Suite Hierarchy
Tests are co-located in `backend/tests/` and mirror backend architecture:

```
backend/
├── app/
│   ├── main.py                     # Application entrypoint & middleware
│   ├── schemas.py                  # Pydantic v2 strict schemas
│   ├── db.py                       # SQLAlchemy models & SQLite/PostGIS abstraction
│   ├── routes/                     # Decomposed APIRouters
│   │   ├── heat.py                 # Spatial heat, overview, cities
│   │   ├── models.py               # ML tournament & TreeSHAP
│   │   ├── simulation.py           # 8 intervention simulation models
│   │   ├── optimization.py         # Google OR-Tools CP-SAT solver
│   │   ├── risk.py                 # Multi-criteria parametric risk
│   │   ├── data.py                 # Ingestion, status, time series
│   │   ├── ai.py                   # Resilience assistant with guardrails
│   │   └── reports.py              # Synthesis export (JSON, CSV, Markdown)
│   └── services/                   # Core scientific & analytical engines
└── tests/
    ├── conftest.py                 # Global test database & temp directory isolation
    ├── test_foundation.py          # Data generation, synthetic geometry, indices
    ├── test_pipeline.py            # ML spatial holdout split, TreeSHAP, optimizer constraints
    ├── test_api.py                 # Basic integration smoke tests
    ├── test_sources.py             # External adapter unit mocks
    ├── test_ai.py                  # AI assistant provider validation
    └── test_e2e_tiers.py           # Comprehensive E2E Test Suite (Tiers 1–4)
```

---

## 3. Systematic Testing Methodology (Tiers 1–4)

### Tier 1 — Feature Coverage (>=5 Tests Per Functional Domain)
Exhaustive verification of all 10 core capability areas:
1. **System Health & Foundation**: `/api/health`, `/api/ready`, `/api/meta`, `/api/cities`, `/api/tiles/*`
2. **Heat Metrics & Baseline Data**: `/api/heat/map`, `/api/heat/hotspots`, `/api/heat/predict`, multi-city overviews
3. **ML Training & Validation**: Spatial holdout evaluation (6 longitudinal blocks), non-leaking predictors, confidence intervals, retraining
4. **TreeSHAP Explainability**: Local exact additivity ($Base + \sum SHAP = \hat{y}$), global ranking, hotspot vs cool-zone attributions
5. **Urban Heat Risk Index**: Hazard, exposure, vulnerability weights, single-zone vs city-wide distribution
6. **Intervention Simulation**: 8 distinct models (trees, vegetation, parks, cool roofs, pavements, corridors, roof gardens, water), physical capacity, convenience conversions
7. **CP-SAT Optimizer**: Discrete multi-zone optimization, water limit constraint, budget enforcement, 50% water sensitivity alternative
8. **AI Resilience Assistant**: Context grounding, fact citation validation, numeric prose guardrails, feasible action filtering
9. **Data Ingestion & Catalogs**: Multi-source catalog status, synthetic sample ingestion, weather series, explicit HTTP 502 upstream errors
10. **Report Synthesis & Export**: Multi-format downloads (JSON, CSV, Markdown) with synthetic provenance disclaimer

### Tier 2 — Boundary Value Analysis & Corner Cases (BVA)
Boundary limits and adversarial inputs:
- Geographic coordinates at exact limits ([-80, 80], [-180, 180]) and just beyond (80.1, -80.1, 180.1, -180.1).
- Incomplete coordinate pairs (latitude without longitude).
- Negative water, negative budgets, and negative coverage percentages.
- Extreme resource limits (water > $10^7$ $\text{m}^3/\text{day}$).
- Over-allocation exceeding physical capacity (roof surfaces $> \text{roof\_pct}$, ground surfaces $> \text{available\_land\_pct}$).
- Duplicate zone IDs in multi-zone requests.
- Zero water budget solving with non-water interventions.
- Malformed GeoJSON polygons, non-polygon geometries, and areas $> 4\text{ deg}^2$.
- Inverted date intervals ($\text{end} < \text{start}$) and date spans $> 366$ days.
- Malformed JSON payloads and invalid enum literals.
- Missing resource identifiers (HTTP 404).
- Security middleware verification (Bearer token authentication and `nosniff`/`strict-origin-when-cross-origin` headers).

### Tier 3 — Cross-Feature Pairwise Workflows
End-to-end integration workflows:
- **Workflow 1**: Ingestion $\rightarrow$ Baseline Heat $\rightarrow$ Single Zone Prediction $\rightarrow$ Local TreeSHAP Explanation $\rightarrow$ Parametric Risk Assessment.
- **Workflow 2**: Prediction $\rightarrow$ 8-Intervention Simulation $\rightarrow$ CP-SAT Multi-Zone Optimization $\rightarrow$ Budget Allocation $\rightarrow$ Multi-Format Report Export (JSON, CSV, Markdown).
- **Workflow 3**: Simulation & Optimization Run $\rightarrow$ AI Resilience Assistant Query $\rightarrow$ Fact Grounding & Numerical Guardrail Assertion.

### Tier 4 — Real-World Municipal Planning Scenarios
Concrete urban climate resilience scenarios:
- **Scenario A (Ahmedabad Extreme Heatwave Crisis)**: 5 priority informal settlement zones at 45°C ambient temperature. Severe water scarcity (200 $\text{m}^3/\text{day}$) and tight budget. Optimizer selects reflective cool roofs as primary intervention and provides a feasible 50% water contingency alternative.
- **Scenario B (Rapid Urbanization Dual-Hazard)**: Developing corridor in Hyderabad with low infiltration and high heat. Combined green corridor and permeable pavement interventions lower SUHII and enhance surface permeability.
- **Scenario C (Industrial Corridor Retrofit)**: Large logistics park in Delhi with high metal roof and road fractions. Deployment of large-scale reflective coatings achieves $\ge 1.0^\circ\text{C}$ cooling with 0 municipal water usage.

---

## 4. Test Execution Instructions

### Running the Full E2E Test Suite
```powershell
pytest backend/tests/test_e2e_tiers.py -v
```

### Running Specific Tiers
```powershell
# Tier 1 only
pytest backend/tests/test_e2e_tiers.py -k "test_tier1" -v

# Tier 2 only
pytest backend/tests/test_e2e_tiers.py -k "test_tier2" -v

# Tier 3 only
pytest backend/tests/test_e2e_tiers.py -k "test_tier3" -v

# Tier 4 only
pytest backend/tests/test_e2e_tiers.py -k "test_tier4" -v
```

### Running All Backend Tests
```powershell
pytest backend/tests -v
```

---

## 5. Performance Benchmarks
- Full E2E Test Suite (78 tests): ~34.4 seconds.
- Single zone inference & TreeSHAP: ~120 ms.
- CP-SAT 5-zone multi-intervention optimization: ~45 ms.
- Tournament training & spatial CV: ~1.08 seconds.
