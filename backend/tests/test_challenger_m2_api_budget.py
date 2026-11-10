"""Empirical Adversarial Stress-Test Suite for Milestone 2 Backend API, Concurrency, and CP-SAT Budget Optimizer.

Covers:
1. CP-SAT budget optimizer edge cases and invariants ($0, tight, massive, negative, schema validation).
2. Thread-safety and concurrent state access on backend/app/services/state.py.
3. Edge case and error-handling probing across all 8 APIRouters.
"""

import concurrent.futures
import threading
import pytest
from fastapi.testclient import TestClient
from app.db import init_db
from app.main import app
from app.services.state import state, zone, analyze, get_city_overview, clear_state, STATE, LOCK
from app.services.planning import optimize


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    init_db()


@pytest.fixture(autouse=True, scope="function")
def reset_rate_limit():
    from app.main import RATE
    RATE.clear()
    yield
    RATE.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# =====================================================================
# 1. CP-SAT Physical Optimizer Extremes & Invariants (Budget Removed)
# =====================================================================

def test_cpsat_zero_water_zero_cooling():
    """Zero cooling target with adequate water finds optimal feasible allocation."""
    zones = [zone("Ahmedabad", None)]
    res = optimize(zones, water_limit=1000, min_cooling=0.0)
    assert res["feasible"] is True
    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    assert "budget_limit" not in res
    assert "budget_enforced" not in res
    assert res["water_used"] <= 1000.0
    assert res["mean_cooling"] >= 0.0


def test_cpsat_impossible_cooling_infeasible():
    """min_cooling exceeding physical limits (4.0°C) must be INFEASIBLE and return diagnostics."""
    zones = [zone("Ahmedabad", None)]
    res = optimize(zones, water_limit=1000, min_cooling=4.0)
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"
    assert len(res["violations"]) > 0
    assert "Requested minimum mean cooling is incompatible" in res["violations"][0]


def test_cpsat_high_water_unconstrained_budget():
    """Unconstrained budget allows CP-SAT solver to maximize cooling subject only to physical surface & water capacities."""
    zones = sorted((f["properties"] for f in state("Ahmedabad")["data"]["features"]), key=lambda p: -p["risk_score"])[:5]
    res = optimize(zones, water_limit=5000, min_cooling=0.0)
    assert res["feasible"] is True
    assert res["mean_cooling"] > 0.0
    assert res["water_used"] <= 5000.0
    assert "total_cost" not in res
    assert "alternative" in res


def test_cpsat_discrete_5pct_step_invariant():
    """Verify that all intervention coverage percentages are discrete multiples of 5."""
    zones = sorted((f["properties"] for f in state("Ahmedabad")["data"]["features"]), key=lambda p: -p["risk_score"])[:3]
    res = optimize(zones, water_limit=2000, min_cooling=0.1)
    assert res["feasible"] is True
    for s in res["selections"]:
        for intervention, pct in s["coverage"].items():
            assert pct % 5 == 0, f"Intervention {intervention} coverage {pct}% is not a multiple of 5"


def test_cpsat_water_limit_strict_invariant():
    """Verify water_used <= water_limit strictly holds across allocations."""
    zones = sorted((f["properties"] for f in state("Ahmedabad")["data"]["features"]), key=lambda p: -p["risk_score"])[:4]
    water_limit = 1200
    res = optimize(zones, water_limit=water_limit, min_cooling=0.0)
    assert res["feasible"] is True
    assert res["water_used"] <= water_limit + 1e-6
    assert sum(s["water_m3_day"] for s in res["selections"]) <= water_limit + 1e-6


def test_cpsat_roof_mutual_exclusivity_invariant():
    """Cool roofs and rooftop gardens must never coexist in the same zone."""
    zones = sorted((f["properties"] for f in state("Ahmedabad")["data"]["features"]), key=lambda p: -p["risk_score"])[:3]
    res = optimize(zones, water_limit=3000, min_cooling=0.0)
    assert res["feasible"] is True
    for s in res["selections"]:
        cov = s["coverage"]
        assert not (cov.get("cool_roofs", 0) > 0 and cov.get("roof_gardens", 0) > 0)


def test_cpsat_direct_negative_water():
    """Direct call with negative water limit returns INFEASIBLE cleanly."""
    zones = [zone("Ahmedabad", None)]
    res = optimize(zones, water_limit=-1000, min_cooling=0.0)
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"


def test_optimization_api_budget_parameters_removed(client):
    """Test optimizer API endpoint rejects removed budget parameters and runs unconstrained budget."""
    # Extra field 'budget_limit' must be rejected with 422 because it was deleted from OptimizationRequest
    r_budget = client.post("/api/optimization/run", json={"city": "Ahmedabad", "budget_limit": 50000})
    assert r_budget.status_code == 422

    # Extra field 'budget_enforced' must also be rejected with 422
    r_enforced = client.post("/api/optimization/run", json={"city": "Ahmedabad", "budget_enforced": True})
    assert r_enforced.status_code == 422

    # Standard physical request without budget succeeds cleanly
    r_valid = client.post("/api/optimization/run", json={"city": "Ahmedabad", "water_limit": 800})
    assert r_valid.status_code == 200
    data = r_valid.json()
    assert data["feasible"] is True
    assert "budget_limit" not in data
    assert "budget_enforced" not in data
    assert "alternative" in data


# =====================================================================
# 2. Concurrency & Thread-Safety Stress Testing (state.py)
# =====================================================================

def test_state_concurrent_cold_start():
    """Clear state and fire 20 concurrent threads calling state('Ahmedabad')."""
    clear_state("Ahmedabad")
    assert "Ahmedabad" not in STATE

    results = []
    errors = []

    def fetch_state():
        try:
            s = state("Ahmedabad")
            results.append(s["data"]["metadata"]["city"])
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=fetch_state) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 20
    assert all(c == "Ahmedabad" for c in results)
    assert "Ahmedabad" in STATE


def test_state_concurrent_multicity_reads():
    """Concurrently read state, overview, and zones across Ahmedabad, Delhi, Hyderabad across 30 threads."""
    cities = ["Ahmedabad", "Delhi", "Hyderabad"]
    errors = []
    zone_counts = []

    def task(city_name):
        try:
            s = state(city_name)
            ov = get_city_overview(city_name)
            z = zone(city_name)
            assert ov["zone_count"] == len(s["data"]["features"])
            assert z["city"] == city_name
            zone_counts.append(ov["zone_count"])
        except Exception as e:
            errors.append((city_name, e))

    threads = [threading.Thread(target=task, args=(cities[i % len(cities)],)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(zone_counts) == 30


def test_state_concurrent_retrain_and_reads():
    """Simulate retraining running in one thread while multiple threads read city overview."""
    errors = []

    def reader(count):
        for _ in range(count):
            try:
                ov = get_city_overview("Ahmedabad")
                assert ov["zone_count"] > 0
                assert "average_suhii" in ov
            except Exception as e:
                errors.append(e)

    def retrainer():
        try:
            s = state("Ahmedabad")
            with LOCK:
                import copy
                STATE["Ahmedabad"] = analyze(copy.deepcopy(s["data"]), retrain=False)
        except Exception as e:
            errors.append(e)

    read_threads = [threading.Thread(target=reader, args=(10,)) for _ in range(10)]
    retrain_thread = threading.Thread(target=retrainer)

    for t in read_threads:
        t.start()
    retrain_thread.start()

    for t in read_threads:
        t.join()
    retrain_thread.join()

    assert len(errors) == 0


def test_state_concurrent_api_client_burst(client):
    """Concurrently fire 30 requests through the FastAPI test client across various endpoints."""
    endpoints = [
        ("GET", "/api/overview?city=Ahmedabad", None),
        ("GET", "/api/heat/map?city=Delhi", None),
        ("GET", "/api/models?city=Hyderabad", None),
        ("GET", "/api/xai/importance?city=Ahmedabad", None),
        ("POST", "/api/heat/predict", {"city": "Ahmedabad"}),
        ("POST", "/api/reports/generate", {"city": "Delhi"}),
    ]

    errors = []
    statuses = []

    def call_ep(method, path, body):
        try:
            if method == "GET":
                r = client.get(path)
            else:
                r = client.post(path, json=body)
            statuses.append(r.status_code)
        except Exception as e:
            errors.append((path, e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(call_ep, *endpoints[i % len(endpoints)])
            for i in range(30)
        ]
        concurrent.futures.wait(futures)

    assert len(errors) == 0
    assert len(statuses) == 30
    assert all(code == 200 for code in statuses)


# =====================================================================
# 3. Router Edge Cases & Adversarial Input Probing
# =====================================================================

# --- 3.1 Heat Router (/api/cities, /api/overview, /api/heat/*) ---
def test_router_heat_edge_cases(client):
    # Invalid city in query param
    assert client.get("/api/overview?city=Atlantis").status_code == 422
    assert client.get("/api/heat/map?city=Tokyo").status_code == 422
    assert client.get("/api/heat/hotspots?city=London").status_code == 422

    # Non-existent zone in predict
    r404 = client.post("/api/heat/predict", json={"city": "Ahmedabad", "zone_id": "NON_EXISTENT_ZONE"})
    assert r404.status_code == 404

    # Extra fields forbidden in strict model
    r_extra = client.post("/api/heat/predict", json={"city": "Ahmedabad", "unexpected_payload": "attack"})
    assert r_extra.status_code == 422

    # Valid cities endpoint
    r_cities = client.get("/api/cities")
    assert r_cities.status_code == 200
    assert len(r_cities.json()) == 3


# --- 3.2 Models Router (/api/models, /api/models/train, /api/xai/*) ---
def test_router_models_edge_cases(client):
    # Invalid city
    assert client.get("/api/models?city=Paris").status_code == 422
    assert client.post("/api/models/train", json={"city": "Paris"}).status_code == 422
    assert client.get("/api/xai/importance?city=Paris").status_code == 422

    # Non-existent zone in explain
    r404 = client.post("/api/xai/explain", json={"city": "Ahmedabad", "zone_id": "NON_EXISTENT_ZONE"})
    assert r404.status_code == 404

    # Explain without zone_id falls back to highest-risk zone cleanly
    r_default = client.post("/api/xai/explain", json={"city": "Ahmedabad"})
    assert r_default.status_code == 200
    assert "contributions" in r_default.json()


# --- 3.3 Simulation Router (/api/interventions, /api/simulation/*) ---
def test_router_simulation_edge_cases(client):
    # Interventions catalog
    assert client.get("/api/interventions").status_code == 200

    # Unknown intervention key
    r_unk = client.post("/api/simulation/run", json={"coverage": {"space_mirror": 50}})
    assert r_unk.status_code == 422

    # Coverage > 100
    r_gt100 = client.post("/api/simulation/run", json={"coverage": {"trees": 150}})
    assert r_gt100.status_code == 422

    # Coverage negative
    r_neg = client.post("/api/simulation/run", json={"coverage": {"trees": -10}})
    assert r_neg.status_code == 422

    # Negative tree count
    r_tree_neg = client.post("/api/simulation/run", json={"tree_count": -5})
    assert r_tree_neg.status_code == 422

    # Tree count beyond maximum 500k
    r_tree_max = client.post("/api/simulation/run", json={"tree_count": 600_000})
    assert r_tree_max.status_code == 422

    # Negative water limit
    r_water_neg = client.post("/api/simulation/run", json={"water_limit": -50})
    assert r_water_neg.status_code == 422

    # Non-existent zone_id
    r404 = client.post("/api/simulation/run", json={"zone_id": "UNKNOWN_ZONE"})
    assert r404.status_code == 404

    # Historical results invalid city
    assert client.get("/api/simulation/results?city=Unknown").status_code == 422


# --- 3.4 Optimization Router (/api/optimization/*) ---
def test_router_optimization_edge_cases(client):
    # Duplicate zones
    r_dup = client.post("/api/optimization/run", json={"zone_ids": ["z1", "z1"]})
    assert r_dup.status_code == 422

    # Non-existent zone
    r404 = client.post("/api/optimization/run", json={"zone_ids": ["NON_EXISTENT_ZONE"]})
    assert r404.status_code == 404

    # Max length > 30 zones
    r_many = client.post("/api/optimization/run", json={"zone_ids": [f"z{i}" for i in range(35)]})
    assert r_many.status_code == 422

    # Impossible cooling with zero water
    r_infeasible = client.post(
        "/api/optimization/run",
        json={"water_limit": 0, "min_cooling": 2.5, "land_limit_pct": 0}
    )
    assert r_infeasible.status_code == 200
    data = r_infeasible.json()
    assert data["feasible"] is False
    assert len(data["violations"]) > 0

    # Historical results invalid city
    assert client.get("/api/optimization/results?city=Unknown").status_code == 422


# --- 3.5 Risk Router (/api/risk/analyze) ---
def test_router_risk_edge_cases(client):
    # Weight < 0.1
    assert client.post("/api/risk/analyze", json={"hazard_weight": 0.05}).status_code == 422

    # Weight > 3.0
    assert client.post("/api/risk/analyze", json={"exposure_weight": 4.5}).status_code == 422

    # Non-existent zone
    assert client.post("/api/risk/analyze", json={"zone_id": "MISSING"}).status_code == 404

    # Valid risk calculation
    r_ok = client.post("/api/risk/analyze", json={"city": "Ahmedabad", "hazard_weight": 1.5, "exposure_weight": 0.8})
    assert r_ok.status_code == 200
    assert len(r_ok.json()["zones"]) > 0


# --- 3.6 Data Router (/api/data/*) ---
def test_router_data_edge_cases(client):
    # Status
    assert client.get("/api/data/status").status_code == 200

    # Records invalid kind
    assert client.get("/api/data/records?kind=invalid_kind").status_code == 422

    # Series
    assert client.get("/api/data/series").status_code == 200

    # Ingest: lat without lon
    assert client.post("/api/data/ingest", json={"latitude": 23.0}).status_code == 422

    # Ingest: end_date < start_date
    assert client.post(
        "/api/data/ingest",
        json={"start_date": "2025-06-01", "end_date": "2025-05-01"}
    ).status_code == 422

    # Ingest: date range > 366 days
    assert client.post(
        "/api/data/ingest",
        json={"start_date": "2024-01-01", "end_date": "2025-02-01"}
    ).status_code == 422

    # Ingest: invalid GeoJSON boundary (Point instead of Polygon)
    assert client.post(
        "/api/data/ingest",
        json={"boundary": {"type": "Point", "coordinates": [72.5, 23.0]}}
    ).status_code == 422

    # Ingest: boundary > 4 square degrees
    large_poly = {
        "type": "Polygon",
        "coordinates": [[[70.0, 20.0], [75.0, 20.0], [75.0, 25.0], [70.0, 25.0], [70.0, 20.0]]]
    }
    assert client.post("/api/data/ingest", json={"boundary": large_poly}).status_code == 422


# --- 3.7 AI Router (/api/ai/chat) ---
def test_router_ai_edge_cases(client):
    # Empty message
    assert client.post("/api/ai/chat", json={"message": ""}).status_code == 422

    # Message > 2000 characters
    long_msg = "x" * 2001
    assert client.post("/api/ai/chat", json={"message": long_msg}).status_code == 422

    # Unknown provider
    assert client.post("/api/ai/chat", json={"message": "Help", "provider": "skynet"}).status_code == 422

    # Non-existent zone
    assert client.post("/api/ai/chat", json={"message": "Help", "zone_id": "MISSING"}).status_code == 404

    # Valid chat with local fallback
    r_chat = client.post("/api/ai/chat", json={"message": "Explain urban heat", "provider": "local"})
    assert r_chat.status_code == 200
    data = r_chat.json()
    assert data["provider"].startswith("local")
    assert data["fallback"] is True
    assert "summary" in data


# --- 3.8 Reports Router (/api/reports/*) ---
def test_router_reports_lifecycle_and_edge_cases(client):
    # Non-existent report downloads
    assert client.get("/api/reports/non_existent_id/download").status_code == 404
    assert client.get("/api/reports/non_existent_id/csv").status_code == 404
    assert client.get("/api/reports/non_existent_id/markdown").status_code == 404

    # Generate with invalid city
    assert client.post("/api/reports/generate", json={"city": "Rome"}).status_code == 422

    # Generate valid report
    r_gen = client.post("/api/reports/generate", json={"city": "Ahmedabad"})
    assert r_gen.status_code == 200
    gen_data = r_gen.json()
    rep_id = gen_data["id"]

    # Verify JSON download
    r_json = client.get(gen_data["download_url"])
    assert r_json.status_code == 200
    assert r_json.headers["content-type"].startswith("application/json")
    assert r_json.json()["title"].startswith("Ahmedabad")

    # Verify CSV download
    r_csv = client.get(gen_data["csv_url"])
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "predicted_suhii" in r_csv.text

    # Verify Markdown download
    r_md = client.get(gen_data["markdown_url"])
    assert r_md.status_code == 200
    assert "text/markdown" in r_md.headers["content-type"]
    assert "SYNTHETIC DEMONSTRATION" in r_md.text
