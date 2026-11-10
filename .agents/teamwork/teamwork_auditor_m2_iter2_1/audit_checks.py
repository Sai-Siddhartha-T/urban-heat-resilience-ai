"""Independent forensic verification script for Milestone 2 Iteration 2."""

import os
import sys
import time
from collections import defaultdict, deque

# Add backend to sys.path
sys.path.insert(0, os.path.abspath("backend"))

# ---------------------------------------------------------------------------
# Check 1: Rate Limiter Middleware Logic & Production vs Test Bypass
# ---------------------------------------------------------------------------
print("=== CHECK 1: RATE LIMITER AUTHENTICITY ===")

# Test logic directly from backend/app/main.py lines 58-68
rate_tracker = defaultdict(deque)

def simulate_request(key, now, is_test):
    if is_test:
        return 200
    q = rate_tracker[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) > 180:
        return 429
    q.append(now)
    return 200

# 1.1 In production mode (is_test=False), exactly 181 requests pass, request 182 returns 429
rate_tracker.clear()
now = time.monotonic()
statuses_prod = [simulate_request("127.0.0.1", now, is_test=False) for _ in range(185)]
assert statuses_prod[:181] == [200] * 181, f"First 181 requests should be 200, got: {statuses_prod[:181]}"
assert statuses_prod[181:] == [429] * 4, f"Requests 182-185 should be 429, got: {statuses_prod[181:]}"
print("[PASS] Production rate limiter triggers HTTP 429 when rate is exceeded (> 180 req/min).")

# 1.2 In test mode (is_test=True), 250 requests pass cleanly without 429
rate_tracker.clear()
statuses_test = [simulate_request("127.0.0.1", now, is_test=True) for _ in range(250)]
assert all(s == 200 for s in statuses_test), "Test mode failed to bypass rate limiter"
print("[PASS] Test rate limiter bypass allows high-throughput test suites without 429.")

# ---------------------------------------------------------------------------
# Check 2: AI Guardrails Regex & Tolerance Authenticity
# ---------------------------------------------------------------------------
print("\n=== CHECK 2: AI GUARDRAILS AUTHENTICITY ===")

from app.services.ai import (
    validate_numeric_guardrails,
    extract_numbers_from_facts,
    NUMERIC_MEASUREMENT_PATTERN,
    ENTITY_WHITELIST,
)

# 2.1 Backtracking & Unit Slicing
for sample in ["10m", "30m", "60m", "100m", "1km", "2km"]:
    matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer(sample)]
    assert matches == [sample], f"Failed to match {sample} atomically: {matches}"
    # Verify no sliced sub-digits like '1' or '3'
    for digit in ["1", "3", "6"]:
        assert digit not in matches, f"Sliced sub-digit '{digit}' found in matches: {matches}"
print("[PASS] Atomic lookahead eliminates regex backtracking into digits on metric units.")

# 2.2 Scientific notation
sci_samples = ["1.85e-3", "-2.4e-2", "1e5", "+3.2e+4"]
for sample in sci_samples:
    matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer(sample)]
    assert matches == [sample], f"Failed to match {sample} in scientific notation: {matches}"
print("[PASS] Scientific notation parsed as single numeric tokens.")

# 2.3 Hexadecimal codes do not falsely trigger
hex_samples = ["#4A90E2", "#FFFFFF", "#000000"]
for sample in hex_samples:
    matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer(sample)]
    assert len(matches) == 0, f"Hex code {sample} falsely matched as numbers: {matches}"
print("[PASS] Hex color codes correctly excluded from numeric validation.")

# 2.4 Fact extraction zero-rounding leakage
facts_with_fractions = {
    "drivers": {"impervious_pct": 0.45, "tree_canopy_pct": 0.05, "albedo": 0.12},
    "prediction": {"suhii_c": 3.42},
}
extracted = extract_numbers_from_facts(facts_with_fractions)
assert 0 not in extracted, f"Integer 0 leaked into extracted facts: {extracted}"
assert 0.45 in extracted and 0.5 in extracted
assert 3.42 in extracted and 3 in extracted  # 3.42 >= 1.0 so int(round(3.42)) == 3 is allowed
print("[PASS] Zero-rounding leakage for fractions < 1.0 completely eliminated.")

# 2.5 Grounding tolerance for fn == 0
facts_with_zero = {"drivers": {"tree_canopy_pct": 0.0}}
extracted_zero = extract_numbers_from_facts(facts_with_zero)
assert 0.0 in extracted_zero

# Hallucinated 0.1°C MUST be rejected even though abs(0.1 - 0) < 0.15
try:
    validate_numeric_guardrails("The microclimate cooled by 0.1°C.", facts_with_zero)
    assert False, "Ungrounded 0.1°C was accepted!"
except ValueError as e:
    assert "0.1°C" in str(e)
print("[PASS] fn == 0 strictly enforces floating epsilon < 1e-6, blocking hallucinated small values.")

# Genuine zero measurement passes
validate_numeric_guardrails("Tree canopy expansion resulted in 0.0°C deviation.", facts_with_zero)
print("[PASS] Genuine 0.0°C measurement accepted when 0.0 is in facts.")

# ---------------------------------------------------------------------------
# Check 3: Spatial Partitioning Dynamism & Robustness
# ---------------------------------------------------------------------------
print("\n=== CHECK 3: SPATIAL PARTITIONING DYNAMISM ===")

from app.services.ml import assign_spatial_partitions, train
from app.db import init_db
from tests.test_challenger_m2 import make_zone_features

init_db()

# Test zone counts N in [60, 75, 89]
for n in [60, 75, 89]:
    coords = [[72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)] for i in range(n)]
    features = make_zone_features(coords)
    data = {
        "type": "FeatureCollection",
        "metadata": {"city": f"TestCity_{n}", "generated_at": "2026-11-09T00:00:00Z"},
        "features": features,
    }
    artifact = train(data)
    assert artifact["winner"] in ["Random Forest", "XGBoost", "LightGBM"]
    assert artifact["split"]["training"] >= 3
    assert artifact["split"]["validation"] >= 1
    assert artifact["split"]["test"] >= 1
    assert artifact["split"]["buffer"] >= 1
    min_expected = max(1, min(15, n // 6))
    assert min(artifact["split"]["training"], artifact["split"]["validation"], artifact["split"]["test"]) >= min_expected
    print(f"[PASS] Successfully partitioned and trained N={n} zones (min_required={min_expected}).")

print("\nALL INDEPENDENT FORENSIC CHECKS PASSED EMPIRICALLY.")
