"""Strict grounding and numeric guardrails to eliminate LLM hallucinations."""

import re
from typing import Any
import numpy as np

# Whitelist benign domain entities with digits that must NOT trigger numeric audits
ENTITY_WHITELIST = re.compile(
    r"\b(?:Sentinel-[12345]|Landsat-[789]|MODIS|GHSL(?:-\d+)?|WorldCover|SRTM|WGS84|EPSG:\d+|PM(?:2\.5|10)|H3-\d+|ISO-\d+|COVID-19"
    r"|(?:10|15|20|30|60|100|250|500|1000)[-\s]?m\b|\b[125][-\s]?km\b)\b",
    re.IGNORECASE,
)
ORDERED_LIST_MARKER = re.compile(r"(?:^|\n|\.\s+)\d+\.\s+")
YEAR_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b")

# Regex targeting physical measurements, percentages, ranges, and signed numbers
NUMERIC_MEASUREMENT_PATTERN = re.compile(
    r"""
    (?<![\w#])                             # Not part of an identifier, hex code, or preceding digits
    (?P<sign>[-+−])?                       # Optional positive or negative sign
    (?=(?P<value>                          # Lookahead captures full numeric literal atomically
        \d+(?:\.\d+)?                      # Integer or decimal
        (?:[eE][-+]?\d+)?                  # Optional scientific exponent notation
    ))(?P=value)                           # Match captured value atomically without backtracking
    (?:\s*(?P<unit>                        # Optional measurement unit
        °[CF]|deg(?:rees)?(?:\s*[CF])?|%|percent|
        m³/day|m3/day|m[²23]|km[²2]|
        kilomet(?:ers?|res?)|km|centimet(?:ers?|res?)|cm|millimet(?:ers?|res?)|mm|hectares?|ha|m(?:eters?|etres?)?|
        USD|INR|\$|₹
    ))?
    (?![a-zA-Z_])                          # Unit or number must not be followed immediately by letters/underscore
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_numbers_from_facts(facts: Any) -> set[float | int]:
    """Recursively collect all finite numeric values present in facts dictionary."""
    found: set[float | int] = set()

    def _walk(obj: Any):
        if isinstance(obj, (int, float)):
            if not isinstance(obj, bool) and np.isfinite(obj):
                val = float(obj)
                found.add(round(val, 2))
                found.add(round(val, 1))
                # Only add integer-rounded values when magnitude >= 1.0 to prevent
                # zero-rounding leakage for small fractions (< 1.0)
                if abs(val) >= 1.0:
                    found.add(int(round(val)))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                _walk(v)

    _walk(facts)
    return found


def validate_numeric_guardrails(text: str, facts: dict[str, Any]) -> None:
    """
    Validates that LLM prose does not contain unsupported or hallucinated numbers.
    Permits whitelisted domain entities, list markers, year dates, and fact numbers within tolerance.
    """
    cleaned = ENTITY_WHITELIST.sub(" ", text)
    cleaned = ORDERED_LIST_MARKER.sub(" ", cleaned)
    cleaned = YEAR_DATE_PATTERN.sub(" ", cleaned)

    fact_numbers = extract_numbers_from_facts(facts)

    for m in NUMERIC_MEASUREMENT_PATTERN.finditer(cleaned):
        raw_val = float(m.group("value"))
        if m.group("sign") in ["-", "−"]:
            raw_val = -raw_val

        # Grounding check: number must match a known fact in context
        is_supported = any(
            (abs(raw_val - fn) < 0.15 if fn != 0 else abs(raw_val) < 1e-6)
            or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
            for fn in fact_numbers
        )
        if not is_supported:
            raise ValueError(
                f"Provider included unsupported numeric prose: {m.group(0).strip()}"
            )


def validate_citations(findings: list[Any], facts: dict[str, Any]) -> None:
    """Verifies that all fact IDs referenced by findings exist in context facts."""
    for finding in findings:
        fact_ids = (
            finding.fact_ids
            if hasattr(finding, "fact_ids")
            else finding.get("fact_ids", [])
        )
        if any(key not in facts for key in fact_ids):
            raise ValueError("Provider cited unsupported evidence")


def validate_action_feasibility(actions: list[str], p: dict[str, Any]) -> None:
    """Verifies that all recommended actions are physically feasible according to simulation."""
    import sys
    ai_mod = sys.modules.get("app.services.ai")
    if ai_mod and hasattr(ai_mod, "simulate"):
        sim_func = ai_mod.simulate
    else:
        from app.services.planning import simulate as sim_func

    p_safe = p if "area_km2" in p else {**p, "area_km2": 1.0}
    for action in actions:
        sim_res = sim_func(p_safe, {action: 5})
        if not sim_res.get("feasible", False):
            raise ValueError(f"Provider suggested an infeasible intervention: {action}")
