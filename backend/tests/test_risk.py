"""Unit tests for multi-factor heat risk assessment and vulnerability integrity.

Verifies:
1. Multi-factor Hazard decomposition (Surface SUHII, Ambient Air Temp, Heatwave Duration).
2. Multi-factor Exposure decomposition (Population Density, Built-Up Density, Sensitive Land Use).
3. Vulnerability Integrity Mandate (Population density is NEVER in vulnerability; Age structure,
   Socioeconomic deprivation, Adaptive cooling deficit, Lack of tree canopy).
4. Parametric IPCC AR5/AR6 risk combination and classification.
"""

import math
import pytest

from app.services import risk


# ---------------------------------------------------------------------------
# 1. Multi-Factor Hazard Decomposition
# ---------------------------------------------------------------------------

def test_hazard_suhii_baseline_compatibility():
    """Verify surface SUHII alone computes exact normalized cap relative to 8°C."""
    assert risk.calculate_hazard(0.0) == 0.0
    assert risk.calculate_hazard(4.0) == 0.50
    assert risk.calculate_hazard(8.0) == 1.0
    # Values above 8.0°C capped at 1.0
    assert risk.calculate_hazard(12.0) == 1.0
    # Negative SUHII (cool island) clipped to 0.0
    assert risk.calculate_hazard(-2.5) == 0.0
    # Non-finite values safely return 0.0
    assert risk.calculate_hazard(float("nan")) == 0.0
    assert risk.calculate_hazard(float("inf")) == 0.0
    assert risk.calculate_hazard(None) == 0.0
    assert risk.calculate_hazard("invalid") == 0.0


def test_hazard_with_ambient_air_temperature():
    """Verify ambient air temperature relative to [28°C, 45°C] climatological baseline."""
    # At baseline onset (28°C), air hazard is 0.0
    h_base = risk.calculate_hazard(4.0, air_temperature=28.0)
    # 0.60 * (4.0 / 8.0) + 0.40 * 0.0 = 0.30
    assert pytest.approx(h_base, 1e-4) == 0.30

    # At extreme threshold (45°C), air hazard is 1.0
    h_extreme = risk.calculate_hazard(4.0, air_temperature=45.0)
    # 0.60 * 0.50 + 0.40 * 1.0 = 0.70
    assert pytest.approx(h_extreme, 1e-4) == 0.70

    # Below 28°C clipped to 0.0
    h_cool = risk.calculate_hazard(4.0, air_temperature=25.0)
    assert pytest.approx(h_cool, 1e-4) == 0.30

    # Above 45°C capped at 1.0
    h_hot = risk.calculate_hazard(4.0, air_temperature=48.0)
    assert pytest.approx(h_hot, 1e-4) == 0.70


def test_hazard_with_heatwave_duration():
    """Verify heatwave duration (consecutive days above threshold / 7 days)."""
    # 0 days duration
    h_zero = risk.calculate_hazard(4.0, heatwave_duration=0.0)
    # 0.70 * 0.50 + 0.30 * 0.0 = 0.35
    assert pytest.approx(h_zero, 1e-4) == 0.35

    # 3.5 days duration (halfway)
    h_mid = risk.calculate_hazard(4.0, heatwave_duration=3.5)
    # 0.70 * 0.50 + 0.30 * 0.50 = 0.50
    assert pytest.approx(h_mid, 1e-4) == 0.50

    # 7+ days duration (max cap)
    h_full = risk.calculate_hazard(4.0, heatwave_duration=10.0)
    # 0.70 * 0.50 + 0.30 * 1.00 = 0.65
    assert pytest.approx(h_full, 1e-4) == 0.65


def test_hazard_three_factor_decomposition():
    """Verify full composite hazard combining surface SUHII, air temp, and duration."""
    # SUHII = 4.0 °C (0.50)
    # Air Temp = 36.5 °C -> (36.5 - 28) / 17 = 0.50
    # Heatwave Duration = 3.5 days -> 3.5 / 7 = 0.50
    # Weights: 0.50 surface + 0.30 air + 0.20 duration = 1.00
    h_composite = risk.calculate_hazard(
        4.0,
        air_temperature=36.5,
        heatwave_duration=3.5,
        surface_weight=0.50,
        air_weight=0.30,
        duration_weight=0.20,
    )
    assert pytest.approx(h_composite, 1e-4) == 0.50

    # From zone properties dictionary
    zone_props = {
        "predicted_suhii": 6.0,  # 6.0 / 8.0 = 0.75
        "air_temperature": 41.6,  # (41.6 - 28) / 17 = 0.80
        "heatwave_duration": 4.9,  # 4.9 / 7 = 0.70
    }
    h_dict = risk.calculate_hazard(zone_props)
    expected = 0.50 * 0.75 + 0.30 * 0.80 + 0.20 * 0.70  # 0.375 + 0.24 + 0.14 = 0.755
    assert pytest.approx(h_dict, 1e-3) == expected


def test_decompose_hazard_metadata_and_units():
    """Verify detailed hazard decomposition returns physical units and transparent values."""
    decomp = risk.decompose_hazard(
        suhii_or_props=5.2,
        air_temperature=39.0,
        heatwave_duration=4.0,
    )
    assert "hazard_score" in decomp
    assert decomp["surface_heat"]["value_celsius"] == 5.2
    assert decomp["surface_heat"]["cap_celsius"] == 8.0
    assert decomp["air_temperature"]["value_celsius"] == 39.0
    assert decomp["air_temperature"]["baseline_celsius"] == 28.0
    assert decomp["heatwave_duration"]["value_days"] == 4.0
    assert "°C" in decomp["units"]["surface_heat"]
    assert "days" in decomp["units"]["heatwave_duration"]


# ---------------------------------------------------------------------------
# 2. Multi-Factor Exposure Decomposition
# ---------------------------------------------------------------------------

def test_exposure_pop_density_baseline_compatibility():
    """Verify population density alone computes exact normalized cap relative to 25,000 / km²."""
    assert risk.calculate_exposure(0.0) == 0.0
    assert risk.calculate_exposure(12500.0) == 0.50
    assert risk.calculate_exposure(25000.0) == 1.0
    assert risk.calculate_exposure(50000.0) == 1.0  # clipped
    assert risk.calculate_exposure(-500.0) == 0.0  # clipped
    assert risk.calculate_exposure(float("nan")) == 0.0
    assert risk.calculate_exposure(None) == 0.0


def test_exposure_with_built_up_density():
    """Verify combining human population density with built-up / residential density."""
    # Population 12,500 (0.50), Built-up 0.80 (80% built)
    # Weights: 0.65 pop + 0.35 built
    e_built = risk.calculate_exposure(12500.0, building_density=0.80)
    expected = 0.65 * 0.50 + 0.35 * 0.80  # 0.325 + 0.280 = 0.605
    assert pytest.approx(e_built, 1e-4) == expected

    # Percentage input (80.0 instead of 0.80) safely normalized
    e_pct = risk.calculate_exposure(12500.0, building_density=80.0)
    assert pytest.approx(e_pct, 1e-4) == expected


def test_exposure_three_factor_decomposition():
    """Verify full composite exposure combining population, built-up surface, and sensitive land use."""
    # Pop density = 12,500 (0.50)
    # Built-up = 0.50 (0.50)
    # Sensitive land use = 0.50 (0.50)
    # Weights: 0.50 pop + 0.30 built + 0.20 sensitive = 0.50
    e_comp = risk.calculate_exposure(
        12500.0,
        building_density=0.50,
        sensitive_land_use=0.50,
        pop_weight=0.50,
        built_weight=0.30,
        sensitive_weight=0.20,
    )
    assert pytest.approx(e_comp, 1e-4) == 0.50

    # From zone dictionary with institutional facilities
    zone_props = {
        "population_density": 15000.0,  # 15000 / 25000 = 0.60
        "building_density": 0.70,  # 0.70
        "schools_count": 6,
        "hospitals_count": 2,  # sensitive = min(1.0, 6*0.05 + 2*0.10) = 0.50
    }
    e_dict = risk.calculate_exposure(zone_props)
    expected_dict = 0.50 * 0.60 + 0.30 * 0.70 + 0.20 * 0.50  # 0.30 + 0.21 + 0.10 = 0.61
    assert pytest.approx(e_dict, 1e-3) == expected_dict


def test_decompose_exposure_metadata_and_units():
    decomp = risk.decompose_exposure(
        population_or_props=18000.0,
        building_density=0.75,
        sensitive_land_use=0.40,
    )
    assert "exposure_score" in decomp
    assert decomp["population_density"]["value_people_km2"] == 18000.0
    assert decomp["built_up_density"]["value_fraction"] == 0.75
    assert decomp["sensitive_land_use"]["value_score"] == 0.40
    assert "people/km²" in decomp["units"]["population_density"]


# ---------------------------------------------------------------------------
# 3. Vulnerability Integrity Mandate (Population Density Strictly Excluded)
# ---------------------------------------------------------------------------

def test_vulnerability_integrity_mandate_no_population_density():
    """CRITICAL MANDATE: Verify population density NEVER inflates or affects vulnerability."""
    base_props = {
        "elderly_share": 0.15,
        "children_share": 0.24,
        "poverty_rate": 0.20,
        "cooling_access_pct": 50.0,
        "tree_canopy_pct": 10.0,
    }

    # Extremely low population density
    v_sparse = risk.calculate_vulnerability({**base_props, "population_density": 100.0})

    # Extremely high population density
    v_dense = risk.calculate_vulnerability({**base_props, "population_density": 50000.0})

    # Massive 500x population density difference MUST NOT change vulnerability score by even 1e-6
    assert abs(v_sparse - v_dense) < 1e-6
    assert v_sparse == v_dense

    # Breakdown attestation
    decomp = risk.decompose_vulnerability(base_props)
    assert decomp["population_density_included"] is False


def test_vulnerability_age_sensitivity_children_under_5():
    """Verify child under 5 sensitivity weighting."""
    # Elderly only
    v_elderly = risk.calculate_vulnerability(elderly_or_props=0.15)
    assert pytest.approx(v_elderly, 1e-4) == 0.15 / 0.25  # 0.60

    # With children under 5 (higher physiological sensitivity)
    v_u5 = risk.calculate_vulnerability(
        elderly_or_props=0.15,
        child_share_under_5=0.08,
    )
    # 0.60 * (0.15 / 0.25) + 0.40 * (0.08 / 0.12) = 0.60 * 0.60 + 0.40 * 0.6667 ~ 0.6267
    assert v_u5 > v_elderly
    assert pytest.approx(v_u5, 1e-2) == 0.63


def test_vulnerability_adaptive_capacity_tree_canopy():
    """Verify lack of tree canopy is integrated into adaptive cooling deficit."""
    base = {
        "elderly_share": 0.12,
        "children_share": 0.22,
        "poverty_rate": 0.18,
        "cooling_access_pct": 60.0,  # 40% indoor deficit
    }
    # High canopy coverage (25% canopy -> 75% canopy deficit)
    v_green = risk.calculate_vulnerability({**base, "tree_canopy_pct": 25.0})

    # Deprived canopy (3% canopy -> 97% canopy deficit)
    v_barren = risk.calculate_vulnerability({**base, "tree_canopy_pct": 3.0})

    assert v_barren > v_green


def test_vulnerability_socioeconomic_deprivation():
    """Verify multidimensional deprivation across poverty, informal housing, and outdoor work."""
    base = {"elderly_share": 0.12, "children_share": 0.22}
    v_baseline = risk.calculate_vulnerability(base)

    deprived = {
        **base,
        "poverty_rate": 0.35,
        "informal_housing_pct": 30.0,
        "outdoor_worker_share": 35.0,
    }
    v_deprived = risk.calculate_vulnerability(deprived)
    assert v_deprived > v_baseline


# ---------------------------------------------------------------------------
# 4. Parametric IPCC AR5/AR6 Risk Evaluation
# ---------------------------------------------------------------------------

def test_risk_full_multidimensional_evaluation():
    """Verify comprehensive parametric risk calculation with all decomposed indices."""
    zone = {
        "id": "AMC-07",
        "name": "Khadia (Central Zone Historic Core)",
        "city": "Ahmedabad",
        "predicted_suhii": 5.6,  # 5.6 / 8 = 0.70
        "air_temperature": 42.0,  # (42 - 28) / 17 = 0.8235
        "heatwave_duration": 4.5,  # 4.5 / 7 = 0.6429
        "population_density": 38000.0,  # capped at 1.0
        "building_density": 0.88,  # 0.88
        "sensitive_facilities_count": 18,  # sensitive ~ 1.0
        "elderly_share": 0.11,
        "children_share": 0.24,
        "children_under_5_share": 0.08,
        "poverty_rate": 0.28,
        "informal_housing_pct": 24.0,
        "outdoor_worker_share": 0.30,
        "cooling_access_pct": 34.0,
        "tree_canopy_pct": 3.0,
        "synthetic": False,
    }
    res = risk.risk(zone)

    assert 0.0 <= res["hazard"] <= 1.0
    assert 0.0 <= res["exposure"] <= 1.0
    assert 0.0 <= res["vulnerability"] <= 1.0
    assert 0.0 <= res["risk_score"] <= 100.0
    assert res["risk_level"] in ["High", "Moderate", "Low"]
    assert res["synthetic_demographics"] is False

    # Check that all breakdowns are populated
    assert "hazard_breakdown" in res
    assert "exposure_breakdown" in res
    assert "vulnerability_breakdown" in res
    assert res["hazard_breakdown"]["surface_heat"]["cap_celsius"] == 8.0
    assert res["exposure_breakdown"]["population_density"]["cap_people_km2"] == 25000.0
    assert res["vulnerability_breakdown"]["population_density_included"] is False


def test_risk_nan_and_none_robustness():
    """Verify NaN and None inputs across hazard, exposure, and vulnerability don't crash."""
    zone_none = {
        "predicted_suhii": None,
        "population_density": None,
        "elderly_share": None,
        "air_temperature": None,
        "building_density": None,
    }
    res = risk.risk(zone_none)
    assert res["hazard"] >= 0.0
    assert res["exposure"] == 0.0
    assert res["vulnerability"] == 0.0
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "Low"

    zone_nan = {
        "predicted_suhii": float("nan"),
        "population_density": float("nan"),
        "elderly_share": float("nan"),
    }
    res_nan = risk.risk(zone_nan)
    assert res_nan["hazard"] == 0.0
    assert res_nan["exposure"] == 0.0
    assert res_nan["vulnerability"] == 0.0
    assert res_nan["risk_score"] == 0.0
