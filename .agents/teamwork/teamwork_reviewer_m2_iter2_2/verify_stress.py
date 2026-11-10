import os
import tempfile
os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp()
import sys
sys.path.insert(0, "backend")

from app.services.ai import (
    NUMERIC_MEASUREMENT_PATTERN,
    ENTITY_WHITELIST,
    extract_numbers_from_facts,
    validate_numeric_guardrails,
)
from app.services.ml import assign_spatial_partitions, train
from shapely.geometry import Polygon, mapping

def run_regex_suite():
    print("=== 1. Testing Regex & Atomic Grouping ===")
    # Identifiers
    test_ids = ["model_v2_run3", "zone_01", "temp_2m", "var_10", "x1", "a0b", "_hidden12"]
    for tid in test_ids:
        matches = list(NUMERIC_MEASUREMENT_PATTERN.finditer(tid))
        assert len(matches) == 0, f"Identifier {tid} produced false positive matches: {[m.group(0) for m in matches]}"

    # Hex codes
    hex_codes = ["#4A90E2", "#FFFFFF", "#000000", "#123456", "#abcdef", "0x1A4F", "#0E2"]
    for hc in hex_codes:
        matches = list(NUMERIC_MEASUREMENT_PATTERN.finditer(hc))
        assert len(matches) == 0, f"Hex code {hc} produced false positive matches: {[m.group(0) for m in matches]}"

    # Metric units and suffixes
    units_tests = [
        ("10m", "10m", "m", 10.0),
        ("30m", "30m", "m", 30.0),
        ("100 km", "100 km", "km", 100.0),
        ("25.5 hectares", "25.5 hectares", "hectares", 25.5),
        ("50ha", "50ha", "ha", 50.0),
        ("1.5 km²", "1.5 km²", "km²", 1.5),
        ("500 m3/day", "500 m3/day", "m3/day", 500.0),
        ("12 cm", "12 cm", "cm", 12.0),
        ("5 mm", "5 mm", "mm", 5.0),
        ("-2.5°C", "-2.5°C", "°C", -2.5),
        ("−3.2 deg C", "−3.2 deg C", "deg C", -3.2),
        ("5000 USD", "5000 USD", "USD", 5000.0),
        ("12500 INR", "12500 INR", "INR", 12500.0),
        ("5000 $", "5000 $", "$", 5000.0),
        ("12500 ₹", "12500 ₹", "₹", 12500.0),
        ("45%", "45%", "%", 45.0),
    ]
    for text, exp_full, exp_unit, exp_val in units_tests:
        matches = list(NUMERIC_MEASUREMENT_PATTERN.finditer(text))
        assert len(matches) == 1, f"Expected 1 match for {text}, got {len(matches)}: {[m.group(0) for m in matches]}"
        m = matches[0]
        val = float(m.group("value"))
        if m.group("sign") in ["-", "−"]:
            val = -val
        assert val == exp_val, f"Val mismatch: {val} != {exp_val}"
        unit = m.group("unit").strip() if m.group("unit") else ""
        assert unit.lower() == exp_unit.lower(), f"Unit mismatch: {unit} != {exp_unit}"

    # Scientific notation
    sci_tests = [
        ("1.85e-3", 1.85e-3),
        ("2.5E4", 2.5e4),
        ("-1.2e-5", -1.2e-5),
        ("+3.0e+2", 3.0e2),
        ("6.022e23", 6.022e23),
    ]
    for text, exp_val in sci_tests:
        matches = list(NUMERIC_MEASUREMENT_PATTERN.finditer(text))
        assert len(matches) == 1, f"Expected 1 match for {text}, got {len(matches)}"
        m = matches[0]
        val = float(m.group("value"))
        if m.group("sign") in ["-", "−"]:
            val = -val
        assert abs(val - exp_val) < 1e-12, f"Sci mismatch: {val} != {exp_val}"

    # Backtracking prevention
    backtrack_tests = ["10xyz", "30abc", "100apples", "123foo_bar"]
    for bt in backtrack_tests:
        matches = list(NUMERIC_MEASUREMENT_PATTERN.finditer(bt))
        assert len(matches) == 0, f"Backtrack failure on {bt}: matches={[(m.group(0), m.span()) for m in matches]}"

    print("Regex suite passed!")


def run_fact_grounding_suite():
    print("=== 2. Testing Fact Grounding & Zero Tolerance ===")
    # Case A: facts contain fractional value < 1.0, e.g. 0.42
    facts_a = {"impervious_pct": 0.42}
    numbers_a = extract_numbers_from_facts(facts_a)
    # Ensure 0 is NOT in numbers_a
    assert 0 not in numbers_a, f"Zero leaked into fact numbers for 0.42: {numbers_a}"
    assert 0.42 in numbers_a
    assert 0.4 in numbers_a

    # Hallucinated 0.1°C against facts_a must be rejected
    try:
        validate_numeric_guardrails("Cooled by 0.1°C", facts_a)
        assert False, "Failed to reject hallucinated 0.1°C when fact is 0.42"
    except ValueError as e:
        assert "0.1°C" in str(e)

    # Hallucinated 0.05 against facts_a must be rejected
    try:
        validate_numeric_guardrails("Reduced by 0.05", facts_a)
        assert False, "Failed to reject hallucinated 0.05 when fact is 0.42"
    except ValueError as e:
        assert "0.05" in str(e)

    # Case B: facts genuinely contain 0.0
    facts_b = {"cooling_celsius": 0.0}
    numbers_b = extract_numbers_from_facts(facts_b)
    assert 0.0 in numbers_b

    # Valid genuine 0.0 in prose should pass
    validate_numeric_guardrails("The cooling effect was 0.0°C", facts_b)
    validate_numeric_guardrails("The cooling effect was 0°C", facts_b)

    # But 0.1°C should NOT pass when genuine fact is 0.0!
    # Because fn == 0 requires abs(raw_val) < 1e-6!
    try:
        validate_numeric_guardrails("The cooling effect was 0.1°C", facts_b)
        assert False, "Failed to reject 0.1°C when fact is 0.0"
    except ValueError as e:
        assert "0.1°C" in str(e)

    # Case C: facts contain value >= 1.0, e.g. 3.42
    facts_c = {"suhii": 3.42}
    numbers_c = extract_numbers_from_facts(facts_c)
    assert 3 in numbers_c
    assert 3.4 in numbers_c
    assert 3.42 in numbers_c

    # In prose: 3.4°C passes, 3.5°C passes (abs(3.5 - 3.42) = 0.08 < 0.15)
    validate_numeric_guardrails("SUHII is 3.4°C", facts_c)
    validate_numeric_guardrails("SUHII is 3.5°C", facts_c)
    # 3.8°C fails (abs(3.8 - 3.42) = 0.38 >= 0.15 and 0.38 / 3.42 = 0.11 > 0.05)
    try:
        validate_numeric_guardrails("SUHII is 3.8°C", facts_c)
        assert False, "Failed to reject 3.8°C"
    except ValueError as e:
        assert "3.8°C" in str(e)

    print("Fact grounding suite passed!")


def run_spatial_clustering_suite():
    print("=== 3. Testing Spatial Clustering Scaling ===")
    from app.services.data import FEATURES

    def make_features(n):
        feats = []
        for i in range(n):
            pt = [72.5 + 0.01 * (i % 8), 23.0 + 0.01 * (i // 8)]
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
            poly = Polygon([
                [pt[0] - 0.005, pt[1] - 0.005],
                [pt[0] + 0.005, pt[1] - 0.005],
                [pt[0] + 0.005, pt[1] + 0.005],
                [pt[0] - 0.005, pt[1] + 0.005],
                [pt[0] - 0.005, pt[1] - 0.005],
            ])
            feats.append({"type": "Feature", "properties": p, "geometry": mapping(poly)})
        return feats

    # Test N in [60, 89] as well as boundaries
    test_ns = [60, 65, 70, 75, 80, 85, 89, 90, 100, 324]
    for n in test_ns:
        min_req = max(1, min(15, n // 6))
        feats = make_features(n)
        blocks, partitions, method = assign_spatial_partitions(feats)
        tr_count = partitions.count("training")
        val_count = partitions.count("validation")
        test_count = partitions.count("test")
        buffer_count = partitions.count("buffer")

        assert len(partitions) == n, f"Length mismatch for N={n}"
        assert min(tr_count, val_count, test_count) >= min_req, (
            f"Partition smaller than min_required ({min_req}) for N={n}: tr={tr_count}, val={val_count}, test={test_count}"
        )
        if n >= 90:
            assert min_req == 15, f"Expected min_req=15 for N={n}, got {min_req}"
        elif n == 60:
            assert min_req == 10, f"Expected min_req=10 for N=60, got {min_req}"
        elif n == 89:
            assert min_req == 14, f"Expected min_req=14 for N=89, got {min_req}"

        print(f"N={n:3d}: min_req={min_req:2d}, tr={tr_count:3d}, val={val_count:2d}, buf={buffer_count:2d}, test={test_count:2d}, method={method[:25]}...")

    print("Spatial clustering suite passed!")


if __name__ == "__main__":
    run_regex_suite()
    run_fact_grounding_suite()
    run_spatial_clustering_suite()
    print("\nALL ADVERSARIAL STRESS TEST SUITES PASSED CLEANLY!")


def run_train_stress_suite():
    print("=== 4. Testing End-to-End train() on N in [60, 89] ===")
    from app.db import init_db
    from app.services.data import FEATURES
    init_db()

    def make_features(n):
        feats = []
        for i in range(n):
            pt = [72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)]
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
            poly = Polygon([
                [pt[0] - 0.005, pt[1] - 0.005],
                [pt[0] + 0.005, pt[1] - 0.005],
                [pt[0] + 0.005, pt[1] + 0.005],
                [pt[0] - 0.005, pt[1] + 0.005],
                [pt[0] - 0.005, pt[1] - 0.005],
            ])
            feats.append({"type": "Feature", "properties": p, "geometry": mapping(poly)})
        return feats

    for n in [60, 61, 65, 70, 75, 80, 85, 88, 89]:
        data = {
            "type": "FeatureCollection",
            "metadata": {"city": f"City{n}", "generated_at": "2026-11-09T00:00:00Z"},
            "features": make_features(n),
        }
        art = train(data)
        min_req = max(1, min(15, n // 6))
        assert art["split"]["training"] >= min_req * 3
        assert art["split"]["validation"] >= min_req
        assert art["split"]["test"] >= min_req
        print(f"N={n:2d}: SUCCESS! winner={art['winner']}, split={art['split']}")

    print("Train stress suite passed!")


if __name__ == "__main__":
    run_train_stress_suite()
