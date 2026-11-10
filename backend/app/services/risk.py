"""Parametric climate heat risk calculation using the IPCC AR5/AR6 framework.

Heat Risk = Hazard × Exposure × Vulnerability
Where:
  - Hazard: Multi-factor composite index combining:
      * Surface heat / SUHII relative to 8.0 °C reference cap
      * Ambient air temperature relative to climatological baseline (28-45 °C)
      * Heatwave duration (consecutive days above local threshold / 7 days)
  - Exposure: Multi-factor composite index combining:
      * Population density relative to 25,000 per km²
      * Built-up / residential density (from GHSL or building footprint fraction)
      * Sensitive land-use indicators (schools, hospitals, informal settlements)
  - Vulnerability: Multidimensional heat sensitivity (strictly socioeconomic & demographic,
    never substituting population density):
      * Age structure: Elderly share (age 65+) and child share (<5 and 0-14)
      * Socioeconomic deprivation: Poverty rate, informal housing %, outdoor workers
      * Adaptive capacity / cooling deficit: Lack of tree canopy, lack of indoor cooling/AC
All components are bounded in [0, 1].
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

# Hazard normalization thresholds
HAZARD_MAX_SUHII: float = 8.0  # °C
HAZARD_AIR_BASELINE_TEMP: float = 28.0  # °C (climatological heat onset)
HAZARD_AIR_EXTREME_TEMP: float = 45.0  # °C (extreme heat cap)
HAZARD_MAX_HEATWAVE_DAYS: float = 7.0  # days (consecutive heatwave duration)

# Exposure normalization thresholds
EXPOSURE_MAX_DENSITY: float = 25000.0  # people/km²
EXPOSURE_MAX_BUILT_UP: float = 1.0  # built-up surface fraction [0, 1]
EXPOSURE_MAX_SENSITIVE_SCORE: float = 1.0  # sensitive land-use index [0, 1]

# Vulnerability normalization thresholds
VULNERABILITY_MAX_ELDERLY_SHARE: float = 0.25  # age 65+
VULNERABILITY_MAX_CHILDREN_SHARE: float = 0.30  # age 0-14
VULNERABILITY_MAX_CHILD_UNDER_5_SHARE: float = 0.12  # age < 5

RISK_HIGH_THRESHOLD: float = 20.0
RISK_MODERATE_THRESHOLD: float = 8.0

DEFAULT_WEIGHTS: Tuple[float, float, float] = (1.0, 1.0, 1.0)

MISSING_INDICATORS: List[str] = [
    "Socioeconomic status",
    "Health conditions",
    "Access to cooling",
]

METHOD_DESCRIPTION: str = (
    "100 × (SUHII / 8)^wH × (population/km² / 25000)^wE × (elderly share / .25)^wV; "
    "components clipped to [0,1]. Synthetic age share is a limited vulnerability proxy."
)

METHOD_DECOMPOSED_DESCRIPTION: str = (
    "100 × (Hazard)^wH × (Exposure)^wE × (Vulnerability)^wV; "
    "Hazard decomposes Surface SUHII, Ambient Air Temp, and Heatwave Duration. "
    "Exposure decomposes Population Density, Built-Up Density, and Sensitive Land Use. "
    "Vulnerability decomposes Age Sensitivity, Socioeconomic Deprivation, and Cooling Deficits. "
    "All sub-indices clipped to [0, 1]."
)


# ---------------------------------------------------------------------------
# 1. Multi-Factor Hazard Decomposition
# ---------------------------------------------------------------------------

def calculate_hazard(
    suhii_or_props: Union[float, int, str, Mapping[str, Any], Dict[str, Any]],
    air_temperature: Optional[float] = None,
    heatwave_duration: Optional[float] = None,
    rural_reference: Optional[float] = None,
    surface_weight: float = 0.50,
    air_weight: float = 0.30,
    duration_weight: float = 0.20,
) -> float:
    """Calculate normalized heat hazard score in [0, 1].

    Decomposes hazard into a composite index combining:
      1. Surface heat / SUHII relative to the 8.0 °C reference cap
      2. Ambient air temperature relative to [28.0 °C, 45.0 °C]
      3. Heatwave duration (consecutive days above threshold / 7.0 days)

    Maintains 100% backward compatibility when only SUHII is provided.
    """
    if isinstance(suhii_or_props, Mapping):
        p = suhii_or_props
        raw_suhii = p.get("predicted_suhii")
        if raw_suhii is None:
            raw_suhii = p.get("observed_suhii")
        if raw_suhii is None:
            raw_suhii = p.get("suhii")
        if raw_suhii is None and "lst" in p:
            ref = rural_reference if rural_reference is not None else p.get("rural_reference", 33.0)
            try:
                raw_suhii = float(p["lst"]) - float(ref)
            except (TypeError, ValueError):
                raw_suhii = 2.0
        if raw_suhii is None:
            raw_suhii = 2.0

        raw_air = (
            p.get("air_temperature")
            or p.get("air_temp")
            or p.get("ambient_temperature")
            or p.get("temp_max")
            or air_temperature
        )
        raw_dur = (
            p.get("heatwave_duration")
            or p.get("heatwave_days")
            or p.get("consecutive_heatwave_days")
            or p.get("heatwave_duration_days")
            or heatwave_duration
        )
    else:
        raw_suhii = suhii_or_props
        raw_air = air_temperature
        raw_dur = heatwave_duration

    # 1. Surface heat / SUHII component
    try:
        val_suhii = float(raw_suhii)
        if not math.isfinite(val_suhii):
            h_surface = 0.0
        else:
            h_surface = min(1.0, max(0.0, val_suhii / HAZARD_MAX_SUHII))
    except (TypeError, ValueError):
        h_surface = 0.0

    # 2. Ambient air temperature component
    h_air: Optional[float] = None
    if raw_air is not None:
        try:
            val_air = float(raw_air)
            if math.isfinite(val_air):
                h_air = min(
                    1.0,
                    max(0.0, (val_air - HAZARD_AIR_BASELINE_TEMP) / (HAZARD_AIR_EXTREME_TEMP - HAZARD_AIR_BASELINE_TEMP)),
                )
        except (TypeError, ValueError):
            h_air = None

    # 3. Heatwave duration component
    h_dur: Optional[float] = None
    if raw_dur is not None:
        try:
            val_dur = float(raw_dur)
            if math.isfinite(val_dur):
                h_dur = min(1.0, max(0.0, val_dur / HAZARD_MAX_HEATWAVE_DAYS))
        except (TypeError, ValueError):
            h_dur = None

    # Multi-factor weighting synthesis
    if h_air is not None and h_dur is not None:
        total_w = surface_weight + air_weight + duration_weight
        score = (surface_weight * h_surface + air_weight * h_air + duration_weight * h_dur) / max(total_w, 1e-4)
    elif h_air is not None:
        score = 0.60 * h_surface + 0.40 * h_air
    elif h_dur is not None:
        score = 0.70 * h_surface + 0.30 * h_dur
    else:
        # Backward-compatible baseline when only SUHII is provided
        score = h_surface

    return round(min(1.0, max(0.0, score)), 4)


def decompose_hazard(
    suhii_or_props: Union[float, int, str, Mapping[str, Any], Dict[str, Any]],
    air_temperature: Optional[float] = None,
    heatwave_duration: Optional[float] = None,
    rural_reference: Optional[float] = None,
) -> Dict[str, Any]:
    """Provide detailed hazard component breakdown with physical units."""
    if isinstance(suhii_or_props, Mapping):
        p = suhii_or_props
        suhii_val = p.get("predicted_suhii", p.get("observed_suhii", p.get("suhii", 0.0)))
        air_val = p.get("air_temperature", p.get("air_temp", air_temperature))
        dur_val = p.get("heatwave_duration", p.get("heatwave_days", heatwave_duration))
    else:
        suhii_val = suhii_or_props
        air_val = air_temperature
        dur_val = heatwave_duration

    hazard_score = calculate_hazard(
        suhii_val,
        air_temperature=air_val,
        heatwave_duration=dur_val,
        rural_reference=rural_reference,
    )

    try:
        s_norm = min(1.0, max(0.0, float(suhii_val) / HAZARD_MAX_SUHII)) if suhii_val is not None and math.isfinite(float(suhii_val)) else 0.0
    except (TypeError, ValueError):
        s_norm = 0.0

    a_norm = None
    if air_val is not None:
        try:
            a_f = float(air_val)
            if math.isfinite(a_f):
                a_norm = min(1.0, max(0.0, (a_f - HAZARD_AIR_BASELINE_TEMP) / (HAZARD_AIR_EXTREME_TEMP - HAZARD_AIR_BASELINE_TEMP)))
        except (TypeError, ValueError):
            pass

    d_norm = None
    if dur_val is not None:
        try:
            d_f = float(dur_val)
            if math.isfinite(d_f):
                d_norm = min(1.0, max(0.0, d_f / HAZARD_MAX_HEATWAVE_DAYS))
        except (TypeError, ValueError):
            pass

    return {
        "hazard_score": hazard_score,
        "surface_heat": {
            "value_celsius": float(suhii_val) if suhii_val is not None and math.isfinite(float(suhii_val)) else 0.0,
            "normalized": round(s_norm, 4),
            "cap_celsius": HAZARD_MAX_SUHII,
        },
        "air_temperature": {
            "value_celsius": float(air_val) if a_norm is not None else None,
            "normalized": round(a_norm, 4) if a_norm is not None else None,
            "baseline_celsius": HAZARD_AIR_BASELINE_TEMP,
            "extreme_celsius": HAZARD_AIR_EXTREME_TEMP,
        },
        "heatwave_duration": {
            "value_days": float(dur_val) if d_norm is not None else None,
            "normalized": round(d_norm, 4) if d_norm is not None else None,
            "max_days": HAZARD_MAX_HEATWAVE_DAYS,
        },
        "units": {
            "surface_heat": "°C (relative to rural reference)",
            "air_temperature": "°C (ambient)",
            "heatwave_duration": "consecutive days > local heat threshold",
        },
    }


# ---------------------------------------------------------------------------
# 2. Multi-Factor Exposure Decomposition
# ---------------------------------------------------------------------------

def calculate_exposure(
    population_or_props: Union[float, int, str, Mapping[str, Any], Dict[str, Any]],
    building_density: Optional[float] = None,
    sensitive_land_use: Optional[float] = None,
    pop_weight: float = 0.50,
    built_weight: float = 0.30,
    sensitive_weight: float = 0.20,
) -> float:
    """Calculate normalized heat exposure score in [0, 1].

    Combines:
      1. Human population density relative to 25,000 people/km²
      2. Residential building density / built-up surface fraction (from GHSL or building footprint %)
      3. Sensitive land-use indicators (schools, hospitals, informal settlements)

    Maintains 100% backward compatibility when only population density is provided.
    """
    if isinstance(population_or_props, Mapping):
        p = population_or_props
        nested_demo = p.get("demographics") if isinstance(p.get("demographics"), Mapping) else {}

        raw_pop = p.get("population_density")
        if raw_pop is None:
            raw_pop = nested_demo.get("population_density")
        if raw_pop is None and "population" in p and "area_km2" in p:
            try:
                area = float(p["area_km2"])
                if area > 0:
                    raw_pop = float(p["population"]) / area
            except (TypeError, ValueError):
                raw_pop = 0.0

        raw_built = (
            p.get("building_density")
            or p.get("built_up_density")
            or p.get("residential_density")
            or p.get("ghsl_built_surface")
            or p.get("built_up_fraction")
            or p.get("building_footprint_pct")
            or building_density
        )

        raw_sens = (
            p.get("sensitive_land_use")
            or p.get("sensitive_infrastructure")
            or p.get("proximity_sensitive_facilities")
            or sensitive_land_use
        )
        if raw_sens is None:
            # Derive sensitive land use from institutional counts or informal settlements if present
            schools = p.get("schools_count") or nested_demo.get("schools_count")
            hospitals = p.get("hospitals_count") or nested_demo.get("hospitals_count")
            sens_fac = p.get("sensitive_facilities_count") or nested_demo.get("sensitive_facilities_count")
            if sens_fac is not None:
                try:
                    raw_sens = min(1.0, float(sens_fac) / 10.0)
                except (TypeError, ValueError):
                    pass
            elif schools is not None or hospitals is not None:
                try:
                    s_c = float(schools or 0.0)
                    h_c = float(hospitals or 0.0)
                    raw_sens = min(1.0, (s_c * 0.05 + h_c * 0.10))
                except (TypeError, ValueError):
                    pass
    else:
        raw_pop = population_or_props
        raw_built = building_density
        raw_sens = sensitive_land_use

    # 1. Population density component
    try:
        val_pop = float(raw_pop)
        if not math.isfinite(val_pop):
            e_pop = 0.0
        else:
            e_pop = min(1.0, max(0.0, val_pop / EXPOSURE_MAX_DENSITY))
    except (TypeError, ValueError):
        e_pop = 0.0

    # 2. Built-up surface / residential building density component
    e_built: Optional[float] = None
    if raw_built is not None:
        try:
            val_built = float(raw_built)
            if math.isfinite(val_built):
                # Normalize percentage to proportion if needed
                b_norm = val_built / 100.0 if val_built > 1.0 else val_built
                e_built = min(1.0, max(0.0, b_norm))
        except (TypeError, ValueError):
            e_built = None

    # 3. Sensitive land-use component
    e_sens: Optional[float] = None
    if raw_sens is not None:
        try:
            val_sens = float(raw_sens)
            if math.isfinite(val_sens):
                s_norm = val_sens / 100.0 if val_sens > 1.0 else val_sens
                e_sens = min(1.0, max(0.0, s_norm))
        except (TypeError, ValueError):
            e_sens = None

    # Multi-factor weighting synthesis
    if e_built is not None and e_sens is not None:
        total_w = pop_weight + built_weight + sensitive_weight
        score = (pop_weight * e_pop + built_weight * e_built + sensitive_weight * e_sens) / max(total_w, 1e-4)
    elif e_built is not None:
        score = 0.65 * e_pop + 0.35 * e_built
    elif e_sens is not None:
        score = 0.70 * e_pop + 0.30 * e_sens
    else:
        # Backward-compatible baseline when only population density is provided
        score = e_pop

    return round(min(1.0, max(0.0, score)), 4)


def decompose_exposure(
    population_or_props: Union[float, int, str, Mapping[str, Any], Dict[str, Any]],
    building_density: Optional[float] = None,
    sensitive_land_use: Optional[float] = None,
) -> Dict[str, Any]:
    """Provide detailed exposure component breakdown with physical units."""
    if isinstance(population_or_props, Mapping):
        p = population_or_props
        pop_val = p.get("population_density")
        built_val = p.get("building_density", p.get("built_up_density", building_density))
        sens_val = p.get("sensitive_land_use", sensitive_land_use)
    else:
        pop_val = population_or_props
        built_val = building_density
        sens_val = sensitive_land_use

    exposure_score = calculate_exposure(
        pop_val,
        building_density=built_val,
        sensitive_land_use=sens_val,
    )

    try:
        p_norm = min(1.0, max(0.0, float(pop_val) / EXPOSURE_MAX_DENSITY)) if pop_val is not None and math.isfinite(float(pop_val)) else 0.0
    except (TypeError, ValueError):
        p_norm = 0.0

    b_norm = None
    if built_val is not None:
        try:
            b_f = float(built_val)
            if math.isfinite(b_f):
                b_norm = min(1.0, max(0.0, b_f / 100.0 if b_f > 1.0 else b_f))
        except (TypeError, ValueError):
            pass

    s_norm = None
    if sens_val is not None:
        try:
            s_f = float(sens_val)
            if math.isfinite(s_f):
                s_norm = min(1.0, max(0.0, s_f / 100.0 if s_f > 1.0 else s_f))
        except (TypeError, ValueError):
            pass

    return {
        "exposure_score": exposure_score,
        "population_density": {
            "value_people_km2": float(pop_val) if pop_val is not None and math.isfinite(float(pop_val)) else 0.0,
            "normalized": round(p_norm, 4),
            "cap_people_km2": EXPOSURE_MAX_DENSITY,
        },
        "built_up_density": {
            "value_fraction": round(b_norm, 4) if b_norm is not None else None,
            "normalized": round(b_norm, 4) if b_norm is not None else None,
        },
        "sensitive_land_use": {
            "value_score": round(s_norm, 4) if s_norm is not None else None,
            "normalized": round(s_norm, 4) if s_norm is not None else None,
        },
        "units": {
            "population_density": "people/km²",
            "built_up_density": "fraction of surface area [0, 1]",
            "sensitive_land_use": "composite proximity/facility score [0, 1]",
        },
    }


# ---------------------------------------------------------------------------
# 3. Vulnerability Integrity (Socioeconomic & Demographic, Never Population)
# ---------------------------------------------------------------------------

def calculate_vulnerability(
    elderly_or_props: Union[float, Mapping[str, Any], Dict[str, Any]],
    children_share: Optional[float] = None,
    poverty_rate: Optional[float] = None,
    cooling_deficit: Optional[float] = None,
    informal_housing_pct: Optional[float] = None,
    outdoor_worker_share: Optional[float] = None,
    child_share_under_5: Optional[float] = None,
    tree_canopy_pct: Optional[float] = None,
) -> float:
    """Calculate normalized heat vulnerability score in [0, 1].

    INTEGRITY MANDATE:
    DO NOT substitute population density for vulnerability.
    Vulnerability is strictly an index composed of:
      1. Age sensitivity: Elderly share (>65) and child share (<5 or <14)
      2. Socioeconomic deprivation: Poverty rate, informal housing %, outdoor worker share
      3. Adaptive capacity / cooling deficit: Lack of tree canopy, lack of indoor cooling/AC

    Supports both legacy signature `calculate_vulnerability(elderly_share: float)`
    and dictionary-based property inputs containing multidimensional indicators.
    """
    if isinstance(elderly_or_props, Mapping):
        p = elderly_or_props
        nested_demo = p.get("demographics") if isinstance(p.get("demographics"), Mapping) else {}
        age_groups = nested_demo.get("age_groups") if isinstance(nested_demo.get("age_groups"), Mapping) else {}
        socio_dict = (
            nested_demo.get("socioeconomic_indicators")
            or nested_demo.get("socioeconomic_data")
            or p.get("socioeconomic_data")
            or {}
        )

        e_share = p.get("elderly_share")
        if e_share is None:
            e_share = nested_demo.get("elderly_share")
        if e_share is None:
            e_share = age_groups.get("elderly_share", 0.0)
        try:
            elderly = max(0.0, float(e_share)) if e_share is not None and math.isfinite(float(e_share)) else 0.0
        except (TypeError, ValueError):
            elderly = 0.0

        # Child under 5 sensitivity
        c_u5 = (
            p.get("child_share_under_5")
            or p.get("children_under_5")
            or p.get("children_under_5_share")
            or nested_demo.get("children_under_5_share")
            or age_groups.get("children_under_5_share")
            or child_share_under_5
        )
        try:
            children_under_5 = max(0.0, float(c_u5)) if c_u5 is not None and math.isfinite(float(c_u5)) else None
        except (TypeError, ValueError):
            children_under_5 = None

        # General children share (0-14)
        c_share = p.get("children_share")
        if c_share is None:
            c_share = nested_demo.get("children_share")
        if c_share is None:
            c_share = age_groups.get("children_share")
        if c_share is None:
            c_share = children_share
        try:
            children = max(0.0, float(c_share)) if c_share is not None and math.isfinite(float(c_share)) else None
        except (TypeError, ValueError):
            children = None

        pov = (
            p.get("poverty_rate")
            or nested_demo.get("poverty_rate")
            or socio_dict.get("poverty_rate")
            or p.get("socioeconomic_vulnerability")
            or nested_demo.get("socioeconomic_vulnerability")
        )
        if pov is None:
            pov = poverty_rate
        try:
            poverty = float(pov) if pov is not None and math.isfinite(float(pov)) else None
        except (TypeError, ValueError):
            poverty = None

        inf = p.get("informal_housing_pct") or nested_demo.get("informal_housing_pct") or socio_dict.get("informal_housing_pct")
        if inf is None:
            inf = informal_housing_pct
        try:
            informal = float(inf) if inf is not None and math.isfinite(float(inf)) else None
        except (TypeError, ValueError):
            informal = None

        out = p.get("outdoor_worker_share") or nested_demo.get("outdoor_worker_share") or socio_dict.get("outdoor_worker_share")
        if out is None:
            out = outdoor_worker_share
        try:
            outdoor = float(out) if out is not None and math.isfinite(float(out)) else None
        except (TypeError, ValueError):
            outdoor = None

        # Indoor cooling access / deficit
        cool_def = p.get("cooling_deficit") or nested_demo.get("cooling_deficit") or socio_dict.get("cooling_deficit")
        cool_acc = (
            p.get("cooling_access")
            or p.get("cooling_access_pct")
            or nested_demo.get("cooling_access_pct")
            or socio_dict.get("cooling_access_pct")
        )
        c_deficit = None
        if cool_def is not None:
            try:
                c_deficit = float(cool_def) if math.isfinite(float(cool_def)) else None
            except (TypeError, ValueError):
                pass
        elif cool_acc is not None:
            try:
                ca = float(cool_acc)
                if math.isfinite(ca):
                    c_deficit = 1.0 - (ca / 100.0 if ca > 1.0 else ca)
            except (TypeError, ValueError):
                pass
        if c_deficit is None and cooling_deficit is not None:
            try:
                c_deficit = float(cooling_deficit) if math.isfinite(float(cooling_deficit)) else None
            except (TypeError, ValueError):
                pass

        # Tree canopy deficit (lack of tree canopy)
        canopy = (
            p.get("tree_canopy_pct")
            or p.get("canopy_cover_pct")
            or p.get("canopy_pct")
            or nested_demo.get("tree_canopy_pct")
            or socio_dict.get("tree_canopy_pct")
            or tree_canopy_pct
        )
        canopy_deficit = None
        if canopy is not None:
            try:
                can_val = float(canopy)
                if math.isfinite(can_val):
                    can_norm = can_val / 100.0 if can_val > 1.0 else can_val
                    canopy_deficit = min(1.0, max(0.0, 1.0 - can_norm))
            except (TypeError, ValueError):
                pass
    else:
        try:
            elderly = max(0.0, float(elderly_or_props)) if elderly_or_props is not None and math.isfinite(float(elderly_or_props)) else 0.0
        except (TypeError, ValueError):
            elderly = 0.0
        children = children_share
        children_under_5 = child_share_under_5
        poverty = poverty_rate
        informal = informal_housing_pct
        outdoor = outdoor_worker_share
        c_deficit = cooling_deficit
        canopy_deficit = None
        if tree_canopy_pct is not None:
            try:
                tc = float(tree_canopy_pct)
                if math.isfinite(tc):
                    canopy_deficit = min(1.0, max(0.0, 1.0 - (tc / 100.0 if tc > 1.0 else tc)))
            except (TypeError, ValueError):
                pass

    # 1. Age sensitivity component
    if children_under_5 is not None:
        s_age = min(
            1.0,
            0.60 * (elderly / VULNERABILITY_MAX_ELDERLY_SHARE)
            + 0.40 * (children_under_5 / VULNERABILITY_MAX_CHILD_UNDER_5_SHARE),
        )
    elif children is not None:
        s_age = min(
            1.0,
            0.65 * (elderly / VULNERABILITY_MAX_ELDERLY_SHARE)
            + 0.35 * (children / VULNERABILITY_MAX_CHILDREN_SHARE),
        )
    else:
        s_age = min(1.0, elderly / VULNERABILITY_MAX_ELDERLY_SHARE)

    # 2. Socioeconomic deprivation component
    socio_values = []
    if poverty is not None:
        socio_values.append(min(1.0, max(0.0, float(poverty))))
    if informal is not None:
        val = float(informal)
        socio_values.append(min(1.0, max(0.0, val / 100.0 if val > 1.0 else val)))
    if outdoor is not None:
        val = float(outdoor)
        socio_values.append(min(1.0, max(0.0, val / 100.0 if val > 1.0 else val)))

    s_socio = sum(socio_values) / len(socio_values) if socio_values else 0.0

    # 3. Adaptive capacity deficit component (combining indoor cooling deficit & canopy lack)
    d_cooling_parts = []
    if c_deficit is not None:
        d_cooling_parts.append(("indoor", min(1.0, max(0.0, float(c_deficit)))))
    if canopy_deficit is not None:
        d_cooling_parts.append(("canopy", min(1.0, max(0.0, float(canopy_deficit)))))

    if len(d_cooling_parts) == 2:
        d_adaptive = 0.60 * d_cooling_parts[0][1] + 0.40 * d_cooling_parts[1][1]
    elif len(d_cooling_parts) == 1:
        d_adaptive = d_cooling_parts[0][1]
    else:
        d_adaptive = 0.0

    # Combine into vulnerability score
    has_enhanced = (children is not None) or (children_under_5 is not None) or bool(socio_values) or bool(d_cooling_parts)
    if not has_enhanced:
        return round(s_age, 4)

    # Additive amplification of vulnerability under deprivation and adaptive deficits
    vuln = min(1.0, s_age + 0.25 * s_socio + 0.25 * d_adaptive)
    return round(vuln, 4)


def decompose_vulnerability(
    elderly_or_props: Union[float, Mapping[str, Any], Dict[str, Any]],
    children_share: Optional[float] = None,
    poverty_rate: Optional[float] = None,
    cooling_deficit: Optional[float] = None,
    informal_housing_pct: Optional[float] = None,
    outdoor_worker_share: Optional[float] = None,
    child_share_under_5: Optional[float] = None,
    tree_canopy_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Provide detailed vulnerability breakdown across sensitivity, deprivation, and adaptive capacity."""
    score = calculate_vulnerability(
        elderly_or_props,
        children_share=children_share,
        poverty_rate=poverty_rate,
        cooling_deficit=cooling_deficit,
        informal_housing_pct=informal_housing_pct,
        outdoor_worker_share=outdoor_worker_share,
        child_share_under_5=child_share_under_5,
        tree_canopy_pct=tree_canopy_pct,
    )
    return {
        "vulnerability_score": score,
        "population_density_included": False,  # Strict integrity check: always False
        "pillars": {
            "age_sensitivity": "Elderly (>65) and children (<5, <14)",
            "socioeconomic_deprivation": "Poverty rate, informal housing %, outdoor workers",
            "adaptive_capacity_deficit": "Lack of tree canopy, lack of indoor cooling/AC",
        },
    }


def classify_risk_level(score: float) -> str:
    """Categorize continuous risk score into High, Moderate, or Low."""
    try:
        val = float(score)
        if not math.isfinite(val):
            return "Low"
    except (TypeError, ValueError):
        return "Low"

    if val >= RISK_HIGH_THRESHOLD:
        return "High"
    if val >= RISK_MODERATE_THRESHOLD:
        return "Moderate"
    return "Low"


# ---------------------------------------------------------------------------
# 4. Composite Parametric Risk Evaluation
# ---------------------------------------------------------------------------

def risk(
    p: Mapping[str, Any] | Dict[str, Any],
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> Dict[str, Any]:
    """Calculate IPCC-aligned parametric heat risk from zone attributes and weights.

    Incorporates multi-factor decomposition across Hazard, Exposure, and Vulnerability.

    Args:
        p: Dictionary or mapping of zone attributes.
        weights: 3-tuple of exponent weights (w_hazard, w_exposure, w_vulnerability).

    Returns:
        Dictionary containing risk_score, hazard, exposure, vulnerability,
        risk_level, missing_indicators, method, demographic_factors, synthetic flag,
        and detailed decomposition breakdowns.
    """
    nested_demo = p.get("demographics") if isinstance(p.get("demographics"), Mapping) else {}
    age_groups = nested_demo.get("age_groups") if isinstance(nested_demo.get("age_groups"), Mapping) else {}
    socio_dict = (
        nested_demo.get("socioeconomic_indicators")
        or nested_demo.get("socioeconomic_data")
        or p.get("socioeconomic_data")
        or {}
    )

    # 1. Multi-factor Hazard
    hazard = calculate_hazard(p)

    # 2. Multi-factor Exposure
    exposure = calculate_exposure(p)

    # 3. Multidimensional Vulnerability
    vulnerability = calculate_vulnerability(p)

    w_h, w_e, w_v = weights
    value = 100.0 * (hazard ** w_h) * (exposure ** w_e) * (vulnerability ** w_v)

    # Extract demographic factors present
    factors: Dict[str, Any] = {}
    for key in ["elderly_share", "children_share", "child_share_under_5"]:
        val = p.get(key)
        if val is None:
            val = nested_demo.get(key)
        if val is None:
            val = age_groups.get(key)
        if val is not None:
            try:
                factors[key] = round(float(val), 4)
            except (TypeError, ValueError):
                pass

    for key in ["poverty_rate", "cooling_deficit", "tree_canopy_pct", "informal_housing_pct", "outdoor_worker_share"]:
        val = p.get(key)
        if val is None:
            val = nested_demo.get(key)
        if val is None:
            val = socio_dict.get(key)
        if val is not None:
            try:
                factors[key] = round(float(val), 4)
            except (TypeError, ValueError):
                pass

    # Track missing indicators dynamically
    missing = []
    has_socio = (
        p.get("poverty_rate") is not None
        or p.get("socioeconomic_vulnerability") is not None
        or nested_demo.get("poverty_rate") is not None
        or nested_demo.get("socioeconomic_vulnerability") is not None
        or socio_dict.get("poverty_rate") is not None
        or bool(p.get("socioeconomic_data"))
    )
    if not has_socio:
        missing.append("Socioeconomic status")

    missing.append("Health conditions")

    has_cooling = (
        p.get("cooling_access") is not None
        or p.get("cooling_access_pct") is not None
        or p.get("cooling_deficit") is not None
        or nested_demo.get("cooling_deficit") is not None
        or socio_dict.get("cooling_access_pct") is not None
        or socio_dict.get("cooling_deficit") is not None
        or p.get("tree_canopy_pct") is not None
        or nested_demo.get("tree_canopy_pct") is not None
    )
    if not has_cooling:
        missing.append("Access to cooling")

    has_hazard_decomp = (
        p.get("air_temperature") is not None
        or p.get("heatwave_duration") is not None
        or p.get("heatwave_days") is not None
    )
    has_exposure_decomp = (
        p.get("building_density") is not None
        or p.get("built_up_density") is not None
        or p.get("sensitive_land_use") is not None
    )
    is_enhanced = (
        "children_share" in factors
        or "child_share_under_5" in factors
        or "poverty_rate" in factors
        or "cooling_deficit" in factors
        or has_hazard_decomp
        or has_exposure_decomp
    )

    if is_enhanced:
        method = (
            f"100 × (Hazard)^{w_h} × (Exposure)^{w_e} × (Vulnerability)^{w_v}; "
            "components clipped to [0,1]. Incorporates multi-factor hazard, exposure, and vulnerability indicators."
        )
    else:
        method = METHOD_DESCRIPTION

    # Check synthetic flag
    is_synth = True
    if p.get("synthetic") is not None:
        is_synth = bool(p["synthetic"])
    elif nested_demo.get("synthetic") is not None:
        is_synth = bool(nested_demo["synthetic"])
    elif isinstance(nested_demo.get("metadata"), Mapping) and nested_demo["metadata"].get("synthetic") is not None:
        is_synth = bool(nested_demo["metadata"]["synthetic"])

    return {
        "risk_score": value,
        "hazard": hazard,
        "exposure": exposure,
        "vulnerability": vulnerability,
        "risk_level": classify_risk_level(value),
        "missing_indicators": missing,
        "method": method,
        "demographic_factors": factors,
        "synthetic_demographics": is_synth,
        "hazard_breakdown": decompose_hazard(p),
        "exposure_breakdown": decompose_exposure(p),
        "vulnerability_breakdown": decompose_vulnerability(p),
    }


__all__ = [
    "risk",
    "calculate_hazard",
    "calculate_exposure",
    "calculate_vulnerability",
    "decompose_hazard",
    "decompose_exposure",
    "decompose_vulnerability",
    "classify_risk_level",
    "HAZARD_MAX_SUHII",
    "HAZARD_AIR_BASELINE_TEMP",
    "HAZARD_AIR_EXTREME_TEMP",
    "HAZARD_MAX_HEATWAVE_DAYS",
    "EXPOSURE_MAX_DENSITY",
    "EXPOSURE_MAX_BUILT_UP",
    "EXPOSURE_MAX_SENSITIVE_SCORE",
    "VULNERABILITY_MAX_ELDERLY_SHARE",
    "VULNERABILITY_MAX_CHILDREN_SHARE",
    "VULNERABILITY_MAX_CHILD_UNDER_5_SHARE",
    "RISK_HIGH_THRESHOLD",
    "RISK_MODERATE_THRESHOLD",
    "DEFAULT_WEIGHTS",
    "MISSING_INDICATORS",
    "METHOD_DESCRIPTION",
    "METHOD_DECOMPOSED_DESCRIPTION",
]
