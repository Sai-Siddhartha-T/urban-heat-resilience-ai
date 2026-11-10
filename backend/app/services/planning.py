"""Literature-grounded urban heat intervention simulator.

Models microclimatic cooling effects, evapotranspiration water demands,
and environmental metric deltas (LST, NDVI, albedo, stormwater runoff reduction)
grounded in empirical urban climatology and microclimate literature.
Explicitly labels all outputs as hypothetical estimates separate from
predictive SHAP associations.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from app.services.risk import risk

# =============================================================================
# Literature-Grounded Interventions Catalog
# Grounded in empirical literature:
# - Bowler et al. (2010), Akbari et al. (2001, 2012), Santamouris (2014, 2017)
# - Gill et al. (2007), Oliveira et al. (2011), Coutts et al. (2016), Ferguson (2005)
# ZERO financial costs, budget parameters, or capex/opex variables.
# =============================================================================

INTERVENTIONS: Dict[str, Dict[str, Any]] = {
    "trees": {
        "name": "Urban trees",
        "surface": "ground",
        "cooling_per_10pct": 0.35,  # °C SUHII reduction per 10% zone area canopy
        "water_per_pct": 20,         # m³/day per 1% zone area per km²
        "vegetation": True,
        "cooling_uncertainty": (0.22, 0.48),  # Lower and upper bound cooling per 10%
        "ndvi_delta_per_10pct": 0.040,        # Expected NDVI increase per 10% coverage
        "albedo_delta_per_10pct": -0.005,     # Slight albedo drop due to dark foliage
        "runoff_reduction_pct_per_10pct": 6.0,# Stormwater interception & soil infiltration
        "cooling_mechanism": "Direct solar radiation interception (canopy shading) and leaf evapotranspiration",
        "citation": "Bowler et al. (2010); Akbari et al. (2001)",
    },
    "vegetation": {
        "name": "Native vegetation",
        "surface": "ground",
        "cooling_per_10pct": 0.25,
        "water_per_pct": 10,
        "vegetation": True,
        "cooling_uncertainty": (0.15, 0.35),
        "ndvi_delta_per_10pct": 0.035,
        "albedo_delta_per_10pct": 0.010,
        "runoff_reduction_pct_per_10pct": 4.5,
        "cooling_mechanism": "Ground-level evapotranspirative cooling and soil moisture retention",
        "citation": "Gill et al. (2007); Dimoudi & Nikolopoulou (2003)",
    },
    "parks": {
        "name": "Pocket parks",
        "surface": "ground",
        "cooling_per_10pct": 0.30,
        "water_per_pct": 15,
        "vegetation": True,
        "cooling_uncertainty": (0.18, 0.42),
        "ndvi_delta_per_10pct": 0.038,
        "albedo_delta_per_10pct": 0.008,
        "runoff_reduction_pct_per_10pct": 5.0,
        "cooling_mechanism": "Combined Park Cool Island (PCI) oasis effect with mixed turf and shade trees",
        "citation": "Oliveira et al. (2011); Chang et al. (2007)",
    },
    "cool_roofs": {
        "name": "Cool roofs",
        "surface": "roof",
        "cooling_per_10pct": 0.28,
        "water_per_pct": 0,
        "vegetation": False,
        "cooling_uncertainty": (0.18, 0.38),
        "ndvi_delta_per_10pct": 0.000,
        "albedo_delta_per_10pct": 0.050,      # Significant zone-averaged albedo increase
        "runoff_reduction_pct_per_10pct": 0.0,
        "cooling_mechanism": "High solar reflectance (albedo >= 0.70) and high thermal emittance (>= 0.85)",
        "citation": "Akbari et al. (2012); Santamouris (2014)",
    },
    "pavements": {
        "name": "Reflective pavements",
        "surface": "road",
        "cooling_per_10pct": 0.18,
        "water_per_pct": 0,
        "vegetation": False,
        "cooling_uncertainty": (0.10, 0.25),
        "ndvi_delta_per_10pct": 0.000,
        "albedo_delta_per_10pct": 0.030,
        "runoff_reduction_pct_per_10pct": 4.0,# Permeable pavement porous base water infiltration
        "cooling_mechanism": "High-albedo pavement coating and permeable structure evaporative infiltration",
        "citation": "Santamouris et al. (2012); Ferguson (2005)",
    },
    "corridors": {
        "name": "Green corridors",
        "surface": "ground",
        "cooling_per_10pct": 0.32,
        "water_per_pct": 15,
        "vegetation": True,
        "cooling_uncertainty": (0.20, 0.44),
        "ndvi_delta_per_10pct": 0.040,
        "albedo_delta_per_10pct": 0.010,
        "runoff_reduction_pct_per_10pct": 5.0,
        "cooling_mechanism": "Linear advective ventilation and continuous vegetative shade pathways",
        "citation": "Coutts et al. (2016); Norton et al. (2015)",
    },
    "roof_gardens": {
        "name": "Rooftop gardens",
        "surface": "roof",
        "cooling_per_10pct": 0.22,
        "water_per_pct": 12,
        "vegetation": True,
        "cooling_uncertainty": (0.14, 0.30),
        "ndvi_delta_per_10pct": 0.030,
        "albedo_delta_per_10pct": 0.020,
        "runoff_reduction_pct_per_10pct": 7.0,# Rooftop stormwater detention and retention
        "cooling_mechanism": "Building envelope thermal insulation, altered roof albedo, and plant evapotranspiration",
        "citation": "Santamouris (2014); Berardi et al. (2014)",
    },
    "water": {
        "name": "Water-based cooling",
        "surface": "ground",
        "cooling_per_10pct": 0.20,
        "water_per_pct": 40,
        "vegetation": False,
        "cooling_uncertainty": (0.12, 0.28),
        "ndvi_delta_per_10pct": 0.000,
        "albedo_delta_per_10pct": 0.000,
        "runoff_reduction_pct_per_10pct": 2.0,
        "cooling_mechanism": "High thermal inertia and direct latent heat absorption via evaporative water bodies",
        "citation": "Theeuwes et al. (2013); Manteghi et al. (2015)",
    },
}

# Empirical literature references
LITERATURE_REFERENCES: List[Dict[str, str]] = [
    {
        "citation": "Bowler, D. E., Buyung-Ali, L., Knight, T. M., & Pullin, A. S. (2010). Urban greening to cool towns and cities: A systematic review of the empirical evidence. Landscape and Urban Planning, 97(3), 147-155.",
        "key_finding": "Tree canopy provides an average 0.3°C to 0.5°C cooling per 10% canopy cover via shade and transpiration.",
    },
    {
        "citation": "Akbari, H., Pomerantz, M., & Taha, H. (2001). Cool surfaces and shade trees to reduce energy use and improve air quality in urban areas. Solar Energy, 70(3), 295-310.",
        "key_finding": "Increasing roof albedo by 0.40 and planting 3 trees per house reduces cooling energy demand and lowers air temperatures by 0.5-1.5°C.",
    },
    {
        "citation": "Santamouris, M. (2014). Cooling the cities—a review of reflective and green roof mitigation technologies to fight heat island and improve comfort in urban environments. Solar Energy, 103, 682-703.",
        "key_finding": "Reflective cool roofs lower ambient urban temperature by 0.15-0.3°C per 10% roof albedo increase without water consumption.",
    },
    {
        "citation": "Gill, S. E., Handley, J. F., Ennos, A. R., & Pauleit, S. (2007). Adapting cities for climate change: the role of the green infrastructure. Built Environment, 33(1), 115-133.",
        "key_finding": "Adding 10% green cover in high-density residential areas keeps maximum surface temperatures at baseline under climate warming.",
    },
    {
        "citation": "Ferguson, B. K. (2005). Porous Pavements. CRC Press.",
        "key_finding": "Permeable and porous pavements mitigate urban heat via evaporative cooling and reduce peak stormwater runoff by 40-80%.",
    },
]

# Canonical assumed crown area used to convert tree counts into zone-area coverage
CANOPY_M2_PER_TREE: float = 28.0

ASSUMPTIONS: List[str] = [
    "Literature-grounded microclimatic cooling coefficients derived from empirical meta-analyses (Bowler 2010, Santamouris 2014, Akbari 2001).",
    "Coverage represents percentage points of total zone surface area, not isolated portions of individual parcels.",
    "Combined cooling combines additively up to a 3.0°C microclimatic saturation ceiling, reflecting physical boundary layer feedback limits.",
    "Uncertainty ranges represent climatological upper and lower bounds based on urban density, building aspect ratio, and atmospheric humidity.",
    "Water consumption represents estimated daily municipal irrigation requirements in m³/day per percentage point coverage per km².",
    "Tree canopy conversions use a canonical 28.0 m² mature crown area (equivalent to a ~6m diameter canopy).",
    "Roof and road treatments are converted to zone-area coverage based on each zone's specific roof and road area proportions.",
    "All intervention scenarios are explicitly labelled as hypothetical climatological estimates and must be verified with site-level microclimate modeling (e.g. ENVI-met).",
]


def apply_convenience(
    zone: Dict[str, Any],
    coverage: Dict[str, float],
    tree_count: Optional[int] = None,
    roof_treated_pct: Optional[float] = None,
    road_treated_pct: Optional[float] = None,
) -> Tuple[Dict[str, float], List[str]]:
    """Translate planner-facing counts into the simulator's zone-area percentages.

    Args:
        zone: Zone properties dictionary containing area_km2, roof_pct, road_pct.
        coverage: Base intervention coverage dictionary.
        tree_count: Optional absolute number of mature trees to plant.
        roof_treated_pct: Optional percentage of existing roofs to treat with cool roofs.
        road_treated_pct: Optional percentage of existing roads to treat with reflective pavements.

    Returns:
        Tuple of (converted coverage dict, conversion explanation notes).
    """
    converted = dict(coverage)
    notes: List[str] = []
    area_m2 = float(zone.get("area_km2", 1.0)) * 1_000_000.0

    if tree_count is not None:
        if area_m2 <= 0:
            raise ValueError("Zone area must be positive to convert a tree count.")
        percent = (float(tree_count) * CANOPY_M2_PER_TREE / area_m2) * 100.0
        if percent > 100.0:
            raise ValueError(
                f"{tree_count} trees at {CANOPY_M2_PER_TREE:.0f} m² each exceed this zone. "
                "Reduce the count; the crown size is an assumption, not a measured canopy."
            )
        converted["trees"] = percent
        notes.append(
            f"{tree_count} trees converted with an assumed {CANOPY_M2_PER_TREE:.0f} m² crown "
            f"to {percent:.2f}% of zone area."
        )

    if roof_treated_pct is not None:
        percent = (float(roof_treated_pct) / 100.0) * float(zone.get("roof_pct", 0.0))
        converted["cool_roofs"] = percent
        notes.append(
            f"{roof_treated_pct:.1f}% of existing roofs converts to {percent:.2f}% of zone area "
            "and is applied to cool roofs."
        )

    if road_treated_pct is not None:
        percent = (float(road_treated_pct) / 100.0) * float(zone.get("road_pct", 0.0))
        converted["pavements"] = percent
        notes.append(
            f"{road_treated_pct:.1f}% of existing roads converts to {percent:.2f}% of zone area "
            "and is applied to reflective pavements."
        )

    return converted, notes


def simulate(
    p: Dict[str, Any],
    coverage: Dict[str, float],
    water_limit: float = 1000.0,
    max_vegetation_pct: float = 40.0,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Simulate cooling potential, water consumption, and environmental metric deltas.

    Evaluates physical feasibility against ground, roof, and road capacities,
    protected status, roof exclusivity, vegetation ceiling, and water limits.
    Calculates literature-grounded cooling with uncertainty bounds and metric deltas.

    Args:
        p: Zone properties dictionary.
        coverage: Map of intervention names to percentage point coverage.
        water_limit: Maximum daily municipal water allocation in m³/day.
        max_vegetation_pct: Maximum allowed vegetative intervention percentage.

    Returns:
        Structured simulation response dictionary.
    """
    violations: List[str] = []
    totals = {"ground": 0.0, "roof": 0.0, "road": 0.0}
    water = 0.0
    cooling_raw = 0.0
    cooling_lower_raw = 0.0
    cooling_upper_raw = 0.0
    vegetation = 0.0

    total_ndvi_delta = 0.0
    total_albedo_delta = 0.0
    total_runoff_reduction = 0.0

    area_km2 = float(p.get("area_km2", 1.0))

    for key, pct_val in coverage.items():
        if key not in INTERVENTIONS:
            raise ValueError(f"Unknown intervention '{key}'.")
        pct = float(pct_val)
        if not math.isfinite(pct) or pct < 0.0 or pct > 100.0:
            raise ValueError("Coverage must be finite and between 0 and 100.")
        if pct == 0.0:
            continue

        spec = INTERVENTIONS[key]
        totals[spec["surface"]] += pct
        water += pct * spec["water_per_pct"] * area_km2
        
        # Base cooling
        cooling_raw += (pct / 10.0) * spec["cooling_per_10pct"]
        
        # Uncertainty bounds based on empirical literature ranges
        u_lower, u_upper = spec.get("cooling_uncertainty", (spec["cooling_per_10pct"] * 0.7, spec["cooling_per_10pct"] * 1.3))
        cooling_lower_raw += (pct / 10.0) * u_lower
        cooling_upper_raw += (pct / 10.0) * u_upper

        if spec["vegetation"]:
            vegetation += pct

        # Metric deltas
        total_ndvi_delta += (pct / 10.0) * spec.get("ndvi_delta_per_10pct", 0.0)
        total_albedo_delta += (pct / 10.0) * spec.get("albedo_delta_per_10pct", 0.0)
        total_runoff_reduction += (pct / 10.0) * spec.get("runoff_reduction_pct_per_10pct", 0.0)

    # Physical Surface Capacities
    capacities = {
        "ground": float(p.get("available_land_pct", 0.0)),
        "roof": float(p.get("roof_pct", 0.0)),
        "road": float(p.get("road_pct", 0.0)),
    }

    for surface, total in totals.items():
        if total > capacities[surface] + 1e-6:
            violations.append(
                f"{surface.title()} coverage exceeds available land area ({capacities[surface]:.1f}%)."
                if surface == "ground"
                else f"{surface.title()} coverage exceeds available area ({capacities[surface]:.1f}%)."
            )

    # Protected zone prohibition on ground interventions
    if p.get("protected", False) and totals["ground"] > 0:
        violations.append("Protected zone prohibits ground interventions.")

    # Mutual exclusivity of cool roofs and rooftop gardens
    if coverage.get("cool_roofs", 0) > 0 and coverage.get("roof_gardens", 0) > 0:
        violations.append(
            "Cool roofs and rooftop gardens are mutually exclusive in this prototype."
        )

    # Vegetation ceiling constraint
    if vegetation > max_vegetation_pct + 1e-6:
        violations.append("Added vegetation exceeds the configured maximum.")

    # Water limit constraint
    if water > float(water_limit) + 1e-6:
        violations.append("Daily water requirement exceeds the available water.")

    # Physical 3.0°C cooling saturation curve
    cooling = min(3.0, cooling_raw)
    cooling_lower = min(3.0, cooling_lower_raw)
    cooling_upper = min(3.0, cooling_upper_raw)

    before = float(p.get("predicted_suhii", p.get("observed_suhii", 2.0)))
    after = before - cooling

    is_feasible = len(violations) == 0

    # Literature-grounded metric deltas:
    # LST delta: Surface LST decreases ~1.25x more than near-surface air temperature (SUHII)
    # NDVI delta: Vegetative index increase
    # Albedo delta: Zone-averaged solar reflectance change
    # Runoff reduction: Percentage reduction in peak urban stormwater runoff
    metrics_delta = {
        "lst_delta_celsius": round(-1.25 * cooling, 3) if is_feasible else 0.0,
        "suhii_delta_celsius": round(-cooling, 3) if is_feasible else 0.0,
        "ndvi_delta": round(total_ndvi_delta, 4) if is_feasible else 0.0,
        "albedo_delta": round(total_albedo_delta, 4) if is_feasible else 0.0,
        "runoff_reduction_pct": round(min(100.0, total_runoff_reduction), 2) if is_feasible else 0.0,
    }

    return {
        "zone_id": p.get("id", "unknown-zone"),
        "coverage": coverage,
        "feasible": is_feasible,
        "violations": violations,
        "warnings": list(violations),
        "before_suhii": before,
        "after_suhii": after if is_feasible else None,
        "estimated_cooling": cooling if is_feasible else None,
        "cooling_celsius": cooling if is_feasible else None,
        # Backward compatibility sensitivity range (±40%)
        "sensitivity_range": [cooling * 0.6, cooling * 1.4] if is_feasible else None,
        # Explicit climatology uncertainty range
        "uncertainty_range": [round(cooling_lower, 3), round(cooling_upper, 3)] if is_feasible else None,
        "water_m3_day": water,
        "metrics_delta": metrics_delta,
        "area_coverage": totals,
        # Prominent hypothetical estimate labelling
        "hypothetical": True,
        "estimate_label": "Hypothetical Climatological Estimate (Literature-Grounded)",
        "disclaimer": (
            "Scenario cooling and water metrics are hypothetical estimates grounded in urban climatology literature. "
            "They represent potential microclimatic shifts and must be validated through site-specific microclimate "
            "modeling (e.g. ENVI-met) and municipal engineering assessments before implementation."
        ),
        "assumptions": ASSUMPTIONS,
        "literature_citations": [ref["citation"] for ref in LITERATURE_REFERENCES],
    }


# Re-export optimize from dedicated optimization service for backwards compatibility via PEP 562
def __getattr__(name: str):
    if name == "optimize":
        from app.services.optimization import optimize
        globals()["optimize"] = optimize
        return optimize
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
