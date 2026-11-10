"""Shared provenance and freshness contracts for acquired evidence.

This module deliberately does not manufacture observations.  It only describes
what an adapter actually returned, when it was retrieved, and how it may be
used by the product.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


CATEGORY_ALIASES = {
    "openaq": "air_quality", "monitoring": "air_quality",
    "earth_engine": "satellite", "stac": "satellite",
    "sentinel_indices": "satellite", "copernicus": "satellite",
    "landsat": "satellite", "sentinel": "satellite", "modis": "satellite",
    "worldcover": "land_cover", "srtm": "elevation",
    "worldpop": "population", "ghsl": "population",
    "nasa_power": "weather", "osm": "infrastructure",
}


def canonical_category(category: str) -> str:
    return CATEGORY_ALIASES.get(category, category)


def _source_times(value: Any) -> str | list[str] | None:
    """Keep source dates, converting epoch milliseconds only when supplied."""
    if isinstance(value, list):
        times = [_source_times(item) for item in value]
        return [item for item in times if isinstance(item, str)] or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    return value if isinstance(value, str) and value else None


def provenance(
    *,
    source: str,
    category: str,
    city: str | None,
    observation_time: str | list[str] | None = None,
    coverage: str | None = None,
    resolution: str | int | float | None = None,
    units: dict[str, str] | None = None,
    processing: str | None = None,
    quality: str | None = None,
    status: str = "latest_available",
    mode: str = "live",
    kind: str = "observed",
    retrieved_at: str | None = None,
    freshness: str = "unknown",
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Return the API-wide evidence metadata shape.

    ``mode`` is either ``live`` or ``demo``.  A live asset being present never
    implies that it is a validated heat-analysis input.
    """
    return {
        "source": source,
        "category": canonical_category(category),
        "mode": mode,
        "kind": kind,
        "status": status,
        "retrieved_at": retrieved_at or utc_now(),
        "observation_time": _source_times(observation_time),
        "city": city,
        "coverage": coverage,
        "resolution": str(resolution) if resolution is not None else None,
        "units": ({"measurement": units} if isinstance(units, str) else units) if units else {},
        "processing": processing,
        "quality": quality,
        "freshness": freshness,
        "analysis_ready": False,
        "limitations": limitations or [],
    }


def asset_provenance(result: dict[str, Any], *, city: str, category: str) -> dict[str, Any]:
    """Normalize adapter output without guessing missing source metadata."""
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    supplied = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
    metadata = {**metadata, **supplied}
    source = str(metadata.get("source") or result.get("source") or category)
    observation = (
        metadata.get("observation_time")
        or metadata.get("acquisition_date")
        or metadata.get("acquisition_dates")
        or result.get("acquisition_date")
        or result.get("observation_time")
        or result.get("acquisition_dates_ms")
        or result.get("observation_period")
    )
    raw_weather = result.get("data") if isinstance(result.get("data"), dict) else {}
    current = raw_weather.get("current") or {}
    if not observation and current.get("time"):
        observation = current["time"]
    if not observation and raw_weather.get("hourly", {}).get("time"):
        times = raw_weather["hourly"]["time"]
        observation = [times[0], times[-1]]
    resolution = metadata.get("resolution") or metadata.get("resolution_m") or result.get("resolution") or result.get("resolution_m") or result.get("native_resolution")
    if isinstance(resolution, (int, float)):
        resolution = f"{resolution} m"
    raw_units = metadata.get("units") or result.get("units") or raw_weather.get("current_units") or raw_weather.get("hourly_units") or {}
    if isinstance(raw_units, str):
        units = {"depth_below_ground_m" if "mbgl" in raw_units else "measurement": raw_units}
    elif isinstance(raw_units, dict):
        units = raw_units
    else:
        units = {}
    is_weather = canonical_category(category) == "weather"
    kind = metadata.get("kind") or result.get("kind") or ("modelled" if is_weather else "observed")
    status = metadata.get("status") or result.get("status") or ("forecast" if "forecast" in source.lower() else "latest_available")
    coverage = metadata.get("coverage") or metadata.get("scope") or result.get("scope")
    if not coverage and result.get("latitude") is not None and result.get("longitude") is not None:
        coverage = f"Point request at {result['latitude']}, {result['longitude']}; not a citywide observation."
    return provenance(
        source=source,
        category=category,
        city=city,
        observation_time=observation,
        coverage=coverage,
        resolution=resolution,
        units=units,
        processing=metadata.get("processing") or metadata.get("cloud_filter") or result.get("method") or result.get("note"),
        quality=metadata.get("quality") or result.get("quality"),
        status=status,
        mode="demo" if bool(result.get("synthetic") or metadata.get("synthetic")) else "live",
        kind=kind,
        retrieved_at=metadata.get("retrieved_at") or result.get("retrieved_at"),
        freshness=metadata.get("freshness", "unknown"),
        limitations=metadata.get("limitations") or result.get("limitations") or [],
    )
