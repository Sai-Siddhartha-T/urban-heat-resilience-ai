"""Unit and integration tests for combinatorial multi-zone intervention optimization.

Verifies:
1. Literature-grounded cooling intervention categories (trees, vegetation, parks, cool_roofs,
   pavements, corridors, roof_gardens, water) with empirical citations and uncertainty ranges.
2. Physical simulation, feasibility constraints, and metric deltas (ground, roof, road,
   protected land, roof exclusivity, max vegetation, water limit, 3°C cooling saturation,
   LST delta, NDVI delta, albedo delta, runoff reduction).
3. Complete removal of financial budget constraints (CP-SAT solver unconstrained by budget,
   zero financial fields or costs in schemas or models).
4. Discrete 5-percentage-point decision variables and equity-weighted priority objective.
5. Infeasibility diagnostics and automatic half-water alternative scenarios.
6. Spatial priority rankings and feasible allocation matrices.
7. 50% water sensitivity contingency analysis.
8. Solver execution stability guard preventing native C++ crashes on Windows Python 3.14.
9. API endpoint contracts (/api/optimization/run and /api/optimization/results).
10. Backward compatibility re-export in planning.py.
"""

import pytest
from fastapi.testclient import TestClient
from ortools.sat.python import cp_model
from app.db import init_db
from app.main import app
from app.services.state import state, zone
from app.services.optimization import (
    optimize,
    safe_solve,
    calculate_max_possible_cooling,
    calculate_zero_water_cooling,
    diagnose_infeasibility,
)
from app.services.planning import (
    INTERVENTIONS,
    LITERATURE_REFERENCES,
    CANOPY_M2_PER_TREE,
    apply_convenience,
    simulate,
    optimize as planning_optimize,
)


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    init_db()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_zones():
    """Retrieve top-5 priority zones from Ahmedabad baseline state."""
    features = state("Ahmedabad", mode="demo")["data"]["features"]
    return sorted((f["properties"] for f in features), key=lambda p: -p["risk_score"])[:5]


# =====================================================================
# 1. 8 Cooling Intervention Categories, Literature Grounding & Physics
# =====================================================================


def test_all_8_cooling_interventions_catalog():
    """Verify presence and attributes of all 8 literature-derived cooling intervention categories."""
    expected_categories = [
        "trees",
        "vegetation",
        "parks",
        "cool_roofs",
        "pavements",
        "corridors",
        "roof_gardens",
        "water",
    ]
    for cat in expected_categories:
        assert cat in INTERVENTIONS, f"Intervention category '{cat}' missing from catalog"
        spec = INTERVENTIONS[cat]
        assert "name" in spec
        assert spec["surface"] in ["ground", "roof", "road"]
        assert spec["cooling_per_10pct"] > 0
        assert spec["water_per_pct"] >= 0
        assert isinstance(spec["vegetation"], bool)
        assert "citation" in spec
        assert "cooling_uncertainty" in spec
        assert len(spec["cooling_uncertainty"]) == 2
        assert spec["cooling_uncertainty"][0] <= spec["cooling_uncertainty"][1]
        assert "cooling_mechanism" in spec
        # Strict zero financial budget/cost audit
        assert "cost_per_pct" not in spec
        assert "capex_per_m2" not in spec
        assert "opex_per_m2_yr" not in spec
        assert "budget" not in spec

    assert CANOPY_M2_PER_TREE == 28.0
    assert len(LITERATURE_REFERENCES) >= 5


def test_tree_planting_canopy_conversion():
    """Verify tree planting canopy conversion (28.0 m2/tree) translates tree counts into zone area %."""
    synthetic_zone = {
        "id": "tree-test-zone",
        "name": "Tree Test Area",
        "city": "Ahmedabad",
        "area_km2": 1.0,  # 1,000,000 m2
        "available_land_pct": 40.0,
        "roof_pct": 20.0,
        "road_pct": 15.0,
        "population": 5000,
        "elderly_share": 0.1,
        "predicted_suhii": 2.5,
        "protected": False,
    }
    # 1,000 trees * 28 m2 = 28,000 m2 / 1,000,000 m2 = 2.8%
    cov, notes = apply_convenience(synthetic_zone, {}, tree_count=1000)
    assert cov["trees"] == pytest.approx(2.8, abs=1e-3)
    assert any("28 m²" in n for n in notes)


def test_simulation_uncertainty_ranges_and_metrics_delta():
    """Verify simulator computes explicit uncertainty bounds and feasible metric deltas."""
    zone_data = {
        "id": "sim-test-zone",
        "name": "Simulation Test Zone",
        "area_km2": 1.0,
        "available_land_pct": 50.0,
        "roof_pct": 30.0,
        "road_pct": 20.0,
        "predicted_suhii": 3.0,
        "protected": False,
    }
    res = simulate(zone_data, {"trees": 10.0, "cool_roofs": 15.0}, water_limit=500)
    assert res["feasible"] is True
    assert res["hypothetical"] is True
    assert "uncertainty_range" in res
    assert len(res["uncertainty_range"]) == 2
    assert res["uncertainty_range"][0] <= res["uncertainty_range"][1]
    assert "metrics_delta" in res
    md = res["metrics_delta"]
    assert "lst_delta_celsius" in md
    assert "suhii_delta_celsius" in md
    assert "ndvi_delta" in md
    assert "albedo_delta" in md
    assert "runoff_reduction_pct" in md
    assert md["suhii_delta_celsius"] < 0
    assert md["ndvi_delta"] > 0
    assert md["albedo_delta"] > 0
    assert md["runoff_reduction_pct"] > 0
    assert "literature_citations" in res
    assert len(res["literature_citations"]) >= 5


# =====================================================================
# 2. Feasible Optimization Scenarios & Physical Invariants
# =====================================================================


def test_optimization_feasible_default(sample_zones):
    """Basic optimization with default parameters finds feasible multi-zone plan."""
    res = optimize(
        sample_zones,
        water_limit=1000,
        max_vegetation_pct=40,
        min_cooling=0.0,
        land_limit_pct=100,
    )
    assert res["feasible"] is True
    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    assert res["water_used"] <= 1000
    assert res["water_available"] == 1000
    assert len(res["selections"]) == len(sample_zones)
    assert res["mean_cooling"] >= 0.0
    # Complete removal of budget
    assert "budget_limit" not in res
    assert "budget_enforced" not in res
    assert "total_cost" not in res
    assert res["violations"] == []
    assert "alternative" in res
    assert "spatial_priority_ranking" in res
    assert len(res["spatial_priority_ranking"]) == len(sample_zones)
    assert "allocations" in res
    assert "sensitivity_50pct_water" in res


def test_optimization_discrete_5pct_step_decision_variables(sample_zones):
    """CP-SAT solver decision variables must be discrete 5-percentage-point increments."""
    res = optimize(sample_zones, water_limit=2500, min_cooling=0.1)
    assert res["feasible"] is True
    for s in res["selections"]:
        for k, pct in s["coverage"].items():
            assert pct % 5 == 0, f"Zone {s['zone_id']} intervention {k} has non-discrete coverage {pct}%"


def test_optimization_water_limit_strict_enforcement(sample_zones):
    """Restricted water limit (250 m³/day) is strictly respected by all allocations."""
    water_cap = 250
    res = optimize(sample_zones, water_limit=water_cap, min_cooling=0.0)
    assert res["feasible"] is True
    assert res["water_used"] <= water_cap + 1e-6
    assert sum(s["water_m3_day"] for s in res["selections"]) <= water_cap + 1e-6


def test_optimization_land_limit_scaling(sample_zones):
    """Ground land limit (land_limit_pct=30%) caps ground interventions proportionally."""
    land_pct = 30
    res = optimize(sample_zones, land_limit_pct=land_pct, min_cooling=0.0)
    assert res["feasible"] is True
    for s in res["selections"]:
        ground_cov = sum(
            pct for k, pct in s["coverage"].items() if INTERVENTIONS[k]["surface"] == "ground"
        )
        z_prop = next(p for p in sample_zones if p["id"] == s["zone_id"])
        allowed_ground = z_prop["available_land_pct"] * (land_pct / 100.0)
        assert ground_cov <= allowed_ground + 1e-6


def test_optimization_road_capacity_constraint(sample_zones):
    """Road surface capacity strictly limits reflective pavements coverage to <= road_pct."""
    res = optimize(sample_zones, water_limit=3000, min_cooling=0.0)
    assert res["feasible"] is True
    for s in res["selections"]:
        pavement_cov = s["coverage"].get("pavements", 0.0)
        z_prop = next(p for p in sample_zones if p["id"] == s["zone_id"])
        assert pavement_cov <= z_prop["road_pct"] + 1e-6


def test_optimization_roof_capacity_constraint(sample_zones):
    """Roof surface capacity strictly limits combined roof coverage to <= roof_pct."""
    res = optimize(sample_zones, water_limit=3000, min_cooling=0.0)
    assert res["feasible"] is True
    for s in res["selections"]:
        roof_cov = s["coverage"].get("cool_roofs", 0.0) + s["coverage"].get("roof_gardens", 0.0)
        z_prop = next(p for p in sample_zones if p["id"] == s["zone_id"])
        assert roof_cov <= z_prop["roof_pct"] + 1e-6


def test_optimization_protected_zone_exclusion():
    """Protected zones must completely prohibit ground interventions."""
    synthetic_zone = {
        "id": "protected-test-zone",
        "name": "Protected Sanctuary",
        "city": "Ahmedabad",
        "area_km2": 1.5,
        "available_land_pct": 50.0,
        "roof_pct": 20.0,
        "road_pct": 15.0,
        "population": 10000,
        "population_density": 6667,
        "elderly_share": 0.12,
        "predicted_suhii": 3.0,
        "observed_suhii": 3.0,
        "protected": True,
        "risk_score": 25.0,
    }
    res = optimize([synthetic_zone], water_limit=500, min_cooling=0.0)
    assert res["feasible"] is True
    sel = res["selections"][0]
    ground_cov = sum(
        pct for k, pct in sel["coverage"].items() if INTERVENTIONS[k]["surface"] == "ground"
    )
    assert ground_cov == 0.0


def test_optimization_roof_mutual_exclusivity(sample_zones):
    """Cool roofs and rooftop gardens must never be allocated simultaneously on the same zone."""
    res = optimize(sample_zones, water_limit=3000, min_cooling=0.0)
    assert res["feasible"] is True
    for s in res["selections"]:
        has_cool_roofs = s["coverage"].get("cool_roofs", 0) > 0
        has_roof_gardens = s["coverage"].get("roof_gardens", 0) > 0
        assert not (has_cool_roofs and has_roof_gardens)


def test_optimization_max_vegetation_ceiling(sample_zones):
    """Total added vegetative interventions cannot exceed max_vegetation_pct."""
    max_veg = 15
    res = optimize(sample_zones, max_vegetation_pct=max_veg, water_limit=2000)
    assert res["feasible"] is True
    for s in res["selections"]:
        veg_total = sum(
            pct for k, pct in s["coverage"].items() if INTERVENTIONS[k]["vegetation"]
        )
        assert veg_total <= max_veg + 1e-6


def test_optimization_cooling_saturation_at_3_degrees():
    """Combined cooling per zone must saturate at 3.0°C maximum."""
    massive_zone = {
        "id": "massive-zone",
        "name": "Expansive Zone",
        "city": "Ahmedabad",
        "area_km2": 0.5,
        "available_land_pct": 80.0,
        "roof_pct": 50.0,
        "road_pct": 30.0,
        "population": 20000,
        "elderly_share": 0.2,
        "predicted_suhii": 5.0,
        "protected": False,
        "risk_score": 35.0,
    }
    res = optimize([massive_zone], water_limit=50000, max_vegetation_pct=80, min_cooling=0.0)
    assert res["feasible"] is True
    sel = res["selections"][0]
    assert sel["estimated_cooling"] <= 3.0
    assert sel["after_suhii"] >= massive_zone["predicted_suhii"] - 3.0 - 1e-6


def test_optimization_equity_weighted_priority():
    """Solver prioritizes higher-risk zone with larger vulnerable population under water constraints."""
    zone_high_priority = {
        "id": "zone-high-equity",
        "name": "High Vulnerability District",
        "city": "Ahmedabad",
        "area_km2": 1.0,
        "available_land_pct": 40.0,
        "roof_pct": 20.0,
        "road_pct": 10.0,
        "population": 50000,
        "elderly_share": 0.25,
        "predicted_suhii": 4.5,
        "protected": False,
        "risk_score": 40.0,
    }
    zone_low_priority = {
        "id": "zone-low-equity",
        "name": "Low Vulnerability Suburb",
        "city": "Ahmedabad",
        "area_km2": 1.0,
        "available_land_pct": 40.0,
        "roof_pct": 20.0,
        "road_pct": 10.0,
        "population": 1000,
        "elderly_share": 0.05,
        "predicted_suhii": 1.0,
        "protected": False,
        "risk_score": 5.0,
    }
    res = optimize([zone_high_priority, zone_low_priority], water_limit=150, min_cooling=0.0)
    assert res["feasible"] is True
    sel_high = next(s for s in res["selections"] if s["zone_id"] == "zone-high-equity")
    sel_low = next(s for s in res["selections"] if s["zone_id"] == "zone-low-equity")
    assert (sel_high["estimated_cooling"] or 0.0) >= (sel_low["estimated_cooling"] or 0.0)


def test_optimization_cooling_target_achievement(sample_zones):
    """When a positive min_cooling target (0.2°C) is feasible, mean_cooling meets or exceeds it."""
    target_cooling = 0.2
    res = optimize(sample_zones, min_cooling=target_cooling, water_limit=3000)
    assert res["feasible"] is True
    assert res["mean_cooling"] >= target_cooling - 1e-6


def test_optimization_half_water_alternative(sample_zones):
    """Feasible optimization automatically generates a valid half-water alternative scenario."""
    water_cap = 1000
    res = optimize(sample_zones, water_limit=water_cap, min_cooling=0.0)
    assert res["feasible"] is True
    assert "alternative" in res
    alt = res["alternative"]
    assert alt["label"] == "Half-water alternative"
    assert alt["feasible"] is True
    assert alt["water_used"] <= (water_cap * 0.5) + 1e-6


def test_optimization_spatial_priority_ranking(sample_zones):
    """Verify explicit spatial priority rankings and zone allocation matrix generation."""
    res = optimize(sample_zones, water_limit=2000, min_cooling=0.0)
    assert res["feasible"] is True
    assert "spatial_priority_ranking" in res
    assert isinstance(res["spatial_priority_ranking"], list)
    assert len(res["spatial_priority_ranking"]) == len(sample_zones)
    assert "spatial_priority_details" in res
    assert len(res["spatial_priority_details"]) == len(sample_zones)
    # Check ranking ordering
    details = res["spatial_priority_details"]
    assert details[0]["rank"] == 1
    assert "allocations" in res
    assert isinstance(res["allocations"], dict)


def test_optimization_water_sensitivity_50pct(sample_zones):
    """Verify 50% water sensitivity contingency analysis calculations."""
    res = optimize(sample_zones, water_limit=1500, min_cooling=0.0)
    assert res["feasible"] is True
    assert "sensitivity_50pct_water" in res
    sens = res["sensitivity_50pct_water"]
    assert sens["water_limit_50pct"] == 750.0
    assert sens["water_used_50pct"] <= 750.0 + 1e-6
    assert "cooling_loss_celsius" in sens
    assert "cooling_retention_pct" in sens
    assert 0.0 <= sens["cooling_retention_pct"] <= 100.0
    assert "vulnerable_population_impact" in sens


def test_optimization_empty_zones():
    """Empty zones list returns optimal feasible result with zero selections."""
    res = optimize([])
    assert res["feasible"] is True
    assert res["status"] == "OPTIMAL"
    assert res["selections"] == []
    assert res["mean_cooling"] == 0.0
    assert res["water_used"] == 0.0


def test_optimization_single_zone(sample_zones):
    """Single zone optimization executes correctly and respects local capacities."""
    res = optimize([sample_zones[0]], water_limit=500, min_cooling=0.1)
    assert res["feasible"] is True
    assert len(res["selections"]) == 1
    assert res["mean_cooling"] >= 0.1 - 1e-6


def test_solver_execution_stability_guard():
    """Verify safe_solve executes reliably and handles unexpected exceptions gracefully."""
    model = cp_model.CpModel()
    x = model.NewIntVar(0, 10, "x")
    model.Add(x >= 3)
    model.Maximize(x)
    solver = cp_model.CpSolver()
    status = safe_solve(solver, model, max_time_seconds=5.0)
    assert status == cp_model.OPTIMAL
    assert solver.Value(x) == 10


def test_planning_reexport_backward_compatibility():
    """Verify that backend.app.services.planning re-exports optimize identically."""
    assert optimize is planning_optimize


# =====================================================================
# 3. Infeasible Scenarios & Clear Warning Diagnostics
# =====================================================================


def test_optimization_infeasible_impossible_cooling(sample_zones):
    """Requesting impossible cooling (3.8°C when cap is 3.0°C) is INFEASIBLE and returns clear warnings."""
    res = optimize(sample_zones, min_cooling=3.8, water_limit=5000)
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"
    assert len(res["violations"]) > 0
    assert "Requested minimum mean cooling is incompatible" in res["violations"][0]
    assert any("Physical capacity limitation" in v for v in res["violations"])
    assert any("Recommendation:" in v for v in res["violations"])


def test_optimization_infeasible_zero_water_positive_cooling(sample_zones):
    """Zero water with cooling requiring vegetation (2.5°C) is INFEASIBLE and identifies water bottleneck."""
    res = optimize(sample_zones, water_limit=0, min_cooling=2.5)
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"
    assert len(res["violations"]) > 0
    assert any("Water availability limitation" in v for v in res["violations"])


def test_optimization_infeasible_zero_land_and_vegetation(sample_zones):
    """Zero land and zero vegetation with 2.5°C cooling target is INFEASIBLE with surface diagnostics."""
    res = optimize(
        sample_zones,
        water_limit=2000,
        land_limit_pct=0,
        max_vegetation_pct=0,
        min_cooling=2.5,
    )
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"
    assert any("Land availability constraint" in v or "Vegetation constraint" in v for v in res["violations"])


def test_optimization_infeasible_negative_water(sample_zones):
    """Negative water limit makes water constraint mathematically impossible."""
    res = optimize(sample_zones, water_limit=-50, min_cooling=0.0)
    assert res["feasible"] is False
    assert res["status"] == "INFEASIBLE"
    assert len(res["violations"]) > 0


def test_diagnose_infeasibility_helper(sample_zones):
    """Direct verification of diagnostic warnings generator."""
    warnings = diagnose_infeasibility(
        sample_zones,
        water_limit=0,
        max_vegetation_pct=40,
        min_cooling=3.5,
        land_limit_pct=100,
    )
    assert len(warnings) >= 3
    assert "Requested minimum mean cooling is incompatible" in warnings[0]
    assert any("Physical capacity limitation" in w for w in warnings)
    assert any("Water availability limitation" in w for w in warnings)
    assert any("Recommendation:" in w for w in warnings)


def test_theoretical_cooling_calculators(sample_zones):
    """Verify max cooling upper bounds are positive and zero-water cooling <= total max cooling."""
    max_cool = calculate_max_possible_cooling(sample_zones, land_limit_pct=100, max_vegetation_pct=40)
    zero_water_cool = calculate_zero_water_cooling(sample_zones)
    assert max_cool > 0.0
    assert zero_water_cool > 0.0
    assert zero_water_cool <= max_cool


# =====================================================================
# 4. API Contract Verification (/api/optimization/run)
# =====================================================================


def test_api_optimization_run_feasible(client):
    """POST /api/optimization/run without budget fields succeeds with unconstrained budget."""
    payload = {
        "city": "Ahmedabad",
        "mode": "demo",
        "water_limit": 800,
        "max_vegetation_pct": 35,
        "land_limit_pct": 80,
        "min_cooling": 0.1,
    }
    resp = client.post("/api/optimization/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["feasible"] is True
    assert data["status"] in ["OPTIMAL", "FEASIBLE"]
    assert "budget_limit" not in data
    assert "budget_enforced" not in data
    assert data["water_used"] <= 800
    assert "alternative" in data
    assert data["alternative"]["label"] == "Half-water alternative"
    assert data["alternative"]["water_used"] <= 400 + 1e-6
    assert "spatial_priority_ranking" in data


def test_api_optimization_run_infeasible_clear_warnings(client):
    """POST /api/optimization/run with impossible constraints returns 200 with INFEASIBLE and warnings."""
    payload = {
        "city": "Ahmedabad",
        "mode": "demo",
        "water_limit": 10,
        "max_vegetation_pct": 10,
        "land_limit_pct": 10,
        "min_cooling": 3.5,
    }
    resp = client.post("/api/optimization/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["feasible"] is False
    assert data["status"] == "INFEASIBLE"
    assert len(data["violations"]) > 0
    assert any("limitation" in v.lower() or "constraint" in v.lower() for v in data["violations"])


def test_api_optimization_run_duplicate_zones_validation(client):
    """POST /api/optimization/run rejects duplicate zone IDs with HTTP 422."""
    payload = {
        "city": "Ahmedabad",
        "mode": "demo",
        "zone_ids": ["zone-1", "zone-1"],
    }
    resp = client.post("/api/optimization/run", json=payload)
    assert resp.status_code == 422
    assert "Duplicate zones are not allowed" in resp.json()["detail"]


def test_api_optimization_results_history(client):
    """GET /api/optimization/results returns list of historical runs for requested city."""
    client.post("/api/optimization/run", json={"city": "Ahmedabad", "mode": "demo", "water_limit": 500})
    resp = client.get("/api/optimization/results?city=Ahmedabad")
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    assert all(r.get("city") == "Ahmedabad" for r in runs)
