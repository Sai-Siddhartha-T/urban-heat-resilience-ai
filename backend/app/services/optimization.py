"""Combinatorial discrete optimization of urban heat interventions via Google OR-Tools CP-SAT solver.

Implements equity-weighted discrete optimization under physical surface capacity,
land protection, roof exclusivity, vegetation ceiling, water limits, and cooling saturation.
Financial budget constraints are completely removed.
"""

import logging
import math
from typing import Any, Dict, List, Optional
from ortools.sat.python import cp_model
from app.services.planning import INTERVENTIONS, ASSUMPTIONS, simulate
from app.services.risk import risk

log = logging.getLogger("heatwise.optimization")


def safe_solve(
    solver: cp_model.CpSolver,
    model: cp_model.CpModel,
    max_time_seconds: float = 8.0,
) -> int:
    """Execute CP-SAT solver with exception trapping and single-worker fallback.

    Prevents native C++ access violation crashes or threading collisions on Windows Python 3.14
    by catching runtime/system exceptions and falling back to a deterministic single-worker search.

    Args:
        solver: OR-Tools CpSolver instance.
        model: OR-Tools CpModel instance.
        max_time_seconds: Maximum solve time in seconds.

    Returns:
        Solver status integer (cp_model.OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, etc.).
    """
    import sys
    is_win = sys.platform == "win32"
    solver.parameters.max_time_in_seconds = float(max_time_seconds)
    solver.parameters.num_search_workers = 1 if is_win else 2
    solver.parameters.log_search_progress = False
    try:
        return solver.Solve(model)
    except (SystemError, RuntimeError, MemoryError, Exception, BaseException) as exc:
        log.warning(
            "CP-SAT solver encountered exception during execution: %s. Falling back to single-worker safe search.",
            exc,
        )
        try:
            solver.parameters.num_search_workers = 1
            solver.parameters.interleave_search = True
            return solver.Solve(model)
        except (Exception, BaseException) as fallback_exc:
            log.error("CP-SAT fallback solve failed: %s", fallback_exc)
            return cp_model.UNKNOWN


def calculate_max_possible_cooling(
    zones: list[dict[str, Any]],
    land_limit_pct: float = 100.0,
    max_vegetation_pct: float = 40.0,
) -> float:
    """Compute theoretical upper bound of mean cooling achievable across zones ignoring water limit."""
    if not zones:
        return 0.0
    zone_max_coolings = []
    for p in zones:
        cap_ground = (
            0.0
            if p.get("protected", False)
            else float(p.get("available_land_pct", 0.0)) * (land_limit_pct / 100.0)
        )
        cap_roof = float(p.get("roof_pct", 0.0))
        cap_road = float(p.get("road_pct", 0.0))

        veg_cap = min(cap_ground, float(max_vegetation_pct))
        ground_cooling = (veg_cap / 10.0) * 0.35
        remaining_ground = max(0.0, cap_ground - veg_cap)
        ground_cooling += (remaining_ground / 10.0) * 0.20

        roof_cooling = (cap_roof / 10.0) * 0.28
        road_cooling = (cap_road / 10.0) * 0.18

        total_zone_cooling = min(3.0, ground_cooling + roof_cooling + road_cooling)
        zone_max_coolings.append(total_zone_cooling)

    return sum(zone_max_coolings) / len(zones)


def calculate_zero_water_cooling(zones: list[dict[str, Any]]) -> float:
    """Compute maximum mean cooling achievable using zero-water interventions (cool roofs & reflective pavements)."""
    if not zones:
        return 0.0
    zone_coolings = []
    for p in zones:
        cap_roof = float(p.get("roof_pct", 0.0))
        cap_road = float(p.get("road_pct", 0.0))
        cool = (cap_roof / 10.0) * 0.28 + (cap_road / 10.0) * 0.18
        zone_coolings.append(min(3.0, cool))
    return sum(zone_coolings) / len(zones)


def diagnose_infeasibility(
    zones: list[dict[str, Any]],
    water_limit: float,
    max_vegetation_pct: float,
    min_cooling: float,
    land_limit_pct: float,
    **kwargs: Any,
) -> list[str]:
    """Generate clear diagnostic warnings detailing why the constraints are infeasible."""
    violations = [
        "Requested minimum mean cooling is incompatible with land, roof, road, protection, vegetation, or water constraints."
    ]
    if not zones:
        violations.append("No zones were provided to optimize.")
        return violations

    n = len(zones)
    max_possible = calculate_max_possible_cooling(zones, land_limit_pct, max_vegetation_pct)

    if min_cooling > max_possible:
        violations.append(
            f"Physical capacity limitation: The requested minimum cooling of {min_cooling:.2f}°C exceeds "
            f"the theoretical maximum achievable ({max_possible:.2f}°C) given available ground ({land_limit_pct}% "
            f"limit), roof, and road surface capacities across the {n} selected zone(s)."
        )

    if water_limit < 0:
        violations.append(
            f"Water availability constraint: Negative water limit ({water_limit} m³/day) is mathematically impossible to satisfy."
        )
    elif water_limit <= 0 and min_cooling > 0:
        zero_water_max = calculate_zero_water_cooling(zones)
        if min_cooling > zero_water_max:
            violations.append(
                f"Water availability limitation: Zero daily water available ({water_limit} m³/day) prohibits "
                f"all vegetation, trees, and water cooling. Zero-water interventions (cool roofs and pavements) "
                f"can provide at most {zero_water_max:.2f}°C cooling."
            )
    elif water_limit < 100 and min_cooling > 0:
        violations.append(
            f"Water availability limitation: Severely constrained water limit ({water_limit:.0f} m³/day) "
            f"is insufficient to sustain the vegetative coverage required to achieve {min_cooling:.2f}°C cooling."
        )

    if max_vegetation_pct <= 0 and min_cooling > 0:
        violations.append(
            "Vegetation constraint: Added vegetation is prohibited (max_vegetation_pct=0%). "
            "High-cooling green interventions (trees, native vegetation, pocket parks) cannot be allocated."
        )

    if land_limit_pct <= 0:
        violations.append(
            "Land availability constraint: Ground area utilization is prohibited (land_limit_pct=0%). "
            "All ground interventions are excluded."
        )

    violations.append(
        "Recommendation: Lower the minimum cooling target (min_cooling), increase available water "
        "(water_limit), or relax land/vegetation constraints to achieve feasibility."
    )
    return violations


def optimize(
    zones: list[dict[str, Any]],
    water_limit: float = 1000.0,
    max_vegetation_pct: float = 40.0,
    min_cooling: float = 0.0,
    land_limit_pct: float = 100.0,
    include_alternative: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Find pareto-optimal intervention allocation across zones given physical, environmental, land & water limits.

    The OR-Tools CP-SAT model optimizes discrete 5-percentage-point decision variables
    subject to physical surface capacities (ground, roof, road), environmental limits
    (maximum vegetation, minimum mean cooling), land protection, roof mutual exclusivity,
    and municipal water availability. Cooling saturates at 3.0°C maximum.
    Financial budget constraints are completely removed.
    """
    water_limit = float(water_limit)
    max_vegetation_pct = float(max_vegetation_pct)
    min_cooling = float(min_cooling)
    land_limit_pct = float(land_limit_pct)

    if not zones:
        return {
            "status": "OPTIMAL",
            "feasible": True,
            "selections": [],
            "allocations": {},
            "spatial_priority_ranking": [],
            "spatial_priority_details": [],
            "violations": [],
            "water_used": 0.0,
            "total_water_used": 0.0,
            "water_available": float(water_limit),
            "water_limit": float(water_limit),
            "mean_cooling": 0.0,
            "total_cooling": 0.0,
            "population_in_selected_zones": 0,
            "hypothetical": True,
            "assumptions": ASSUMPTIONS,
            "objective": "Maximize hypothetical surface cooling weighted by population, synthetic elderly share, and surface heat. This is a prioritization proxy, not an estimate of people protected.",
            "explanation": "No zones provided for optimization.",
            "constraints": {
                "max_vegetation_pct": max_vegetation_pct,
                "land_limit_pct": land_limit_pct,
                "min_mean_cooling": min_cooling,
                "water_limit": water_limit,
            },
            "alternative": None,
            "sensitivity_50pct_water": None,
        }

    model = cp_model.CpModel()
    variables = {}
    cool_terms = []
    water_terms = []
    objectives = []
    zone_priorities = {}

    for p in zones:
        z = p["id"]
        local = {}
        area_km2 = float(p.get("area_km2", 1.0))
        for key, spec in INTERVENTIONS.items():
            surface = spec["surface"]
            cap = {
                "ground": float(p.get("available_land_pct", 0.0)) * land_limit_pct / 100.0,
                "roof": float(p.get("roof_pct", 0.0)),
                "road": float(p.get("road_pct", 0.0)),
            }[surface]
            if p.get("protected", False) and surface == "ground":
                cap = 0.0
            levels = model.NewIntVar(0, int(cap // 5), f"{z}-{key}")
            variables[(z, key)] = levels
            local[key] = levels
            water_terms.append(levels * int(round(5.0 * spec["water_per_pct"] * area_km2)))

        # Surface area capacity constraints (ground, roof, road)
        for surface in ["ground", "roof", "road"]:
            cap = {
                "ground": float(p.get("available_land_pct", 0.0)) * land_limit_pct / 100.0,
                "roof": float(p.get("roof_pct", 0.0)),
                "road": float(p.get("road_pct", 0.0)),
            }[surface]
            if p.get("protected", False) and surface == "ground":
                cap = 0.0
            model.Add(
                sum(
                    v * 5
                    for k, v in local.items()
                    if INTERVENTIONS[k]["surface"] == surface
                )
                <= int(cap)
            )

        # Vegetation ceiling constraint
        model.Add(
            sum(v * 5 for k, v in local.items() if INTERVENTIONS[k]["vegetation"])
            <= int(max_vegetation_pct)
        )

        # Roof mutual exclusivity: cool roofs and rooftop gardens cannot coexist in the same zone
        roof_kind = model.NewBoolVar(f"{z}-roof-kind")
        model.Add(local["cool_roofs"] == 0).OnlyEnforceIf(roof_kind)
        model.Add(local["roof_gardens"] == 0).OnlyEnforceIf(roof_kind.Not())

        # Cooling saturation: combined cooling saturates at 3.0°C (3000 milli-degrees) maximum
        raw = sum(
            v * round(INTERVENTIONS[k]["cooling_per_10pct"] * 500)
            for k, v in local.items()
        )
        cool = model.NewIntVar(0, 3000, f"{z}-cooling")
        model.AddMinEquality(cool, [raw, 3000])
        cool_terms.append(cool)

        # Equity-weighted heat-risk reduction and population protected priority
        # priority = population * (0.2 + elderly_share) * SUHII
        suhii = max(0.2, float(p.get("predicted_suhii", p.get("observed_suhii", 2.0))))
        population = float(p.get("population", 1000.0))
        elderly_share = float(p.get("elderly_share", 0.1))
        priority = max(
            1,
            round(
                population
                * (0.2 + elderly_share)
                * suhii
            ),
        )
        zone_priorities[z] = priority
        objectives.append(cool * priority)

    # Municipal water limit constraint
    model.Add(sum(water_terms) <= int(water_limit))

    # Target minimum mean cooling constraint
    model.Add(sum(cool_terms) >= math.ceil(min_cooling * 1000 * len(zones)))

    # Maximize equity-weighted heat-risk reduction
    model.Maximize(sum(objectives))

    solver = cp_model.CpSolver()
    status = safe_solve(solver, model, max_time_seconds=8.0)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        violations = (
            diagnose_infeasibility(
                zones,
                water_limit=water_limit,
                max_vegetation_pct=max_vegetation_pct,
                min_cooling=min_cooling,
                land_limit_pct=land_limit_pct,
            )
            if status == cp_model.INFEASIBLE
            else ["Solver time limit reached without a feasible solution."]
        )
        return {
            "status": solver.StatusName(status) if hasattr(solver, "StatusName") else "INFEASIBLE",
            "feasible": False,
            "selections": [],
            "allocations": {},
            "spatial_priority_ranking": [],
            "spatial_priority_details": [],
            "violations": violations,
            "water_used": 0.0,
            "total_water_used": 0.0,
            "water_available": float(water_limit),
            "water_limit": float(water_limit),
            "mean_cooling": 0.0,
            "total_cooling": 0.0,
            "population_in_selected_zones": 0,
            "hypothetical": True,
            "assumptions": ASSUMPTIONS,
            "objective": "Maximize hypothetical surface cooling weighted by population, synthetic elderly share, and surface heat. This is a prioritization proxy, not an estimate of people protected.",
            "explanation": "No feasible allocation satisfies the requested constraints.",
            "constraints": {
                "max_vegetation_pct": max_vegetation_pct,
                "land_limit_pct": land_limit_pct,
                "min_mean_cooling": min_cooling,
                "water_limit": water_limit,
            },
            "alternative": None,
            "sensitivity_50pct_water": None,
        }

    selections = []
    allocations = {}
    for p in zones:
        z_id = p["id"]
        coverage = {k: solver.Value(variables[(z_id, k)]) * 5 for k in INTERVENTIONS}
        coverage = {k: v for k, v in coverage.items() if v > 0}
        if coverage:
            allocations[z_id] = coverage
        result = simulate(
            p,
            coverage,
            water_limit=water_limit,
            max_vegetation_pct=max_vegetation_pct,
        )
        selections.append(
            {
                **result,
                "zone_name": p.get("name", z_id),
                "population": p.get("population", 0),
                "risk_score": risk(p)["risk_score"],
            }
        )

    water_used = sum(s["water_m3_day"] for s in selections)
    total_cooling = sum(s.get("estimated_cooling") or 0.0 for s in selections)
    mean_cooling = total_cooling / len(zones) if zones else 0.0

    # =========================================================================
    # Spatial Priority Plan Generation
    # Rank zones by equity-weighted heat-risk reduction and water efficiency
    # =========================================================================
    def calculate_priority_score(s: dict[str, Any]) -> float:
        z_id = s["zone_id"]
        cooling_val = s.get("estimated_cooling") or 0.0
        priority_weight = zone_priorities.get(z_id, 1)
        equity_impact = cooling_val * priority_weight
        water_req = s.get("water_m3_day", 0.0)
        # Higher equity impact and better water efficiency yield higher ranking
        return equity_impact + (equity_impact / max(1.0, water_req))

    # Zones with interventions ranked first by impact/efficiency, followed by remaining zones by risk score
    active_selections = [s for s in selections if s.get("coverage")]
    inactive_selections = [s for s in selections if not s.get("coverage")]

    sorted_active = sorted(active_selections, key=calculate_priority_score, reverse=True)
    sorted_inactive = sorted(inactive_selections, key=lambda s: s.get("risk_score", 0.0), reverse=True)
    full_sorted = sorted_active + sorted_inactive

    spatial_priority_ranking: list[str] = [s["zone_id"] for s in full_sorted]
    spatial_priority_details: list[dict[str, Any]] = [
        {
            "rank": rank_idx + 1,
            "zone_id": s["zone_id"],
            "zone_name": s.get("zone_name", s["zone_id"]),
            "cooling_achieved": s.get("estimated_cooling") or 0.0,
            "water_allocated_m3_day": s.get("water_m3_day", 0.0),
            "interventions": s.get("coverage", {}),
            "priority_score": round(calculate_priority_score(s), 2),
            "risk_score": s.get("risk_score", 0.0),
        }
        for rank_idx, s in enumerate(full_sorted)
    ]

    res: dict[str, Any] = {
        "status": solver.StatusName(status) if hasattr(solver, "StatusName") else "OPTIMAL",
        "feasible": True,
        "selections": selections,
        "allocations": allocations,
        "spatial_priority_ranking": spatial_priority_ranking,
        "spatial_priority_details": spatial_priority_details,
        "water_used": water_used,
        "total_water_used": water_used,
        "water_available": float(water_limit),
        "water_limit": float(water_limit),
        "total_cooling": round(total_cooling, 4),
        "mean_cooling": round(mean_cooling, 4),
        "population_in_selected_zones": sum(
            s["population"] for s in selections if s["coverage"]
        ),
        "violations": [],
        "hypothetical": True,
        "assumptions": ASSUMPTIONS,
        "objective": "Maximize hypothetical surface cooling weighted by population, synthetic elderly share, and surface heat. This is a prioritization proxy, not an estimate of people protected.",
        "explanation": "Selected 5-percentage-point increments with shared ground/roof/road capacities, protected-land exclusions, roof compatibility, total water, and land-availability limits.",
        "constraints": {
            "max_vegetation_pct": max_vegetation_pct,
            "land_limit_pct": land_limit_pct,
            "min_mean_cooling": min_cooling,
            "water_limit": water_limit,
        },
    }

    # =========================================================================
    # 50% Water Sensitivity Contingency Analysis
    # Assess resilience and cooling loss if municipal water drops by half
    # =========================================================================
    if include_alternative:
        alt = optimize(
            zones,
            water_limit=water_limit * 0.5,
            max_vegetation_pct=max_vegetation_pct,
            min_cooling=0.0,
            land_limit_pct=land_limit_pct,
            include_alternative=False,
        )
        res["alternative"] = {"label": "Half-water alternative", **alt}

        alt_mean_cooling = alt.get("mean_cooling", 0.0)
        cooling_loss = max(0.0, mean_cooling - alt_mean_cooling)
        retention_pct = (
            round((alt_mean_cooling / max(1e-6, mean_cooling)) * 100.0, 1)
            if mean_cooling > 0
            else 100.0
        )

        res["sensitivity_50pct_water"] = {
            "water_limit_50pct": round(water_limit * 0.5, 2),
            "water_used_50pct": round(alt.get("water_used", 0.0), 2),
            "mean_cooling_50pct": round(alt_mean_cooling, 4),
            "cooling_loss_celsius": round(cooling_loss, 4),
            "cooling_retention_pct": retention_pct,
            "vulnerable_population_impact": (
                f"Under a 50% municipal water reduction, mean cooling decreases by {cooling_loss:.2f}°C, "
                f"retaining {retention_pct:.1f}% of baseline equity-weighted heat resilience."
                if mean_cooling > 0
                else "Zero baseline cooling; unaffected by municipal water reduction."
            ),
            "allocations": alt.get("allocations", {}),
            "spatial_priority_ranking": alt.get("spatial_priority_ranking", []),
        }
    else:
        res["alternative"] = None
        res["sensitivity_50pct_water"] = None

    return res
