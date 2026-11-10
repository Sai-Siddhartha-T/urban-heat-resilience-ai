"""Explainable AI (XAI) service using TreeSHAP for tree-based ensemble models.

Provides local feature attributions, base/expected values, global feature importance rankings,
and SHAP value persistence.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import shap

from app.db import ROOT, save
from app.services.features import DEFAULT_FEATURES, FEATURES

logger = logging.getLogger("heatwise.xai")

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
MODEL_DIR.mkdir(exist_ok=True, parents=True)

NON_CAUSAL_DISCLAIMER: str = (
    "TreeSHAP feature attributions reflect statistical associations within the trained regression model "
    "and do NOT represent causal physical cooling impacts. Physical intervention effects must be evaluated "
    "using microclimate physics models (e.g., intervention simulation with surface energy balance)."
)

FEATURE_HUMAN_NAMES: Dict[str, str] = {
    "ndvi": "Vegetation Density (NDVI)",
    "ndwi": "Surface Moisture / Water Index (NDWI)",
    "ndbi": "Built-Up Surface Index (NDBI)",
    "ndbai": "Bare Soil Index (NDBAI)",
    "building_density": "Urban Building Density",
    "population_density": "Population Density",
    "air_temperature": "Ambient Air Temperature",
    "humidity": "Relative Humidity",
    "rainfall": "Precipitation / Rainfall",
    "solar_radiation": "Solar Radiation",
    "soil_moisture": "Soil Moisture",
    "land_cover": "Land Cover Classification",
    "elderly_share": "Elderly Population Proportion",
    "children_share": "Children Population Proportion",
    "poverty_rate": "Poverty Rate",
    "cooling_deficit": "Cooling Infrastructure Deficit",
}


def format_understandable_contributions(
    contributions: Dict[str, float],
    base_value: float,
    feature_values: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Format local TreeSHAP contributions into human-understandable, scientifically defensible non-causal terms."""
    items = []
    for feat, shap_val in sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True):
        human_name = FEATURE_HUMAN_NAMES.get(feat, feat.replace("_", " ").title())
        direction = "warming_association" if shap_val > 0 else "cooling_association"
        val_str = f" ({feat}={feature_values[feat]:.2f})" if feature_values and feat in feature_values else ""
        if shap_val > 0:
            narrative = (
                f"{human_name}{val_str} is statistically associated with +{shap_val:.3f}°C higher predicted temperature "
                f"relative to the expected base value ({base_value:.2f}°C)."
            )
        else:
            narrative = (
                f"{human_name}{val_str} is statistically associated with {shap_val:.3f}°C lower predicted temperature "
                f"relative to the expected base value ({base_value:.2f}°C)."
            )
        items.append({
            "feature": feat,
            "feature_label": human_name,
            "shap_value": float(shap_val),
            "effect_direction": direction,
            "narrative": narrative,
            "non_causal_note": "Observational statistical correlation; non-causal association, not a direct causal intervention impact.",
        })
    return items


def get_model_dir() -> Path:
    """Return current MODEL_DIR respecting runtime environment variable changes."""
    p = Path(os.getenv("MODEL_DIR", str(MODEL_DIR)))
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_tree_explainer(model: Any) -> shap.TreeExplainer:
    """Create a TreeExplainer for a trained tree ensemble (RF, XGBoost, LightGBM)."""
    try:
        return shap.TreeExplainer(model)
    except Exception as exc:
        logger.warning("Standard TreeExplainer failed (%s); attempting with interventional feature perturber.", exc)
        return shap.TreeExplainer(model, feature_perturbation="interventional")


def explain_predictions(
    explainer: shap.TreeExplainer,
    X: Union[np.ndarray, pd.DataFrame],
    feature_names: Optional[List[str]] = None,
) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """Compute TreeSHAP explanations for feature matrix X.

    Returns:
        (shap_values, base_values, global_importance):
            shap_values: np.ndarray of shape (N, n_features)
            base_values: np.ndarray of shape (N,)
            global_importance: list of dicts {"feature": str, "importance": float} sorted descending.
    """
    names = feature_names or DEFAULT_FEATURES
    X_arr = np.asarray(X, dtype=float)

    explanation = explainer(X_arr)
    raw_shap = np.asarray(explanation.values)

    # In case of multidimensional output (e.g. classification), take first dimension
    if raw_shap.ndim > 2:
        raw_shap = raw_shap[:, :, 0]

    # Reshape base values to 1D array of length N
    base_vals = np.asarray(explanation.base_values)
    if base_vals.ndim > 1:
        base_vals = base_vals.reshape(-1)
    if len(base_vals) == 1 and len(X_arr) > 1:
        base_vals = np.full(len(X_arr), float(base_vals[0]))

    # Global feature importance: mean absolute SHAP value per feature
    mean_abs_shap = np.mean(np.abs(raw_shap), axis=0)
    global_importance = sorted(
        [
            {"feature": names[j], "importance": float(mean_abs_shap[j])}
            for j in range(min(len(names), raw_shap.shape[1]))
        ],
        key=lambda item: -item["importance"],
    )

    return raw_shap, base_vals, global_importance


def explain_zone(
    explainer: shap.TreeExplainer,
    X_single: Union[np.ndarray, List[float], Dict[str, float]],
    feature_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate local TreeSHAP attribution for a single zone or feature dictionary."""
    names = feature_names or DEFAULT_FEATURES

    if isinstance(X_single, dict):
        # Accept a zone-property payload containing the full feature set; ignore metadata fields.
        X_vec = np.array([[float(X_single.get(name, 0.0)) for name in names]])
    else:
        X_arr = np.asarray(X_single, dtype=float)
        X_vec = X_arr.reshape(1, -1) if X_arr.ndim == 1 else X_arr

    shap_values, base_values, _ = explain_predictions(explainer, X_vec, names)

    contributions = {
        name: float(shap_values[0, j])
        for j, name in enumerate(names)
        if j < shap_values.shape[1]
    }
    base_val = float(base_values[0])
    predicted = base_val + sum(contributions.values())
    additivity_error = abs((base_val + sum(contributions.values())) - predicted)

    feature_val_dict = X_single if isinstance(X_single, dict) else None
    understandable = format_understandable_contributions(contributions, base_val, feature_val_dict)

    return {
        "prediction": predicted,
        "base_value": base_val,
        "contributions": contributions,
        "shap": contributions,
        "shap_base": base_val,
        "additivity_valid": additivity_error < 1e-4,
        "additivity_error": additivity_error,
        "attribution_type": "statistical_association",
        "non_causal_disclaimer": NON_CAUSAL_DISCLAIMER,
        "understandable_contributions": understandable,
    }


def save_explainer(explainer: shap.TreeExplainer, path: Union[Path, str]) -> Path:
    """Persist the SHAP TreeExplainer to disk."""
    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(explainer, save_path)
    logger.info("Persisted TreeExplainer to %s", save_path)
    return save_path


def load_explainer(path: Union[Path, str]) -> Optional[shap.TreeExplainer]:
    """Load a persisted SHAP TreeExplainer from disk."""
    load_path = Path(path)
    if not load_path.exists():
        fallback_path = get_model_dir() / load_path.name
        if fallback_path.exists():
            load_path = fallback_path
        else:
            logger.warning("Explainer path does not exist: %s", load_path)
            return None
    try:
        return joblib.load(load_path)
    except Exception as exc:
        logger.warning("Failed loading explainer from %s: %s", load_path, exc)
        return None


def save_shap_values(
    city: str,
    shap_records: Union[List[Dict[str, Any]], Dict[str, Any]],
    importance: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    """Persist calculated SHAP values and global feature importances to disk and DB."""
    city_clean = city.lower()
    path = get_model_dir() / f"{city_clean}_shap.joblib"

    if isinstance(shap_records, dict):
        if "shap_records" in shap_records and isinstance(shap_records["shap_records"], list):
            records_list = shap_records["shap_records"]
        else:
            records_list = [shap_records]
        global_imp = (
            shap_records.get("global_importance")
            or shap_records.get("importance")
            or importance
        )
    else:
        records_list = list(shap_records)
        global_imp = importance

    # Ensure records_list is not an inadvertently wrapped dict
    while isinstance(records_list, dict) and "shap_records" in records_list:
        records_list = records_list["shap_records"]

    payload = {
        "city": city,
        "shap_records": records_list,
        "importance": global_imp,
    }
    joblib.dump(payload, path)
    logger.info("Persisted SHAP values to %s (%d records)", path, len(records_list))

    try:
        save(
            "shap_values",
            {
                "city": city,
                "importance": global_imp,
                "count": len(records_list) if isinstance(records_list, list) else 1,
            },
            record_id=f"shap-{city_clean}",
        )
    except Exception as exc:
        logger.debug("Database record save skipped for SHAP: %s", exc)
    return path


def load_shap_values(city: str) -> Optional[Dict[str, Any]]:
    """Retrieve persisted SHAP values and global feature importances."""
    city_clean = city.lower()
    path = get_model_dir() / f"{city_clean}_shap.joblib"
    if path.exists():
        try:
            data = joblib.load(path)
            if isinstance(data, dict):
                # Normalize nested shap_records if present
                if isinstance(data.get("shap_records"), dict) and "shap_records" in data["shap_records"]:
                    data["shap_records"] = data["shap_records"]["shap_records"]
            return data
        except Exception as exc:
            logger.warning("Could not read SHAP cache at %s: %s", path, exc)
    return None


def check_shap_additivity(
    prediction: float,
    base_value: float,
    contributions: Union[Dict[str, float], Sequence[float]],
    tol: float | None = None,
    tolerance: float | None = None,
) -> bool:
    """Verify that base_value + sum(contributions) equals prediction within numerical tolerance.

    Accepts both legacy ``tol`` and the newer ``tolerance`` keyword for compatibility with
    different callers and test suites.
    """
    threshold = float(tolerance if tolerance is not None else tol if tol is not None else 1e-4)
    vals = contributions.values() if isinstance(contributions, dict) else contributions
    reconstructed = float(base_value) + sum(float(v) for v in vals)
    return abs(reconstructed - float(prediction)) < threshold


def compare_zones_xai(
    zone_a: Dict[str, Any],
    zone_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare heat-driving factors between two geographical locations using TreeSHAP attributions."""
    p_a = zone_a.get("properties", zone_a)
    p_b = zone_b.get("properties", zone_b)
    shap_a = p_a.get("shap", {})
    shap_b = p_b.get("shap", {})

    feature_names = list(DEFAULT_FEATURES)
    diffs = {
        k: float(shap_a.get(k, 0.0)) - float(shap_b.get(k, 0.0))
        for k in feature_names
    }
    delta_predicted_suhii = float(p_a.get("predicted_suhii", 0.0)) - float(p_b.get("predicted_suhii", 0.0))

    heating = sorted(
        diffs.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    cooling = sorted(
        diffs.items(),
        key=lambda item: item[1],
    )[:3]

    summary = (
        f"{p_a.get('id', 'zone_a')} has a model prediction {delta_predicted_suhii:.3f}°C warmer than "
        f"{p_b.get('id', 'zone_b')}, statistically associated with differing model contributions from "
        f"{', '.join(f'{FEATURE_HUMAN_NAMES.get(k, k)}' for k, _ in heating[:2])} (observational association, non-causal)."
    )

    return {
        "zone_a_id": p_a.get("id"),
        "zone_b_id": p_b.get("id"),
        "delta_predicted_suhii": delta_predicted_suhii,
        "predicted_diff": delta_predicted_suhii,
        "driving_deltas": diffs,
        "top_heating_factors_a": [{"feature": name, "delta": value} for name, value in heating],
        "top_cooling_factors_a": [{"feature": name, "delta": value} for name, value in cooling],
        "shap_diffs": diffs,
        "summary": summary,
        "attribution_type": "statistical_association",
        "non_causal_disclaimer": NON_CAUSAL_DISCLAIMER,
    }


def get_spatial_shap_contributions(
    data: Any,
    target_feature: str = "ndvi",
) -> List[Dict[str, Any]]:
    """Extract local SHAP attributions and predictions for all zones in a GeoJSON dataset."""
    features = data.get("features", data) if isinstance(data, dict) else data
    output: List[Dict[str, Any]] = []

    for i, feature in enumerate(features):
        props = feature.get("properties", feature) if isinstance(feature, dict) else {}
        shap_map = props.get("shap", {})
        if not isinstance(shap_map, dict):
            shap_map = {}

        heating = max(shap_map.items(), key=lambda item: float(item[1]), default=(None, 0.0))
        cooling = min(shap_map.items(), key=lambda item: float(item[1]), default=(None, 0.0))
        target_value = float(shap_map.get(target_feature, 0.0))
        scale = max((abs(float(v)) for v in shap_map.values()), default=1.0)
        normalized = 0.0 if scale == 0 else max(-1.0, min(1.0, target_value / scale))

        output.append(
            {
                "zone_id": props.get("id", f"zone_{i}"),
                "predicted_suhii": float(props.get("predicted_suhii", 0.0)),
                "shap_base": float(props.get("shap_base", 0.0)),
                "shap": shap_map,
                "dominant_heating_factor": heating[0] if heating[0] is not None else None,
                "dominant_cooling_factor": cooling[0] if cooling[0] is not None else None,
                "target_feature": target_feature,
                "target_shap": target_value,
                "normalized_impact": normalized,
                "attribution_type": "statistical_association",
                "non_causal_disclaimer": NON_CAUSAL_DISCLAIMER,
            }
        )

    return output


__all__ = [
    "FEATURE_HUMAN_NAMES",
    "MODEL_DIR",
    "NON_CAUSAL_DISCLAIMER",
    "check_shap_additivity",
    "compare_zones_xai",
    "create_tree_explainer",
    "explain_predictions",
    "explain_zone",
    "format_understandable_contributions",
    "get_model_dir",
    "get_spatial_shap_contributions",
    "load_explainer",
    "load_shap_values",
    "save_explainer",
    "save_shap_values",
]

