"""Explicitly hypothetical interventions, separate from predictive SHAP associations."""

import math
from ortools.sat.python import cp_model

INTERVENTIONS = {
    "trees": {
        "name": "Urban trees",
        "surface": "ground",
        "cooling_per_10pct": 0.35,
        "water_per_pct": 20,
        "vegetation": True,
    },
    "vegetation": {
        "name": "Native vegetation",
        "surface": "ground",
        "cooling_per_10pct": 0.25,
        "water_per_pct": 10,
        "vegetation": True,
    },
    "parks": {
        "name": "Pocket parks",
        "surface": "ground",
        "cooling_per_10pct": 0.30,
        "water_per_pct": 15,
        "vegetation": True,
    },
    "cool_roofs": {
        "name": "Cool roofs",
        "surface": "roof",
        "cooling_per_10pct": 0.28,
        "water_per_pct": 0,
        "vegetation": False,
    },
    "pavements": {
        "name": "Reflective pavements",
        "surface": "road",
        "cooling_per_10pct": 0.18,
        "water_per_pct": 0,
        "vegetation": False,
    },
    "corridors": {
        "name": "Green corridors",
        "surface": "ground",
        "cooling_per_10pct": 0.32,
        "water_per_pct": 15,
        "vegetation": True,
    },
    "roof_gardens": {
        "name": "Rooftop gardens",
        "surface": "roof",
        "cooling_per_10pct": 0.22,
        "water_per_pct": 12,
        "vegetation": True,
    },
    "water": {
        "name": "Water-based cooling",
        "surface": "ground",
        "cooling_per_10pct": 0.20,
        "water_per_pct": 40,
        "vegetation": False,
    },
}
ASSUMPTIONS = [
    "Hypothetical coefficients chosen for software demonstration; no causal or locally calibrated cooling claim.",
    "Coverage is percentage points of total zone area, not percentage of roofs or roads.",
    "Cooling combines linearly up to a 3°C cap; ±40% sensitivity range is not a statistical confidence interval.",
    "Water is a hypothetical daily requirement in m³/day per percentage point per km².",
    "No budgets or financial costs are used.",
]


def risk(p, weights=(1, 1, 1)):
    hazard = min(1, max(0, p["predicted_suhii"]) / 8)
    exposure = min(1, p["population_density"] / 25000)
    vulnerability = min(1, p["elderly_share"] / 0.25)
    value = (
        100
        * hazard ** weights[0]
        * exposure ** weights[1]
        * vulnerability ** weights[2]
    )
    return {
        "risk_score": value,
        "hazard": hazard,
        "exposure": exposure,
        "vulnerability": vulnerability,
        "risk_level": "High" if value >= 20 else "Moderate" if value >= 8 else "Low",
        "missing_indicators": [
            "Socioeconomic status",
            "Health conditions",
            "Access to cooling",
        ],
        "method": "100 × (SUHII / 8)^wH × (population/km² / 25000)^wE × (elderly share / .25)^wV; components clipped to [0,1]. Synthetic age share is a limited vulnerability proxy.",
    }


def simulate(p, coverage, water_limit=1000, max_vegetation_pct=40):
    violations = []
    totals = {"ground": 0.0, "roof": 0.0, "road": 0.0}
    water = 0.0
    cooling = 0.0
    vegetation = 0.0
    for key, pct in coverage.items():
        if key not in INTERVENTIONS:
            raise ValueError(f"Unknown intervention: {key}")
        if not math.isfinite(pct) or pct < 0 or pct > 100:
            raise ValueError("Coverage must be finite and between 0 and 100.")
        spec = INTERVENTIONS[key]
        totals[spec["surface"]] += pct
        water += pct * spec["water_per_pct"] * p["area_km2"]
        cooling += pct / 10 * spec["cooling_per_10pct"]
        if spec["vegetation"]:
            vegetation += pct
    capacities = {
        "ground": p["available_land_pct"],
        "roof": p["roof_pct"],
        "road": p["road_pct"],
    }
    for surface, total in totals.items():
        if total > capacities[surface] + 1e-6:
            violations.append(
                f"{surface.title()} coverage exceeds available area ({capacities[surface]:.1f}%)."
            )
    if p["protected"] and totals["ground"] > 0:
        violations.append("Protected zone prohibits ground interventions.")
    if coverage.get("cool_roofs", 0) > 0 and coverage.get("roof_gardens", 0) > 0:
        violations.append(
            "Cool roofs and rooftop gardens are mutually exclusive in this prototype."
        )
    if vegetation > max_vegetation_pct:
        violations.append("Added vegetation exceeds the configured maximum.")
    if water > water_limit + 1e-6:
        violations.append("Daily water requirement exceeds the available water.")
    cooling = min(3.0, cooling)
    before = p["predicted_suhii"]
    after = before - cooling
    return {
        "zone_id": p["id"],
        "coverage": coverage,
        "feasible": not violations,
        "violations": violations,
        "before_suhii": before,
        "after_suhii": after if not violations else None,
        "estimated_cooling": cooling if not violations else None,
        "sensitivity_range": [cooling * 0.6, cooling * 1.4] if not violations else None,
        "water_m3_day": water,
        "area_coverage": totals,
        "hypothetical": True,
        "assumptions": ASSUMPTIONS,
    }


def optimize(
    zones, water_limit=1000, max_vegetation_pct=40, min_cooling=0.0, land_limit_pct=100
):
    model = cp_model.CpModel()
    variables = {}
    cool_terms = []
    water_terms = []
    objectives = []
    for p in zones:
        z = p["id"]
        local = {}
        for key, spec in INTERVENTIONS.items():
            surface = spec["surface"]
            cap = {
                "ground": p["available_land_pct"] * land_limit_pct / 100,
                "roof": p["roof_pct"],
                "road": p["road_pct"],
            }[surface]
            if p["protected"] and surface == "ground":
                cap = 0
            levels = model.NewIntVar(0, int(cap // 5), f"{z}-{key}")
            variables[(z, key)] = levels
            local[key] = levels
            water_terms.append(levels * int(5 * spec["water_per_pct"] * p["area_km2"]))
        for surface in ["ground", "roof", "road"]:
            cap = {
                "ground": p["available_land_pct"] * land_limit_pct / 100,
                "roof": p["roof_pct"],
                "road": p["road_pct"],
            }[surface]
            model.Add(
                sum(
                    v * 5
                    for k, v in local.items()
                    if INTERVENTIONS[k]["surface"] == surface
                )
                <= int(cap)
            )
        model.Add(
            sum(v * 5 for k, v in local.items() if INTERVENTIONS[k]["vegetation"])
            <= int(max_vegetation_pct)
        )
        roof_kind = model.NewBoolVar(f"{z}-roof-kind")
        model.Add(local["cool_roofs"] == 0).OnlyEnforceIf(roof_kind)
        model.Add(local["roof_gardens"] == 0).OnlyEnforceIf(roof_kind.Not())
        # Thousandths of a degree; all coefficients are integer at 5% increments.
        raw = sum(
            v * round(INTERVENTIONS[k]["cooling_per_10pct"] * 500)
            for k, v in local.items()
        )
        cool = model.NewIntVar(0, 3000, f"{z}-cooling")
        model.AddMinEquality(cool, [raw, 3000])
        cool_terms.append(cool)
        priority = max(
            1,
            round(
                p["population"]
                * (0.2 + p["elderly_share"])
                * max(0.2, p["predicted_suhii"])
            ),
        )
        objectives.append(cool * priority)
    model.Add(sum(water_terms) <= int(water_limit))
    model.Add(sum(cool_terms) >= math.ceil(min_cooling * 1000 * len(zones)))
    model.Maximize(sum(objectives))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 8
    solver.parameters.num_search_workers = 2
    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {
            "status": solver.StatusName(status),
            "feasible": False,
            "selections": [],
            "violations": (
                [
                    "Requested minimum mean cooling is incompatible with land, roof, road, protection, vegetation, or water constraints. Reduce the minimum cooling target or relax the limits."
                ]
                if status == cp_model.INFEASIBLE
                else ["Solver time limit reached without a feasible solution."]
            ),
            "hypothetical": True,
            "assumptions": ASSUMPTIONS,
        }
    selections = []
    for p in zones:
        coverage = {k: solver.Value(variables[(p["id"], k)]) * 5 for k in INTERVENTIONS}
        coverage = {k: v for k, v in coverage.items() if v}
        result = simulate(p, coverage, water_limit, max_vegetation_pct)
        selections.append(
            {
                **result,
                "zone_name": p["name"],
                "population": p["population"],
                "risk_score": risk(p)["risk_score"],
            }
        )
    return {
        "status": solver.StatusName(status),
        "feasible": True,
        "selections": selections,
        "water_used": sum(s["water_m3_day"] for s in selections),
        "water_available": water_limit,
        "mean_cooling": sum(s["estimated_cooling"] for s in selections) / len(zones),
        "population_in_selected_zones": sum(
            s["population"] for s in selections if s["coverage"]
        ),
        "violations": [],
        "hypothetical": True,
        "assumptions": ASSUMPTIONS,
        "objective": "Maximize hypothetical surface cooling weighted by population, synthetic elderly share, and surface heat. This is a prioritization proxy, not an estimate of people protected.",
        "explanation": "Selected 5-percentage-point increments with shared ground/roof/road capacities, protected-land exclusions, roof compatibility, total water and per-zone vegetation limits.",
        "constraints": {
            "max_vegetation_pct": max_vegetation_pct,
            "land_limit_pct": land_limit_pct,
            "min_mean_cooling": min_cooling,
        },
    }
