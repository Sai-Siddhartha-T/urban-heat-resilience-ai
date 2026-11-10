"""Empirical challenger test suite for Milestone 2 ML spatial partitioning and AI numeric guardrails."""

import math
import numpy as np
import pytest
from shapely.geometry import Point, LineString, Polygon, mapping

from app.db import init_db
from app.services.ml import assign_spatial_partitions, extract_coordinates, train
from app.services.ai import (
    validate_numeric_guardrails,
    extract_numbers_from_facts,
    NUMERIC_MEASUREMENT_PATTERN,
)
from app.services.data import FEATURES


# =====================================================================
# 1. SPATIAL PARTITIONING EMPIRICAL STRESS TESTS
# =====================================================================

def make_zone_features(coords_list, geoms=None, extra_props=None):
    """Generate synthetic GeoJSON features with specified coordinates or geometries."""
    features = []
    for i, pt in enumerate(coords_list):
        p = {
            "id": f"zone_{i}",
            "name": f"Zone {i}",
            "longitude": float(pt[0]),
            "latitude": float(pt[1]),
            "observed_suhii": 2.5 + 0.1 * (i % 10),
            "lst": 38.0 + 0.2 * (i % 10),
        }
        for f in FEATURES:
            p[f] = 0.1 * (i % 5 + 1)
        if extra_props and i in extra_props:
            p.update(extra_props[i])

        feat = {"type": "Feature", "properties": p}
        if geoms and i < len(geoms):
            feat["geometry"] = geoms[i]
        else:
            x, y = pt[0], pt[1]
            poly = Polygon([
                [x - 0.01, y - 0.01],
                [x + 0.01, y - 0.01],
                [x + 0.01, y + 0.01],
                [x - 0.01, y + 0.01],
                [x - 0.01, y - 0.01],
            ])
            feat["geometry"] = mapping(poly)
        features.append(feat)
    return features


class TestSpatialClusteringStress:
    """Probing assign_spatial_partitions() across size boundaries and pathological geometries."""

    def test_zone_count_3_raises_value_error(self):
        """Under-threshold zone counts (<5) must raise ValueError."""
        features = make_zone_features([[72.5, 23.0], [72.6, 23.1], [72.7, 23.2]])
        with pytest.raises(ValueError, match="Need at least 5 zones"):
            assign_spatial_partitions(features)

    def test_zone_count_4_raises_value_error(self):
        """Boundary count of 4 zones must also raise ValueError."""
        features = make_zone_features([[72.5, 23.0], [72.6, 23.1], [72.7, 23.2], [72.8, 23.3]])
        with pytest.raises(ValueError, match="Need at least 5 zones"):
            assign_spatial_partitions(features)

    def test_zone_count_5_minimal_valid(self):
        """5-zone minimal city: Train=3, Val=1, Test=1, Buffer=0."""
        coords = [[72.5 + 0.05 * i, 23.0 + 0.05 * i] for i in range(5)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 5
        assert partitions.count("training") == 3
        assert partitions.count("validation") == 1
        assert partitions.count("test") == 1
        assert "Small-area spatial ranking" in method
        assert set(blocks) == {0, 3, 5}

    def test_zone_count_8_quantile_split(self):
        """8-zone configuration: 4-block quantile split (2 train, 1 val, 1 test blocks)."""
        coords = [[72.5 + 0.02 * i, 23.0 + 0.03 * i] for i in range(8)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 8
        assert partitions.count("training") == 4
        assert partitions.count("validation") == 2
        assert partitions.count("test") == 2
        assert "4-block spatial quantile" in method

    def test_zone_count_12_quantile_split(self):
        """12-zone configuration: 4-block quantile split."""
        coords = [[72.5 + 0.02 * i, 23.0 + 0.03 * i] for i in range(12)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 12
        assert partitions.count("training") == 6
        assert partitions.count("validation") == 3
        assert partitions.count("test") == 3
        assert "4-block spatial quantile" in method

    def test_zone_count_25_kmeans_or_quantile(self):
        """25-zone configuration: 6-block partitioning with train, val, buffer, test."""
        coords = [[72.5 + 0.01 * (i % 5), 23.0 + 0.01 * (i // 5)] for i in range(25)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 25
        assert partitions.count("training") >= 3
        assert partitions.count("validation") >= 1
        assert partitions.count("test") >= 1
        assert partitions.count("buffer") >= 1

    def test_zone_count_50_large_city(self):
        """50-zone configuration: ensures non-empty partitions and proper spatial blocks."""
        np.random.seed(42)
        coords = [[72.5 + np.random.uniform(0, 0.2), 23.0 + np.random.uniform(0, 0.2)] for _ in range(50)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 50
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0
        assert partitions.count("buffer") > 0
        assert partitions.count("training") + partitions.count("validation") + partitions.count("test") + partitions.count("buffer") == 50

    def test_collinear_zones_exact_same_longitude(self):
        """Pathological: All zones on the exact same meridian (var[lon] == 0)."""
        coords = [[72.5700, 23.00 + 0.01 * i] for i in range(16)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 16
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0
        assert "axis 1" in method or "KMeans" in method

    def test_collinear_zones_exact_same_latitude(self):
        """Pathological: All zones on the exact same parallel (var[lat] == 0)."""
        coords = [[72.50 + 0.01 * i, 23.0225] for i in range(16)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 16
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0
        assert "axis 0" in method or "KMeans" in method

    def test_concentric_ring_zones(self):
        """Pathological: Concentric circular/ring polygons around the same center."""
        geoms = []
        for r in range(1, 10):
            outer = [
                [72.5 + r * 0.01 * math.cos(theta), 23.0 + r * 0.01 * math.sin(theta)]
                for theta in np.linspace(0, 2 * math.pi, 16)
            ]
            if r == 1:
                poly = Polygon(outer)
            else:
                inner = [
                    [72.5 + (r - 0.5) * 0.01 * math.cos(theta), 23.0 + (r - 0.5) * 0.01 * math.sin(theta)]
                    for theta in np.linspace(0, 2 * math.pi, 16)
                ]
                poly = Polygon(outer, [inner])
            geoms.append(mapping(poly))

        coords = [[72.5, 23.0] for _ in range(9)]
        features = make_zone_features(coords, geoms=geoms)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 9
        assert partitions.count("training") >= 2
        assert partitions.count("validation") >= 1
        assert partitions.count("test") >= 1

    def test_zero_area_geometries(self):
        """Pathological: Zero-area geometries (Points, LineStrings, collapsed Polygons)."""
        geoms = [
            mapping(Point(72.5 + 0.01 * i, 23.0 + 0.01 * i)) if i < 3
            else mapping(LineString([[72.5 + 0.01 * i, 23.0], [72.5 + 0.01 * i, 23.05]])) if i < 6
            else mapping(Polygon([[72.5 + 0.01 * i, 23.0], [72.5 + 0.01 * i, 23.0], [72.5 + 0.01 * i, 23.0]]))
            for i in range(10)
        ]
        coords = [[72.5 + 0.01 * i, 23.0 + 0.01 * i] for i in range(10)]
        features = make_zone_features(coords, geoms=geoms)
        
        extracted = extract_coordinates(features)
        assert len(extracted) == 10
        assert np.all(np.isfinite(extracted))

        blocks, partitions, method = assign_spatial_partitions(features)
        assert len(partitions) == 10
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0

    def test_identical_repeated_coordinates_fallback(self):
        """Pathological: Exactly identical coordinates repeated 18 times (zero variance)."""
        coords = [[72.5, 23.0] for _ in range(18)]
        features = make_zone_features(coords)
        blocks, partitions, method = assign_spatial_partitions(features)

        assert len(partitions) == 18
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0


class TestModelTrainingWithCustomPartitions:
    """Stress test train() on synthetic dataset with custom spatial partitions."""

    def test_train_end_to_end_custom_zones(self):
        """Train pipeline runs successfully on 16 custom zones partitioned dynamically."""
        init_db()
        coords = [[72.5 + 0.01 * (i % 4), 23.0 + 0.01 * (i // 4)] for i in range(16)]
        features = make_zone_features(coords)
        data = {
            "type": "FeatureCollection",
            "metadata": {"city": "Testville", "generated_at": "2026-11-09T00:00:00Z"},
            "features": features,
        }
        artifact = train(data)
        assert artifact["winner"] in ["Random Forest", "XGBoost", "LightGBM"]
        assert len(artifact["evaluations"]) == 3
        assert artifact["split"]["training"] > 0
        assert artifact["split"]["validation"] > 0
        assert artifact["split"]["test"] > 0
        assert np.isfinite(artifact["interval"])

    def test_zone_counts_60_to_89_partition_cleanly(self):
        """Custom GeoJSONs with N in [60, 89] zones partition cleanly without partition cell threshold errors."""
        init_db()
        for n in [60, 75, 89]:
            coords = [[72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)] for i in range(n)]
            features = make_zone_features(coords)
            data = {
                "type": "FeatureCollection",
                "metadata": {"city": f"Test{n}", "generated_at": "2026-11-09T00:00:00Z"},
                "features": features,
            }
            artifact = train(data)
            assert artifact["split"]["validation"] >= 1
            assert artifact["split"]["test"] >= 1
            assert artifact["split"]["training"] >= 3
            assert np.isfinite(artifact["interval"])


# =====================================================================
# 2. AI NUMERIC GUARDRAIL ADVERSARIAL STRESS TESTS
# =====================================================================

class TestAINumericGuardrails:
    """Probing regex pipeline in backend/app/services/ai.py against adversarial text."""

    @pytest.fixture
    def mock_facts(self):
        return {
            "prediction": {
                "suhii_c": 3.42,
                "lst_c": 41.8,
                "interval": [2.85, 3.99],
            },
            "drivers": {"impervious_pct": 0.45, "tree_canopy_pct": -0.32},
            "risk": {"risk_score": 0.72, "hazard": 0.81, "exposure": 0.65, "vulnerability": 0.70},
            "constraints": {"available_land_pct": 15.0, "roof_pct": 32.5, "road_pct": 20.0},
            "scenarios": [{"cooling_celsius": 1.25, "water_m3_day": 250.0, "budget_used": 12500.0}],
        }

    def test_extract_numbers_from_facts(self, mock_facts):
        """Verify recursive fact extraction extracts exact, rounded, and integer values."""
        numbers = extract_numbers_from_facts(mock_facts)
        assert 3.42 in numbers
        assert 3.4 in numbers
        assert 3 in numbers
        assert 41.8 in numbers
        assert 42 in numbers
        assert 250.0 in numbers
        assert 12500.0 in numbers

    def test_benign_domain_entities_pass(self, mock_facts):
        """Valid domain entity numbers (Sentinel-2, Landsat-8, PM2.5, years) must pass."""
        text = (
            "Sentinel-2 captured imagery alongside Landsat-8 in 2024. "
            "Ambient PM2.5 and PM10 concentrations were analyzed under WGS84 coordinates. "
            "1. First finding indicates high hazard. 2. Second finding recommends cool roofs."
        )
        validate_numeric_guardrails(text, mock_facts)

    def test_supported_facts_in_prose_pass(self, mock_facts):
        """Numbers present in facts dictionary (within tolerance) must pass."""
        text = (
            "The model predicted a SUHII of 3.4°C and a land surface temperature of 41.8°C. "
            "Available roof area is 32.5% while open land is 15%."
        )
        validate_numeric_guardrails(text, mock_facts)

    def test_supported_facts_with_approximate_tolerance_pass(self, mock_facts):
        """Fact numbers within 0.15 absolute or 5% relative tolerance must pass."""
        text = "Predicted SUHII is 3.4°C and LST is 42°C."
        validate_numeric_guardrails(text, mock_facts)

    def test_hallucinated_temperature_rejected(self, mock_facts):
        """Adversarial: Fabricated extreme temperature must be blocked."""
        text = "The surface temperature dropped by 45.2°C across the neighborhood."
        with pytest.raises(ValueError, match="unsupported numeric prose: 45.2°C"):
            validate_numeric_guardrails(text, mock_facts)

    def test_hallucinated_cooling_rejected(self, mock_facts):
        """Adversarial: Fabricated cooling statistic must be blocked."""
        text = "Implementing roof gardens will reduce surface heat by 8.9°C."
        with pytest.raises(ValueError, match="unsupported numeric prose: 8.9°C"):
            validate_numeric_guardrails(text, mock_facts)

    def test_hallucinated_percentage_rejected(self, mock_facts):
        """Adversarial: Fabricated percentage must be blocked."""
        text = "Over 88% of urban roofs should be converted immediately."
        with pytest.raises(ValueError, match="unsupported numeric prose: 88%"):
            validate_numeric_guardrails(text, mock_facts)

    def test_hallucinated_water_volume_rejected(self, mock_facts):
        """Adversarial: Fabricated water consumption must be blocked."""
        text = "The proposed scenario consumes 950 m³/day of irrigation water."
        with pytest.raises(ValueError, match="unsupported numeric prose: 950 m³/day"):
            validate_numeric_guardrails(text, mock_facts)

    def test_hallucinated_currency_rejected(self, mock_facts):
        """Adversarial: Fabricated budget / currency must be blocked."""
        text = "The total capital expenditure exceeds $99000."
        with pytest.raises(ValueError, match="unsupported numeric prose: 99000"):
            validate_numeric_guardrails(text, mock_facts)

    def test_sneaky_embedded_identifier_numbers_do_not_falsely_fail(self, mock_facts):
        """Sneaky identifiers with digits (model_v2_run3, feature_4) must not trigger numeric check."""
        text = "Algorithm model_v2_run3 analyzed feature_4 in zone_01 using cluster_id_9."
        validate_numeric_guardrails(text, mock_facts)

    def test_hexadecimal_codes_do_not_falsely_fail(self, mock_facts):
        """Hex strings (0x1A4F) must not trigger false positive numeric rejections."""
        text = "Memory pointer 0x1A4F and color code #4A90E2 were processed."
        validate_numeric_guardrails(text, mock_facts)

    def test_regex_backtracking_vulnerability_on_unrecognized_units(self):
        """Regression test: '10m' and '30m' do not backtrack into standalone '1' or '3'."""
        matches_10m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("10m")]
        assert "1" not in matches_10m
        assert matches_10m == ["10m"]

        matches_30m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("30m")]
        assert "3" not in matches_30m
        assert matches_30m == ["30m"]

        # Valid imagery prose with 10m does not falsely fail validation when 1 is not in facts
        facts_without_1 = {"prediction": {"suhii_c": 25.0}}
        validate_numeric_guardrails("Sentinel-2 captured 10m resolution imagery.", facts_without_1)

    def test_scientific_notation_mutilation(self):
        """Regression test: Scientific notation like 1.85e-3 is parsed as a single floating point number."""
        matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3")]
        assert matches == ["1.85e-3"]

    def test_zero_rounding_leakage(self, mock_facts):
        """Regression test: Fabricated number in (-0.15, 0.15) is rejected and does not leak through zero-rounding."""
        text = "The microclimate cooled by 0.1°C."
        with pytest.raises(ValueError, match="unsupported numeric prose: 0.1°C"):
            validate_numeric_guardrails(text, mock_facts)
