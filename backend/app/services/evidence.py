"""Read-only composition of acquired evidence; never generates or trains data."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from shapely.geometry import shape

from app.db import asset_by_id, asset_summaries, assets
from app.provenance import canonical_category
from app.schemas.evidence import EvidenceAsset, EvidenceAssetSummary, MapLayer, RasterGrid
from app.services.data import CITIES


LAYER_SPECS = (
    ("lst", "Observed surface temperature", "lst", "observed", "°C"),
    ("predicted_lst", "Predicted surface temperature", "predicted_lst", "predicted", "°C"),
    ("suhii", "Surface urban heat island intensity", "observed_suhii", "observed", "°C"),
    ("ndvi", "Vegetation · NDVI", "ndvi", "observed", "index"),
    ("building_density", "Built-up density", "building_density", "estimated", "fraction"),
    ("land_cover", "Land cover", "land_cover", "modelled", "class"),
    ("air_quality", "Air-quality monitoring stations", "pollutant_concentration", "observed", None),
    ("weather", "Weather model location", "temperature_2m", "modelled", "°C"),
    ("groundwater", "Groundwater monitoring stations", "depth_below_ground_m", "observed", "m below ground"),
    ("heat_risk", "Heat-risk screening", "risk_score", "modelled", "screening index"),
    ("population", "Population exposure", "population", "modelled", "people"),
    ("interventions", "Proposed interventions", "intervention", "hypothetical", None),
)


def _empty_layer(spec) -> dict[str, Any]:
    identifier, name, variable, kind, unit = spec
    # Estimates share the modelled observation kind; provenance may be estimated.
    return MapLayer(
        id=identifier, name=name, variable=variable, status="unavailable",
        kind="modelled" if kind == "estimated" else kind, unit=unit,
        reason="No georeferenced evidence is available for this layer.",
    ).model_dump()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_geojson(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("type") != "FeatureCollection":
        return None
    features = value.get("features")
    if not isinstance(features, list) or not features:
        return None
    for feature in features:
        try:
            geometry = shape(feature["geometry"])
            west, south, east, north = geometry.bounds
            if geometry.is_empty or not geometry.is_valid or not (
                -180 <= west <= east <= 180 and -90 <= south <= north <= 90
            ):
                return None
        except (KeyError, TypeError, ValueError):
            return None
    return value


def live_assets(city: str, category: str | None = None) -> list[dict[str, Any]]:
    """Exclude demos and legacy unscoped/unparseable evidence at the boundary."""
    result = []
    for asset in assets(city=city, category=canonical_category(category) if category else None, mode="live"):
        payload = asset.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_metadata = payload.get("metadata")
        if not isinstance(payload_metadata, dict):
            payload_metadata = {}
        metadata = asset.get("provenance")
        if not isinstance(metadata, dict):
            continue
        if payload.get("synthetic") is True or payload_metadata.get("synthetic") is True:
            continue
        if metadata.get("city") != city or metadata.get("mode") != "live":
            continue
        try:
            result.append(EvidenceAsset.model_validate(asset).model_dump())
        except ValidationError:
            # Historical, incomplete records remain stored, but are not promoted.
            continue
    return result


def live_asset_summaries(city: str) -> list[dict[str, Any]]:
    """Return validated normal-mode asset metadata without reading payloads."""
    result = []
    for asset in asset_summaries(city=city, mode="live"):
        metadata = asset.get("provenance")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("city") != city or metadata.get("mode") != "live":
            continue
        try:
            result.append(EvidenceAssetSummary.model_validate(asset).model_dump())
        except ValidationError:
            continue
    return result


def asset_summary(asset: dict[str, Any]) -> dict[str, Any]:
    return EvidenceAssetSummary.model_validate({k: v for k, v in asset.items() if k != "payload"}).model_dump()


def get_asset(identifier: str, city: str) -> dict[str, Any]:
    asset = asset_by_id(identifier, city=city, mode="live")
    metadata = asset.get("provenance") if asset else None
    payload = asset.get("payload") if asset else None
    payload_metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if not isinstance(payload_metadata, dict):
        payload_metadata = {}
    if (
        not asset
        or not isinstance(metadata, dict)
        or not isinstance(payload, dict)
        or metadata.get("city") != city
        or metadata.get("mode") != "live"
        or payload.get("synthetic") is True
        or payload_metadata.get("synthetic") is True
    ):
        raise HTTPException(404, "Evidence asset not found in this city's normal workspace.")
    return EvidenceAsset.model_validate(asset).model_dump()


def _layer_from_asset(asset, template, **changes):
    meta = asset["provenance"]
    return {
        **template,
        "source": meta["source"], "observation_time": meta["observation_time"],
        "retrieved_at": meta["retrieved_at"], "resolution": meta["resolution"],
        "asset_id": asset["id"], "limitations": meta["limitations"],
        **changes,
    }


def _sample_layer(asset, template, collection):
    features = []
    for feature in collection.get("features", []):
        properties = feature.get("properties") or {}
        variable = template["variable"]
        value = properties.get(variable)
        if not _finite(value):
            continue
        features.append({
            **feature,
            "properties": {**properties, "value": value, "unit": template["unit"]},
        })
    geojson = _valid_geojson({"type": "FeatureCollection", "features": features})
    if geojson:
        return _layer_from_asset(asset, template, status="available", geojson=geojson, reason=None)
    return None


def map_layers(city: str, stored: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    stored = live_assets(city) if stored is None else stored
    layers = {spec[0]: _empty_layer(spec) for spec in LAYER_SPECS}
    # Oldest first: later successful observations supersede older evidence.
    for asset in reversed(stored):
        payload, meta = asset["payload"], asset["provenance"]
        supplied_layers = payload.get("layers") or []
        if isinstance(supplied_layers, dict):
            supplied_layers = list(supplied_layers.values())
        for supplied in supplied_layers:
            if not isinstance(supplied, dict) or not supplied.get("id"):
                continue
            identifier = supplied["id"]
            template = layers.get(identifier) or _empty_layer((identifier, identifier.replace("_", " ").title(), identifier, "observed", None))
            candidate = _layer_from_asset(asset, template, **{k: v for k, v in supplied.items() if k in MapLayer.model_fields})
            candidate["asset_id"] = asset["id"]
            if candidate.get("geojson") and not _valid_geojson(candidate["geojson"]):
                continue
            if not candidate.get("geojson") and not candidate.get("raster"):
                continue
            try:
                candidate = MapLayer.model_validate({**candidate, "status": "available", "reason": None}).model_dump()
            except ValidationError:
                continue
            layers[identifier] = candidate

        # Legacy georeferenced EE sample points carry real sampled values.
        samples = payload.get("samples")
        if isinstance(samples, dict):
            for identifier in ("lst", "suhii", "ndvi", "land_cover", "population"):
                sample = _sample_layer(asset, layers[identifier], samples)
                if sample:
                    layers[identifier] = sample

        # Existing Sentinel index grids already carry their true affine/CRS.
        if all(key in payload for key in ("crs", "transform", "shape")):
            for identifier, index in (payload.get("indices") or {}).items():
                if not isinstance(index, dict) or "grid" not in index:
                    continue
                try:
                    raster = RasterGrid(
                        crs=payload["crs"], transform=payload["transform"][:6],
                        shape=payload["shape"], values=index["grid"],
                    ).model_dump()
                except (ValidationError, TypeError):
                    continue
                if not any(value is not None for row in raster["values"] for value in row):
                    continue
                template = layers.get(identifier) or _empty_layer((identifier, identifier.upper(), identifier, "observed", "index"))
                layers[identifier] = _layer_from_asset(asset, template, status="available", raster=raster, reason=None)

        if asset["category"] == "weather":
            raw = payload.get("data") or {}
            current = raw.get("current") or {}
            latitude = raw.get("latitude", payload.get("latitude"))
            longitude = raw.get("longitude", payload.get("longitude"))
            if _finite(latitude) and _finite(longitude) and _finite(current.get("temperature_2m")):
                geojson = _valid_geojson({"type": "FeatureCollection", "features": [{
                    "type": "Feature", "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                    "properties": {"id": asset["id"], "name": "Weather model location", **current,
                                   "value": current["temperature_2m"], "unit": (raw.get("current_units") or {}).get("temperature_2m", "°C"),
                                   "observation_time": current.get("time"), "kind": "modelled"},
                }]})
                if geojson:
                    layers["weather"] = _layer_from_asset(asset, layers["weather"], status="available", geojson=geojson, reason=None)

        if asset["category"] in {"air_quality", "groundwater"} and isinstance(payload.get("stations"), list):
            features = []
            for station in payload["stations"]:
                lat, lon = station.get("latitude"), station.get("longitude")
                if not _finite(lat) or not _finite(lon):
                    continue
                measurements = station.get("measurements") or []
                measured = [m for m in measurements if _finite(m.get("value")) and m.get("observation_time")]
                groundwater = station.get("depth_below_ground_m")
                if not measured and not (_finite(groundwater) and station.get("observation_time")):
                    continue
                first = measured[0] if measured else {"value": groundwater, "unit": "m below ground"}
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                 "properties": {**station, "value": first["value"], "unit": first.get("unit")}})
            geojson = _valid_geojson({"type": "FeatureCollection", "features": features})
            if geojson:
                key = asset["category"]
                layers[key] = _layer_from_asset(asset, layers[key], status="available", geojson=geojson, reason=None)

    return [MapLayer.model_validate(layer).model_dump() for layer in layers.values()]


def workspace(city: str) -> dict[str, Any]:
    stored = live_assets(city)
    layers = map_layers(city, stored)
    by_layer = {layer["id"]: layer for layer in layers}
    capabilities = {}
    for name, layer_id in {
        "surface_temperature": "lst", "prediction": "predicted_lst", "suhii": "suhii",
        "vegetation": "ndvi", "land_cover": "land_cover", "weather": "weather",
        "air_quality": "air_quality", "groundwater": "groundwater", "heat_risk": "heat_risk",
        "population": "population", "mitigation": "interventions",
    }.items():
        layer = by_layer[layer_id]
        capabilities[name] = {"status": layer["status"], "reason": layer["reason"],
                              "asset_ids": [layer["asset_id"]] if layer["asset_id"] else []}
    capabilities["explainability"] = {"status": "unavailable", "reason": "No validated model explanation is available.", "asset_ids": []}
    capabilities["reports"] = {"status": "available" if stored else "unavailable", "reason": None if stored else "Retrieve evidence before generating an evidence report.", "asset_ids": [a["id"] for a in stored]}
    observed = by_layer["lst"]
    ready = observed["status"] == "available" and observed["kind"] == "observed" and bool(observed["observation_time"])
    return {
        "schema_version": "1", "city": city, "center": CITIES[city], "mode": "normal",
        "analysis": {"status": "available" if ready else "unavailable", "synthetic": False,
                     "dataset_id": observed["asset_id"] if ready else None,
                     "reason": None if ready else "No verified surface-temperature observations with acquisition dates are available."},
        "assets": [asset_summary(asset) for asset in stored], "layers": layers,
        "capabilities": capabilities,
        "limitations": ["Surface temperature, modelled air temperature, predictions and hypothetical intervention effects are different quantities.",
                        "Evidence availability does not establish model validation or intervention feasibility."],
    }
