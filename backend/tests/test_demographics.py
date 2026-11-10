"""Unit tests for demographic data ingestion, vulnerability indicators, and risk service."""

import asyncio
import httpx
import pytest

from app.services import demographics
from app.services import risk


# ---------------------------------------------------------------------------
# 1. Computation Unit Tests: Density, Age Groups, Vulnerability Indicators
# ---------------------------------------------------------------------------

def test_compute_population_density():
    # Standard calculation
    assert demographics.compute_population_density(10000, 2.0) == 5000.0
    assert demographics.compute_population_density(12345, 1.0) == 12345.0

    # Non-positive or zero area
    assert demographics.compute_population_density(10000, 0.0) == 0.0
    assert demographics.compute_population_density(10000, -1.5) == 0.0
    assert demographics.compute_population_density(10000, float("nan")) == 0.0
    assert demographics.compute_population_density(10000, None) == 0.0

    # Negative or non-finite population
    assert demographics.compute_population_density(-500, 1.0) == 0.0
    assert demographics.compute_population_density(None, 1.0) == 0.0


def test_compute_population_density_robustness():
    # Numeric strings
    assert demographics.compute_population_density("10000", "2.0") == 5000.0
    assert demographics.compute_population_density("15000", 1.5) == 10000.0
    # Invalid strings
    assert demographics.compute_population_density("invalid", 2.0) == 0.0
    assert demographics.compute_population_density(10000, "invalid") == 0.0
    # Non-finite values
    assert demographics.compute_population_density(float("inf"), 1.0) == 0.0
    assert demographics.compute_population_density(10000, float("inf")) == 0.0


def test_compute_age_groups_shares():
    # Input as proportions
    result = demographics.compute_age_groups(
        total_population=10000,
        children=0.25,
        working_age=0.65,
        elderly=0.10,
    )
    assert result["total_population"] == 10000
    assert result["children_share"] == 0.25
    assert result["working_age_share"] == 0.65
    assert result["elderly_share"] == 0.10
    assert result["children_count"] == 2500
    assert result["working_age_count"] == 6500
    assert result["elderly_count"] == 1000
    # Dependency ratio: (0.25 + 0.10) / 0.65 ~ 0.5385
    assert pytest.approx(result["dependency_ratio"], 0.01) == 0.5385
    # Aging index: (0.10 / 0.25) * 100 = 40.0
    assert pytest.approx(result["aging_index"], 0.01) == 40.0


def test_compute_age_groups_counts():
    # Input as counts
    result = demographics.compute_age_groups(
        total_population=20000,
        children=4000,
        working_age=14000,
        elderly=2000,
    )
    assert result["children_share"] == 0.20
    assert result["working_age_share"] == 0.70
    assert result["elderly_share"] == 0.10
    assert result["children_count"] == 4000
    assert result["working_age_count"] == 14000
    assert result["elderly_count"] == 2000


def test_compute_age_groups_zero_total_with_counts():
    # When total is passed as 0 or None, total should be derived from the sum of counts
    result = demographics.compute_age_groups(
        total_population=0,
        children=50,
        working_age=100,
        elderly=20,
    )
    assert result["total_population"] == 170.0
    assert result["children_count"] == 50
    assert result["working_age_count"] == 100
    assert result["elderly_count"] == 20
    assert result["children_share"] == round(50 / 170.0, 4)
    assert result["elderly_share"] == round(20 / 170.0, 4)


def test_compute_age_groups_zero_components():
    result = demographics.compute_age_groups(
        total_population=0,
        children=0,
        working_age=0,
        elderly=0,
    )
    assert result["total_population"] == 0
    assert 0 <= result["elderly_share"] <= 1
    assert result["dependency_ratio"] >= 0


def test_compute_vulnerability_indicators_demographic_only():
    age_data = {
        "elderly_share": 0.20,
        "children_share": 0.25,
        "dependency_ratio": 0.82,
    }
    result = demographics.compute_vulnerability_indicators(age_data)
    assert 0.0 <= result["demographic_sensitivity"] <= 1.0
    assert 0.0 <= result["composite_vulnerability"] <= 1.0
    assert result["vulnerability_level"] in ["Low", "Moderate", "High"]
    # Socioeconomic and cooling access are missing
    assert "Socioeconomic status" in result["missing_indicators"]
    assert "Access to cooling" in result["missing_indicators"]
    assert "Health conditions" in result["missing_indicators"]


def test_compute_vulnerability_indicators_multidimensional():
    age_data = {
        "elderly_share": 0.22,
        "children_share": 0.28,
        "dependency_ratio": 1.0,
    }
    socio_data = {
        "poverty_rate": 0.35,
        "informal_housing_pct": 25.0,
        "outdoor_worker_share": 0.30,
        "cooling_access_pct": 20.0,  # 80% cooling deficit
    }
    result = demographics.compute_vulnerability_indicators(age_data, socio_data)
    assert result["socioeconomic_vulnerability"] is not None
    assert result["socioeconomic_vulnerability"] > 0.25
    assert result["cooling_deficit"] == 0.80
    assert result["composite_vulnerability"] >= 0.60
    assert result["vulnerability_level"] == "High"
    # Socioeconomic and cooling access are NOT in missing indicators
    assert "Socioeconomic status" not in result["missing_indicators"]
    assert "Access to cooling" not in result["missing_indicators"]
    assert "Health conditions" in result["missing_indicators"]


def test_compute_vulnerability_indicators_none_and_embedded_socio():
    # Pass None values without crash
    res_none = demographics.compute_vulnerability_indicators({
        "elderly_share": None,
        "children_share": None,
        "dependency_ratio": None,
    })
    assert 0.0 <= res_none["composite_vulnerability"] <= 1.0
    assert res_none["vulnerability_level"] in ["Low", "Moderate", "High"]

    # Socioeconomic indicators nested directly inside demographic dictionary
    embedded_data = {
        "elderly_share": 0.18,
        "children_share": 0.24,
        "socioeconomic_indicators": {
            "poverty_rate": 0.28,
            "cooling_deficit": 0.50,
        },
    }
    res_embedded = demographics.compute_vulnerability_indicators(embedded_data)
    assert res_embedded["socioeconomic_vulnerability"] is not None
    assert res_embedded["cooling_deficit"] == 0.50
    assert "Socioeconomic status" not in res_embedded["missing_indicators"]


# ---------------------------------------------------------------------------
# 2. Metadata Storage and Fallback Labeling Tests
# ---------------------------------------------------------------------------

def test_metadata_storage_real_data():
    meta = demographics.build_metadata(
        source="WorldPop Global Denominators",
        source_type="WorldPop",
        date="2020",
        resolution_m=100,
        crs="EPSG:4326",
        synthetic=False,
        fallback=False,
    )
    assert meta["source"] == "WorldPop Global Denominators"
    assert meta["source_type"] == "WorldPop"
    assert meta["acquisition_date"] == "2020"
    assert meta["resolution_m"] == 100
    assert meta["resolution"] == "100m"
    assert meta["crs"] == "EPSG:4326"
    assert meta["synthetic"] is False
    assert meta["fallback"] is False
    assert len(meta["limitations"]) > 0


def test_synthetic_fallback_generator():
    result = demographics.generate_synthetic_demographics(
        city="Ahmedabad",
        area_km2=2.5,
        reason="Remote WorldPop server connection timed out",
    )
    # Explicit mandatory fallback labels
    assert result["source"] == "synthetic"
    assert result["synthetic"] is True
    assert result["fallback"] is True
    assert "Remote WorldPop server connection timed out" in result["fallback_reason"]

    # Metadata validation
    assert result["metadata"]["synthetic"] is True
    assert result["metadata"]["fallback"] is True
    assert result["metadata"]["resolution_m"] == 1000
    assert result["metadata"]["fallback_reason"] == "Remote WorldPop server connection timed out"

    # Numerical validity
    assert result["population_density"] > 0
    assert result["total_population"] > 0
    assert 0.0 < result["elderly_share"] < 1.0
    assert 0.0 < result["children_share"] < 1.0
    assert result["vulnerability_indicators"]["composite_vulnerability"] > 0


# ---------------------------------------------------------------------------
# 3. HTTP Mocking Unit Tests: WorldPop Ingestion
# ---------------------------------------------------------------------------

def test_worldpop_success(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        assert params == {"iso3": "IND"}
        return {
            "data": [
                {"id": "wp_2020_ind", "popyear": "2020", "desc": "India 2020 Population", "resolution": "100m"},
                {"id": "wp_2015_ind", "popyear": "2015", "desc": "India 2015 Population"},
            ]
        }

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(demographics.fetch_worldpop(country="India", city="Ahmedabad", year=2020, area_km2=1.5))

    assert result["source"] == "WorldPop"
    assert result["synthetic"] is False
    assert result["fallback"] is False
    assert result["country"] == "IND"
    assert result["city"] == "Ahmedabad"
    assert result["year"] == 2020
    assert len(result["datasets"]) == 1
    assert result["datasets"][0]["id"] == "wp_2020_ind"
    assert result["metadata"]["resolution_m"] == 100
    assert result["metadata"]["synthetic"] is False
    assert result["catalog_only"] is True
    assert result["metadata"]["analysis_ready"] is False
    assert result["population_density"] is None
    assert result["total_population"] is None
    assert result["age_groups"] is None
    assert result["vulnerability_indicators"] is None


def test_worldpop_no_matching_year(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return {"data": [{"id": "wp_2010_ind", "popyear": "2010"}]}

    monkeypatch.setattr(demographics, "get_json", mock_get)
    with pytest.raises(ValueError, match="No WorldPop datasets found"):
        asyncio.run(demographics.fetch_worldpop(country="IND", year=2020))


def test_worldpop_http_error(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        raise httpx.ConnectTimeout("WorldPop API connection timed out")

    monkeypatch.setattr(demographics, "get_json", mock_get)
    with pytest.raises(httpx.ConnectTimeout):
        asyncio.run(demographics.fetch_worldpop(country="IND", year=2020))


# ---------------------------------------------------------------------------
# 4. STAC Mocking Unit Tests: GHSL Ingestion
# ---------------------------------------------------------------------------

def test_ghsl_stac_success(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        assert "bbox" in params
        return {
            "features": [
                {
                    "id": "jrc_ghsl_pop_2020_1",
                    "collection": "jrc_ghsl_pop",
                    "bbox": [72.5, 23.0, 72.6, 23.1],
                    "properties": {"datetime": "2020-01-01T00:00:00Z", "ghsl:population": 12500},
                    "assets": {
                        "data": {"href": "https://example.org/ghsl_tile.tif"}
                    },
                }
            ]
        }

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(demographics.fetch_ghsl(lat=23.02, lon=72.57, city="Ahmedabad", year=2020, area_km2=1.0))

    assert result["source"] == "GHSL"
    assert result["synthetic"] is False
    assert result["fallback"] is False
    assert result["city"] == "Ahmedabad"
    assert len(result["tiles"]) == 1
    assert result["tiles"][0]["id"] == "jrc_ghsl_pop_2020_1"
    assert result["tiles"][0]["asset_href"] == "https://example.org/ghsl_tile.tif"
    assert result["metadata"]["resolution_m"] == 100
    assert result["catalog_only"] is True
    assert result["metadata"]["analysis_ready"] is False
    assert result["population_density"] is None
    assert result["total_population"] is None
    assert result["age_groups"] is None
    assert result["vulnerability_indicators"] is None


def test_ghsl_stac_empty_tiles(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return {"features": []}

    monkeypatch.setattr(demographics, "get_json", mock_get)
    with pytest.raises(ValueError, match="No GHSL population tiles intersect"):
        asyncio.run(demographics.fetch_ghsl(lat=23.02, lon=72.57, year=2020))


def test_ghsl_stac_http_error(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        raise httpx.HTTPStatusError("502 Bad Gateway", request=None, response=None)

    monkeypatch.setattr(demographics, "get_json", mock_get)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(demographics.fetch_ghsl(lat=23.02, lon=72.57, year=2020))


# ---------------------------------------------------------------------------
# 5. HTTP Mocking Unit Tests: Census Ingestion
# ---------------------------------------------------------------------------

def test_census_http_success(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return [
            ["NAME", "P1_001N", "state", "county"],
            ["Ahmedabad Urban Ward", "22450", "24", "001"],
        ]

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(
        demographics.fetch_census(city="Ahmedabad", ward_id="ward_01", year=2021, area_km2=2.0)
    )

    assert result["source"] == "Census"
    assert result["synthetic"] is False
    assert result["fallback"] is False
    assert result["total_population"] == 22450
    assert result["population_density"] == 11225.0
    assert result["socioeconomic_indicators"]["poverty_rate"] > 0
    assert result["metadata"]["source_type"] == "Census"


def test_census_multi_row_matching(monkeypatch):
    # Verify that multi-row tables match the requested ward or city correctly
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return [
            ["NAME", "TOT_P", "state", "county"],
            ["Autauga County, Alabama", "58805", "01", "001"],
            ["Baldwin County, Alabama", "231767", "01", "003"],
        ]

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(
        demographics.fetch_census(city="Baldwin", ward_id="003", year=2020, area_km2=10.0)
    )

    assert result["total_population"] == 231767.0
    assert result["population_density"] == 23176.7


def test_census_invalid_table(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return []

    monkeypatch.setattr(demographics, "get_json", mock_get)
    with pytest.raises(ValueError, match="Census API returned invalid"):
        asyncio.run(demographics.fetch_census(city="Ahmedabad", year=2021))


# ---------------------------------------------------------------------------
# 6. Unified Ingestion and Graceful Fallback
# ---------------------------------------------------------------------------

def test_ingest_demographics_auto_success(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return {
            "data": [
                {"id": "wp_ind_2020", "popyear": "2020", "desc": "India WorldPop"}
            ]
        }

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(demographics.ingest_demographics(source="auto", city="Ahmedabad", year=2020))

    assert result["source"] == "WorldPop"
    assert result["synthetic"] is False
    assert result["fallback"] is False


def test_ingest_demographics_auto_fallback_on_all_errors(monkeypatch):
    async def mock_get(url, params=None, headers=None, timeout=30.0):
        raise httpx.RequestError("Network unreachable")

    monkeypatch.setattr(demographics, "get_json", mock_get)
    result = asyncio.run(
        demographics.ingest_demographics(source="auto", city="Ahmedabad", fallback_on_error=True)
    )

    # Automatic graceful fallback to synthetic
    assert result["source"] == "synthetic"
    assert result["synthetic"] is True
    assert result["fallback"] is True
    assert "Fetch failed for auto" in result["fallback_reason"]
    assert result["metadata"]["synthetic"] is True


def test_ingest_demographics_explicit_synthetic():
    result = demographics.ingest_demographics_sync(source="synthetic", city="Delhi")
    assert result["source"] == "synthetic"
    assert result["synthetic"] is True
    assert result["fallback"] is True
    assert result["city"] == "Delhi"


def test_ingest_demographics_invalid_source():
    with pytest.raises(ValueError, match="Unsupported demographic source"):
        asyncio.run(demographics.ingest_demographics(source="unknown_source", fallback_on_error=False))


def test_demographics_clear_cache():
    demographics.clear_cache()
    assert len(demographics._CACHE) == 0


# ---------------------------------------------------------------------------
# 7. Parametric Risk Assessment Integration (risk.py)
# ---------------------------------------------------------------------------

def test_risk_backward_compatibility():
    """Verify zone with legacy elderly_share produces exact expected baseline calculation."""
    p_legacy = {
        "predicted_suhii": 3.2,
        "population_density": 15000,
        "elderly_share": 0.15,
        "synthetic": True,
    }
    res = risk.risk(p_legacy, weights=(1.0, 1.0, 1.0))

    expected_hazard = 3.2 / 8.0  # 0.40
    expected_exposure = 15000 / 25000.0  # 0.60
    expected_vuln = 0.15 / 0.25  # 0.60
    expected_score = 100.0 * expected_hazard * expected_exposure * expected_vuln  # 14.40

    assert pytest.approx(res["hazard"], 1e-4) == expected_hazard
    assert pytest.approx(res["exposure"], 1e-4) == expected_exposure
    assert pytest.approx(res["vulnerability"], 1e-4) == expected_vuln
    assert pytest.approx(res["risk_score"], 1e-4) == expected_score
    assert res["risk_level"] == "Moderate"
    assert res["missing_indicators"] == [
        "Socioeconomic status",
        "Health conditions",
        "Access to cooling",
    ]


def test_risk_with_enhanced_demographics():
    """Verify incorporating children_share, poverty_rate, and cooling_deficit increases risk fidelity."""
    p_baseline = {
        "predicted_suhii": 3.2,
        "population_density": 15000,
        "elderly_share": 0.15,
    }
    r_base = risk.risk(p_baseline)["risk_score"]

    # Add child vulnerability
    p_with_children = {
        **p_baseline,
        "children_share": 0.30,
    }
    r_children = risk.risk(p_with_children)["risk_score"]
    assert r_children > r_base

    # Add high poverty rate
    p_deprived = {
        **p_with_children,
        "poverty_rate": 0.40,
    }
    r_deprived = risk.risk(p_deprived)["risk_score"]
    assert r_deprived > r_children
    # Socioeconomic status should no longer be listed as missing
    assert "Socioeconomic status" not in risk.risk(p_deprived)["missing_indicators"]

    # Add high cooling deficit (lack of AC / cooling infrastructure)
    p_cooling_deficit = {
        **p_deprived,
        "cooling_deficit": 0.85,
    }
    r_severe = risk.risk(p_cooling_deficit)["risk_score"]
    assert r_severe > r_deprived
    assert "Access to cooling" not in risk.risk(p_cooling_deficit)["missing_indicators"]


def test_risk_with_nested_demographics():
    """Verify zone with nested demographics object extracts density, age shares, and synthetic flag."""
    p_nested = {
        "predicted_suhii": 3.6,
        "demographics": {
            "source": "WorldPop",
            "synthetic": False,
            "population_density": 12500.0,
            "elderly_share": 0.14,
            "children_share": 0.28,
            "socioeconomic_indicators": {
                "poverty_rate": 0.22,
                "cooling_deficit": 0.40,
            },
        },
    }
    res = risk.risk(p_nested)

    assert res["exposure"] == 12500.0 / 25000.0  # 0.50
    assert res["exposure"] > 0.0
    assert res["vulnerability"] > 0.0
    assert res["risk_score"] > 0.0
    assert res["synthetic_demographics"] is False
    assert res["demographic_factors"]["elderly_share"] == 0.14
    assert res["demographic_factors"]["children_share"] == 0.28
    assert res["demographic_factors"]["poverty_rate"] == 0.22
    assert res["demographic_factors"]["cooling_deficit"] == 0.40
    assert "Socioeconomic status" not in res["missing_indicators"]


def test_risk_with_none_values():
    """Verify zone attributes containing None values do not trigger TypeErrors or crash."""
    p_none = {
        "predicted_suhii": 3.0,
        "population_density": 10000,
        "elderly_share": 0.12,
        "children_share": None,
        "poverty_rate": None,
        "cooling_deficit": None,
        "synthetic": None,
    }
    res = risk.risk(p_none)
    assert res["risk_score"] > 0.0
    assert "children_share" not in res["demographic_factors"]
    assert "poverty_rate" not in res["demographic_factors"]
    assert "Socioeconomic status" in res["missing_indicators"]
    assert "Access to cooling" in res["missing_indicators"]


def test_risk_nan_handling():
    """Verify non-finite / NaN values are cleanly bounded and do not propagate NaNs."""
    p_nan = {
        "predicted_suhii": float("nan"),
        "population_density": float("nan"),
        "elderly_share": float("nan"),
    }
    res = risk.risk(p_nan)
    assert res["hazard"] == 0.0
    assert res["exposure"] == 0.0
    assert res["vulnerability"] == 0.0
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "Low"


def test_risk_weights_sensitivity():
    p = {
        "observed_suhii": 4.0,
        "population_density": 20000,
        "elderly_share": 0.18,
        "children_share": 0.25,
        "poverty_rate": 0.25,
    }
    r_balanced = risk.risk(p, weights=(1.0, 1.0, 1.0))["risk_score"]
    r_hazard_heavy = risk.risk(p, weights=(2.5, 1.0, 1.0))["risk_score"]
    r_vuln_heavy = risk.risk(p, weights=(1.0, 1.0, 2.5))["risk_score"]

    assert r_hazard_heavy != r_balanced
    assert r_vuln_heavy != r_balanced
    assert 0.0 <= r_balanced <= 100.0
    assert 0.0 <= r_hazard_heavy <= 100.0


# ---------------------------------------------------------------------------
# 8. Authentic Indian Municipal Ward Benchmarks & Raster Sampling
# ---------------------------------------------------------------------------

def test_ahmedabad_amc_48_wards_benchmark_completeness():
    """Verify all 48 Ahmedabad Municipal Corporation (AMC) wards are present with authentic metrics."""
    wards = demographics.list_municipal_wards("Ahmedabad")
    assert len(wards) == 48

    ward_ids = [w["ward_id"] for w in wards]
    assert len(set(ward_ids)) == 48  # All 48 ward IDs must be unique
    assert ward_ids[0] == "AMC-01"
    assert ward_ids[-1] == "AMC-48"

    # Verify every ward possesses complete authentic demographic and vulnerability indicators
    for w in wards:
        assert w["population"] >= 50000
        assert w["area_km2"] > 0
        assert w["population_density"] == round(w["population"] / w["area_km2"], 2)
        assert 0.05 <= w["elderly_share"] <= 0.20
        assert 0.15 <= w["children_share"] <= 0.35
        assert 0.04 <= w["children_under_5_share"] <= 0.15
        assert 0.04 <= w["poverty_rate"] <= 0.50
        assert 0.0 <= w["informal_housing_pct"] <= 50.0
        assert 0.05 <= w["outdoor_worker_share"] <= 0.50
        assert 15.0 <= w["cooling_access_pct"] <= 95.0
        assert 1.0 <= w["tree_canopy_pct"] <= 35.0
        assert 0.30 <= w["built_up_fraction"] <= 0.95
        assert w["sensitive_facilities_count"] >= 10
        assert "zone" in w and len(w["zone"]) > 0


def test_delhi_and_hyderabad_benchmark_wards():
    """Verify authentic benchmark wards for Delhi MCD and Hyderabad GHMC."""
    delhi_wards = demographics.list_municipal_wards("Delhi")
    assert len(delhi_wards) >= 12
    for dw in delhi_wards:
        assert dw["ward_id"].startswith("MCD-")
        assert dw["population"] > 50000
        assert dw["built_up_fraction"] > 0.50

    hyd_wards = demographics.list_municipal_wards("Hyderabad")
    assert len(hyd_wards) >= 12
    for hw in hyd_wards:
        assert hw["ward_id"].startswith("GHMC-")
        assert hw["population"] > 50000
        assert hw["cooling_access_pct"] > 0


def test_get_ward_profile_lookup():
    """Verify ward lookup by ID, name, substring, and digits."""
    # Match by ID
    w1 = demographics.get_ward_profile("Ahmedabad", "AMC-01")
    assert w1 is not None
    assert w1["ward_name"] == "Navrangpura"
    assert w1["zone"] == "West"

    # Match by Name
    w_khadia = demographics.get_ward_profile("Ahmedabad", "Khadia")
    assert w_khadia is not None
    assert w_khadia["ward_id"] == "AMC-07"
    assert w_khadia["zone"] == "Central"

    # Substring match (case-insensitive)
    w_sub = demographics.get_ward_profile("Ahmedabad", "danilimda")
    assert w_sub is not None
    assert w_sub["ward_id"] == "AMC-21"

    # Match by index digit
    w_digit = demographics.get_ward_profile("Ahmedabad", "48")
    assert w_digit is not None
    assert w_digit["ward_name"] == "Maktampura"

    # Non-existent ward
    assert demographics.get_ward_profile("Ahmedabad", "non_existent_ward_999") is None


def test_fetch_municipal_ward_demographics():
    """Verify dedicated municipal ward demographic retrieval returns authentic benchmark record."""
    result = demographics.fetch_municipal_ward_demographics("Ahmedabad", "AMC-07")
    assert result["city"] == "Ahmedabad"
    assert result["ward_id"] == "AMC-07"
    assert result["ward_name"] == "Khadia"
    assert result["zone"] == "Central"
    assert result["population_density"] > 35000.0  # Dense walled city core
    assert result["source"] == "Municipal Corporation Benchmark"
    assert result["synthetic"] is False
    assert result["fallback"] is False
    assert result["vulnerability_indicators"]["composite_vulnerability"] > 0.40


def test_worldpop_raster_sampling_with_geotiff(tmp_path):
    """Verify WorldPop raster sampling via Rasterio window extraction on a real GeoTIFF."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    tif_path = tmp_path / "worldpop_test.tif"
    transform = from_origin(72.565, 23.025, 0.001, 0.001)
    data = np.full((10, 10), 140.0, dtype=np.float32)  # 140 people per 100m grid cell -> 14,000 / km²
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    result = demographics.sample_worldpop_raster(
        lat=23.020,
        lon=72.570,
        raster_path=str(tif_path),
        area_km2=2.5,
    )
    assert result["sampled"] is True
    assert result["pixel_headcount"] == 140.0
    assert result["population_density"] == 14000.0
    assert result["total_population"] == 35000.0
    assert result["resolution_m"] == 100


def test_ghsl_raster_sampling_with_geotiff(tmp_path):
    """Verify GHSL raster sampling of built-up surface fraction via Rasterio."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    tif_path = tmp_path / "ghsl_built_s_test.tif"
    transform = from_origin(72.565, 23.025, 0.001, 0.001)
    data = np.full((10, 10), 0.78, dtype=np.float32)  # 78% built-up surface
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    result = demographics.sample_ghsl_raster(
        lat=23.020,
        lon=72.570,
        raster_path=str(tif_path),
        product="built_s",
    )
    assert result["sampled"] is True
    assert result["built_up_fraction"] == 0.78
    assert result["building_density"] == 0.78


def test_fetch_worldpop_raster_sampling_integration(tmp_path, monkeypatch):
    """Verify fetch_worldpop with sample_raster=True produces analysis-ready density."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return {
            "data": [{"id": "wp_2020_ind", "popyear": "2020", "desc": "India 2020 Population", "resolution": "100m"}]
        }
    monkeypatch.setattr(demographics, "get_json", mock_get)

    tif_path = tmp_path / "worldpop_integration.tif"
    transform = from_origin(72.565, 23.025, 0.001, 0.001)
    data = np.full((10, 10), 165.0, dtype=np.float32)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data, 1)

    res = asyncio.run(
        demographics.fetch_worldpop(
            city="Ahmedabad",
            year=2020,
            lat=23.020,
            lon=72.570,
            area_km2=2.0,
            sample_raster=True,
            raster_path=str(tif_path),
        )
    )
    assert res["catalog_only"] is False
    assert res["metadata"]["analysis_ready"] is True
    assert res["population_density"] == 16500.0
    assert res["total_population"] == 33000.0
    assert res["age_groups"]["elderly_share"] > 0
    assert res["vulnerability_indicators"]["composite_vulnerability"] > 0


def test_fetch_ghsl_raster_sampling_integration(tmp_path, monkeypatch):
    """Verify fetch_ghsl with sample_raster=True produces analysis-ready built-up fraction."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    async def mock_get(url, params=None, headers=None, timeout=30.0):
        return {"features": [{"id": "jrc_ghsl", "properties": {"datetime": "2020-01-01T00:00:00Z"}, "assets": {}}]}
    monkeypatch.setattr(demographics, "get_json", mock_get)

    tif_path = tmp_path / "ghsl_integration.tif"
    transform = from_origin(72.565, 23.025, 0.001, 0.001)
    data = np.full((10, 10), 0.82, dtype=np.float32)
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=10, width=10, count=1, dtype=data.dtype, crs="EPSG:4326", transform=transform
    ) as dst:
        dst.write(data, 1)

    res = asyncio.run(
        demographics.fetch_ghsl(
            lat=23.020,
            lon=72.570,
            city="Ahmedabad",
            sample_raster=True,
            raster_path=str(tif_path),
        )
    )
    assert res["catalog_only"] is False
    assert res["metadata"]["analysis_ready"] is True
    assert res["built_up_fraction"] == 0.82
    assert res["building_density"] == 0.82

