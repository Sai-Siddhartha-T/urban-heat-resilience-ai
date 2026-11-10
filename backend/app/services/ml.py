"""Machine Learning pipeline, spatial/temporal validation, model tournament, and defensible climate analytics.

Implements:
- Explicit target variable definitions: Land Surface Temperature (LST in °C) and Surface Urban Heat
  Island Intensity (SUHII in °C relative to rural reference), strictly differentiated from air temperature.
- Zero data leakage: coordinates, target variables, and partition labels strictly excluded from predictor tensors.
- Train-only SimpleImputer fitting preventing distribution leakage.
- Spatial Cross-Validation: 6-block spatial separation with isolated spatial buffer fold (Block 4)
  and KMeans spatial clustering across zone centroids.
- Temporal Cross-Validation: chronological forward-chaining expanding window cross-validation across
  multi-date acquisitions to prevent future-to-past temporal leakage.
- Competitive model tournament across Random Forest, XGBoost, and LightGBM selecting the champion
  strictly by lowest validation RMSE.
- Defensible evaluation metrics: R², RMSE, MAE, Mean Prediction Bias (1/N * sum(y_hat - y)),
  residual distribution statistics (mean, std, skewness), and Moran's I spatial residual error autocorrelation.
- Exact additive TreeSHAP explainability per zone (shap_base + sum(shap) == prediction, error < 1e-4).
- Non-causal attribution language in all returned explanations (distinguishing observational statistical
  associations from causal physical intervention cooling).
- Model artifact and TreeExplainer persistence with joblib and DB caching.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import scipy.stats
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from app.db import ROOT, save
from app.services.features import (
    DEFAULT_FEATURES,
    EXTENDED_FEATURES,
    FEATURES,
    FORBIDDEN_COLUMNS,
    PredictionTarget,
    SpatialFold,
    SpatialSplitResult,
    TARGET_COLUMNS,
    TARGET_DEFINITIONS,
    TemporalFold,
    TemporalSplitResult,
    assign_spatial_partitions,
    check_data_provenance,
    engineer_features,
    explain_target_differentiation,
    extract_coordinates,
    extract_feature_frame,
    get_target_definition,
    is_leakage_free,
    prepare_feature_tensors,
    sanitize_features,
    spatial_split,
    temporal_split,
    validate_no_leakage,
)
from app.services.xai import (
    FEATURE_HUMAN_NAMES,
    NON_CAUSAL_DISCLAIMER,
    check_shap_additivity,
    compare_zones_xai,
    create_tree_explainer,
    explain_predictions,
    explain_zone,
    format_understandable_contributions,
    get_model_dir,
    get_spatial_shap_contributions,
    load_explainer,
    load_shap_values,
    save_explainer,
    save_shap_values,
)

logger = logging.getLogger("heatwise.ml")
log = logger

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
MODEL_DIR.mkdir(exist_ok=True, parents=True)


def calculate_spatial_morans_i(
    coordinates: Sequence[Sequence[float]] | np.ndarray,
    residuals: Sequence[float] | np.ndarray,
) -> Dict[str, Any]:
    """Compute Moran's I spatial autocorrelation on regression residuals.

    Tests whether prediction errors are spatially random vs. clustered.
    A defensible spatial ML model must exhibit spatially random errors (Moran's I close to E[I] = -1/(N-1)),
    verifying that the model does not systematically miss localized geographic heat drivers.

    Parameters:
        coordinates: Array-like of shape (N, 2) containing [lon, lat] or [x, y] coordinates.
        residuals: Array-like of shape (N,) containing regression residuals (y_pred - y_true or y_true - y_pred).

    Returns:
        Dict containing morans_i, expected_i, variance, z_score, p_value, and interpretation string.
    """
    coords = np.asarray(coordinates, dtype=float)
    res = np.asarray(residuals, dtype=float)
    n = len(res)

    if n < 4:
        return {
            "morans_i": 0.0,
            "expected_i": 0.0,
            "variance": 0.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "interpretation": "insufficient_data",
            "spatially_random": True,
            "note": "Need at least 4 zones to calculate spatial error autocorrelation.",
        }

    mean_e = float(np.mean(res))
    z = res - mean_e
    denom = float(np.sum(z**2))

    if denom == 0.0:
        return {
            "morans_i": 0.0,
            "expected_i": float(-1.0 / (n - 1)),
            "variance": 0.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "interpretation": "zero_residuals",
            "spatially_random": True,
            "note": "Residuals are uniformly zero (perfect prediction).",
        }

    # Inverse distance spatial weight matrix W
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    dists = np.sqrt(np.sum(diff**2, axis=-1))
    np.fill_diagonal(dists, np.inf)
    dists = np.where(dists == 0.0, 1e-6, dists)
    W = 1.0 / dists
    np.fill_diagonal(W, 0.0)

    S0 = float(np.sum(W))
    if S0 == 0.0:
        return {
            "morans_i": 0.0,
            "expected_i": float(-1.0 / (n - 1)),
            "variance": 0.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "interpretation": "zero_spatial_weights",
            "spatially_random": True,
            "note": "Spatial weight matrix sum is zero.",
        }

    numerator = float(np.sum(W * np.outer(z, z)))
    I = float((n / S0) * (numerator / denom))
    E_I = float(-1.0 / (n - 1))

    # Analytical variance under the randomization assumption
    S1 = float(0.5 * np.sum((W + W.T)**2))
    S2 = float(np.sum((np.sum(W, axis=1) + np.sum(W, axis=0))**2))
    b2 = float((n * np.sum(z**4)) / (denom**2))

    A = n * ((n**2 - 3 * n + 3) * S1 - n * S2 + 3 * S0**2)
    B = b2 * ((n**2 - n) * S1 - 2 * n * S2 + 6 * S0**2)
    denom_var = (n - 1) * (n - 2) * (n - 3) * (S0**2)

    if denom_var > 0:
        var_I = float((A - B) / denom_var - E_I**2)
    else:
        var_I = 0.0
    var_I = max(var_I, 1e-9)

    z_score = float((I - E_I) / np.sqrt(var_I))
    p_val = float(2.0 * scipy.stats.norm.sf(abs(z_score)))

    # Interpretation: alpha = 0.05
    if p_val < 0.05:
        interp = "spatially_clustered" if I > E_I else "spatially_dispersed"
    else:
        interp = "spatially_random"

    return {
        "morans_i": float(I),
        "expected_i": float(E_I),
        "variance": float(var_I),
        "z_score": float(z_score),
        "p_value": float(p_val),
        "interpretation": interp,
        "spatially_random": interp == "spatially_random",
        "description": (
            f"Moran's I on spatial residuals = {I:.4f} (expected = {E_I:.4f}, p = {p_val:.4f}). "
            f"Residual errors are {interp.replace('_', ' ')}."
        ),
    }


def metrics(
    y: Sequence[float],
    p: Sequence[float],
    coordinates: Optional[Sequence[Sequence[float]] | np.ndarray] = None,
) -> Dict[str, Any]:
    """Compute defensible regression evaluation metrics.

    Calculates:
    - R² (coefficient of determination)
    - RMSE (root mean squared error in °C)
    - MAE (mean absolute error in °C)
    - Mean prediction bias: (1/N) * sum(p_i - y_i) in °C (positive = overprediction, negative = underprediction)
    - Residual distribution statistics:
      - residual_mean: mean error
      - residual_std: standard deviation of residuals
      - residual_skewness: Fisher-Pearson skewness coefficient of residual distribution
    - Spatial error autocorrelation (if spatial coordinates are provided):
      - Moran's I on spatial residuals (testing spatial error randomness vs clustering)
      - expected_i: -1 / (N - 1)
      - z_score and p_value
      - interpretation: 'spatially_random', 'spatially_clustered', or 'spatially_dispersed'
    """
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    n = len(y_arr)

    r2 = float(r2_score(y_arr, p_arr))
    rmse = float(np.sqrt(mean_squared_error(y_arr, p_arr)))
    mae = float(mean_absolute_error(y_arr, p_arr))

    # Residuals: e_i = \hat{y}_i - y_i
    residuals = p_arr - y_arr
    bias = float(np.mean(residuals)) if n > 0 else 0.0
    res_std = float(np.std(residuals, ddof=1)) if n > 1 else 0.0

    # Fisher-Pearson skewness
    if n >= 3 and res_std > 1e-9:
        res_skew = float(scipy.stats.skew(residuals))
    else:
        res_skew = 0.0

    result: Dict[str, Any] = {
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
        "bias": bias,
        "mean_prediction_bias": bias,
        "residual_mean": bias,
        "residual_std": res_std,
        "residual_skewness": res_skew,
    }

    if coordinates is not None and len(coordinates) == n:
        moran_res = calculate_spatial_morans_i(coordinates, residuals)
        result["morans_i"] = moran_res["morans_i"]
        result["spatial_error_autocorrelation"] = moran_res["morans_i"]
        result["spatial_error_random"] = moran_res["spatially_random"]
        result["morans_i_details"] = moran_res

    return result


def generate_spatial_error_map(
    features_or_coords: Union[np.ndarray, Sequence[Sequence[float]], List[Dict[str, Any]], Dict[str, Any], pd.DataFrame],
    y_true: Sequence[float],
    y_pred: Sequence[float],
    zone_ids: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Generate spatial residual error map across geographical zones.

    Returns:
        List of dictionaries with zone_id, coordinates [lon, lat], observed, predicted,
        residual (predicted - observed), absolute_error, and standardized_residual (z-score).
    """
    if isinstance(features_or_coords, (np.ndarray, list)) and len(features_or_coords) > 0 and not isinstance(features_or_coords[0], dict):
        coords = np.asarray(features_or_coords, dtype=float)
    else:
        coords = extract_coordinates(features_or_coords)

    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    n = len(y_t)
    residuals = y_p - y_t
    mean_res = float(np.mean(residuals)) if n > 0 else 0.0
    std_res = float(np.std(residuals)) if n > 1 else 1.0
    if std_res == 0.0:
        std_res = 1.0

    records: List[Dict[str, Any]] = []
    for i in range(n):
        zid = zone_ids[i] if zone_ids and i < len(zone_ids) else f"zone_{i}"
        res_val = float(residuals[i])
        records.append({
            "zone_id": zid,
            "coordinates": [float(coords[i, 0]), float(coords[i, 1])],
            "observed": float(y_t[i]),
            "predicted": float(y_p[i]),
            "residual": res_val,
            "absolute_error": abs(res_val),
            "standardized_residual": float((res_val - mean_res) / std_res),
        })
    return records


def train_candidate_models(
    X_train: np.ndarray, y_train: np.ndarray, n_jobs: Optional[int] = None
) -> Dict[str, Any]:
    """Train the three candidate regression models (Random Forest, XGBoost, LightGBM) on training tensors."""
    jobs = n_jobs or int(
        os.getenv("ML_JOBS", os.getenv("ML_N_JOBS", "1" if os.getenv("FAST_STARTUP") == "1" else "2"))
    )

    candidates = {
        "Random Forest": RandomForestRegressor(
            n_estimators=180, min_samples_leaf=2, random_state=42, n_jobs=jobs
        ),
        "XGBoost": XGBRegressor(
            n_estimators=180,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.9,
            random_state=42,
            n_jobs=jobs,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=180,
            max_depth=4,
            num_leaves=12,
            learning_rate=0.04,
            verbosity=-1,
            random_state=42,
            n_jobs=jobs,
        ),
    }

    for name, model in candidates.items():
        model.fit(X_train, y_train)

    return candidates


def evaluate_models(
    candidates: Dict[str, Any],
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: Optional[np.ndarray] = None,
    y_test: Optional[np.ndarray] = None,
    coordinates_val: Optional[np.ndarray] = None,
    coordinates_test: Optional[np.ndarray] = None,
    is_synthetic: bool = True,
    target: str = "suhii",
) -> Tuple[str, List[Dict[str, Any]]]:
    """Evaluate candidate models and select the best model strictly by validation RMSE.

    Strictly separates synthetic benchmark metrics from real-world observation metrics.
    Computes R², RMSE, MAE, Mean Prediction Bias, residual distribution statistics, and Moran's I.
    """
    benchmark_type = (
        "synthetic_spatial_holdout_benchmark"
        if is_synthetic
        else "empirical_spatial_holdout_validation"
    )
    data_provenance = "synthetic_demonstration" if is_synthetic else "real_observation"
    real_world_claim = not is_synthetic
    validation_disclaimer = (
        "Demonstration benchmark only — metrics evaluated on synthetic simulation landscape, "
        "not real-world ground truth observations."
        if is_synthetic
        else "Empirical validation against satellite-observed SUHII."
    )

    evaluations = []
    for name, model in candidates.items():
        val_pred = model.predict(X_val)
        val_metrics = metrics(y_val, val_pred, coordinates=coordinates_val)

        test_metrics = (
            metrics(y_test, model.predict(X_test), coordinates=coordinates_test)
            if (X_test is not None and y_test is not None and len(y_test) > 0)
            else val_metrics
        )

        evaluations.append(
            {
                "model": name,
                "target": target,
                "validation": val_metrics,
                "test": test_metrics,
                "benchmark_type": benchmark_type,
                "data_provenance": data_provenance,
                "real_world_claim": real_world_claim,
                "validation_disclaimer": validation_disclaimer,
            }
        )

    # Winner selected strictly by lowest validation RMSE
    winner = min(evaluations, key=lambda m: m["validation"]["rmse"])["model"]
    return winner, evaluations


def train(
    data: Dict[str, Any],
    n_folds: Optional[int] = None,
    target: Union[PredictionTarget, str] = "suhii",
    validation_strategy: Literal["spatial", "temporal"] = "spatial",
) -> Dict[str, Any]:
    """Execute spatial or temporal cross-validation, train candidate models, select champion by lowest RMSE, and persist artifact.

    Enforces:
    - Zero data leakage: predictors must not contain coordinates, partition labels, or target variables.
    - Explicit target definition: supports SUHII (relative to rural reference) or LST (absolute skin temperature).
    - Strict train-only imputer fitting.
    - Spatial CV: Block 4 acts as an explicit spatial buffer fold completely withheld from training, validation, and testing.
    - Temporal CV: expanding window forward-chaining preventing future-to-past temporal leakage.
    - Defensible evaluation metrics: R², RMSE, MAE, Mean Prediction Bias, residual distribution statistics, and Moran's I.
    """
    validate_no_leakage(FEATURES)

    target_key = str(target.value if isinstance(target, PredictionTarget) else target).lower()
    target_info = get_target_definition(target_key)
    target_col = "lst" if "lst" in target_key else "observed_suhii"

    frame = extract_feature_frame(data["features"], target_column=target_col)
    coords = extract_coordinates(data["features"])
    n = len(frame)

    if validation_strategy == "temporal":
        splits = temporal_split(frame, n_splits=n_folds or 3)
        tr = np.asarray(frame.index.isin(splits.train_indices), dtype=bool)
        val = np.asarray(frame.index.isin(splits.val_indices), dtype=bool)
        test = np.asarray(frame.index.isin(splits.test_indices), dtype=bool)
        for i, f in enumerate(data["features"]):
            f["properties"]["partition"] = (
                "training" if tr[i] else "validation" if val[i] else "test"
            )
        frame["partition"] = [
            "training" if tr[i] else "validation" if val[i] else "test"
            for i in range(n)
        ]
        method = f"Forward-chaining temporal cross-validation with {splits.n_folds} folds without temporal leakage."
        buffer_count = 0
    else:
        # Check for pre-existing valid 6-block synthetic split
        has_legacy_blocks = (
            "spatial_block" in frame.columns
            and set([0, 1, 2, 3, 5]).issubset(set(frame["spatial_block"].unique()))
            and min(
                frame["spatial_block"].isin([0, 1, 2]).sum(),
                frame["spatial_block"].eq(3).sum(),
                frame["spatial_block"].eq(5).sum(),
            )
            >= 15
        )

        if has_legacy_blocks and n_folds is None:
            tr = frame.spatial_block.isin([0, 1, 2])
            val = frame.spatial_block.eq(3)
            test = frame.spatial_block.eq(5)
            # Block 4 is the explicit spatial buffer fold, strictly withheld from train, val, and test
            method = "Western 9 columns train; next 3 validate; 3-column buffer; eastern 3 test. No coordinates or target-derived predictors."
        elif n_folds is not None and n_folds >= 2:
            splits = spatial_split(data["features"], n_folds=n_folds)
            tr = np.asarray(frame.index.isin(splits.train_indices), dtype=bool)
            val = np.asarray(frame.index.isin(splits.val_indices), dtype=bool)
            test = np.asarray(frame.index.isin(splits.test_indices), dtype=bool)
            for i, f in enumerate(data["features"]):
                f["properties"]["spatial_block"] = int(splits.cluster_labels[i])
                f["properties"]["partition"] = (
                    "training" if tr[i] else "validation" if val[i] else "test"
                )
            frame["spatial_block"] = splits.cluster_labels
            frame["partition"] = [
                "training" if tr[i] else "validation" if val[i] else "test"
                for i in range(n)
            ]
            method = f"KMeans spatial cross-validation with {n_folds} folds without data leakage."
        else:
            blocks, partitions, method = assign_spatial_partitions(data["features"])
            for i, f in enumerate(data["features"]):
                f["properties"]["spatial_block"] = blocks[i]
                f["properties"]["partition"] = partitions[i]
            frame["spatial_block"] = blocks
            frame["partition"] = partitions
            tr = frame["partition"].eq("training")
            val = frame["partition"].eq("validation")
            test = frame["partition"].eq("test")

        buffer_count = (
            int(frame["spatial_block"].eq(4).sum())
            if "spatial_block" in frame.columns and 4 in frame["spatial_block"].values
            else int((~tr & ~val & ~test).sum())
        )

    min_required = max(1, min(15, n // 6))
    if min(tr.sum(), val.sum(), test.sum()) < min_required:
        raise ValueError(
            f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid."
        )

    # PREPROCESSING WITHOUT DATA LEAKAGE:
    # Fit imputer ONLY on training partition!
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(frame.loc[tr, FEATURES])
    y = frame.loc[tr, target_col].to_numpy(dtype=float)

    # Transform validation and test partitions strictly using training-derived imputer
    Xval = imputer.transform(frame.loc[val, FEATURES])
    yval = frame.loc[val, target_col].to_numpy(dtype=float)
    Xtest = imputer.transform(frame.loc[test, FEATURES])
    ytest = frame.loc[test, target_col].to_numpy(dtype=float)

    coords_val = coords[val] if coords is not None and len(coords) == n else None
    coords_test = coords[test] if coords is not None and len(coords) == n else None

    # Train all 3 candidate models in tournament
    candidates = train_candidate_models(X, y)

    # Inspect data provenance and fallback flags
    provenance = check_data_provenance(data)
    is_synth = provenance.get("synthetic", True)

    # Evaluate and select best model by validation RMSE
    winner, evaluations = evaluate_models(
        candidates,
        Xval,
        yval,
        Xtest,
        ytest,
        coordinates_val=coords_val,
        coordinates_test=coords_test,
        is_synthetic=is_synth,
        target=target_key,
    )
    model = candidates[winner]

    # Calculate 90% confidence interval from validation errors
    val_errors = np.abs(yval - model.predict(Xval))
    interval = float(np.quantile(val_errors, 0.90)) if len(val_errors) > 0 else 0.5

    # Generate and persist TreeSHAP explainer for winning model
    explainer = create_tree_explainer(model)

    # Winning model validation spatial error autocorrelation
    winning_eval = next(e for e in evaluations if e["model"] == winner)
    spatial_error_autocorrelation = winning_eval["validation"].get("morans_i")

    city_name = data.get("metadata", {}).get("city", "model").lower()

    artifact = {
        "model": model,
        "explainer": explainer,
        "imputer": imputer,
        "winner": winner,
        "interval": interval,
        "evaluations": evaluations,
        "features": FEATURES,
        "provenance": provenance,
        "target": target_key,
        "target_definition": target_info,
        "validation_strategy": validation_strategy,
        "spatial_error_autocorrelation": spatial_error_autocorrelation,
        "metadata": data.get("metadata", {}),
        "split": {
            "training": int(tr.sum()),
            "validation": int(val.sum()),
            "test": int(test.sum()),
            "buffer": buffer_count,
            "method": method,
            "strategy": validation_strategy,
        },
    }

    # Persist chosen model and explainer
    model_path = get_model_dir() / f"{city_name}.joblib"
    explainer_path = get_model_dir() / f"{city_name}_explainer.joblib"
    joblib.dump(artifact, model_path)
    save_explainer(explainer, explainer_path)

    save(
        "model_evaluation",
        describe(artifact),
        record_id=f"model-{data.get('metadata', {}).get('city', 'default')}",
    )
    return artifact


def describe(a: Dict[str, Any]) -> Dict[str, Any]:
    """Extract serializable metadata summary from model artifact."""
    summary: Dict[str, Any] = {
        k: a[k]
        for k in [
            "winner",
            "interval",
            "evaluations",
            "metadata",
            "split",
            "features",
            "provenance",
            "target",
            "target_definition",
            "validation_strategy",
            "spatial_error_autocorrelation",
        ]
        if k in a
    }
    # Add high-level provenance flags if available
    prov = a.get("provenance", {})
    if prov:
        summary["data_provenance"] = prov.get("data_provenance", "unknown")
        summary["benchmark_type"] = prov.get("benchmark_type", "spatial_holdout")
        summary["real_world_claim"] = prov.get("real_world_claim", False)
        summary["validation_disclaimer"] = prov.get("validation_disclaimer", "")
    return summary


def load_or_train(data: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve cached model and explainer, or trigger spatial training."""
    city = data.get("metadata", {}).get("city", "ahmedabad").lower()
    dir_path = get_model_dir()
    path = dir_path / f"{city}.joblib"
    explainer_path = dir_path / f"{city}_explainer.joblib"

    if path.exists():
        try:
            a = joblib.load(path)
            model_meta = a.get("metadata", {})
            data_meta = data.get("metadata", {})
            split = a.get("split") or {}
            counts = [split.get(k, 0) for k in ("training", "validation", "test", "buffer")]
            feature_total = len(data.get("features", []))

            if counts and all(isinstance(v, (int, np.integer)) for v in counts):
                if feature_total and sum(counts) != feature_total:
                    raise ValueError(
                        f"Cached spatial split mismatch for {city}: counts={counts}, feature_count={feature_total}."
                    )

            # Attach explainer if missing in loaded artifact
            if "explainer" not in a or a["explainer"] is None:
                loaded_exp = load_explainer(explainer_path)
                a["explainer"] = loaded_exp or create_tree_explainer(a["model"])

            # Primary check: Exact generation timestamp match
            if model_meta.get("generated_at") == data_meta.get("generated_at"):
                return a
            # Secondary check: Both are synthetic baseline datasets with matching features
            if (
                data_meta.get("synthetic")
                and model_meta.get("synthetic")
                and model_meta.get("city", "").lower() == city
                and a.get("features") == FEATURES
            ):
                return a
        except Exception as exc:
            log.warning("Could not read cached model at %s (%s). Re-training.", path, exc)

    return train(data)


def infer(
    data: Dict[str, Any],
    a: Dict[str, Any],
    target: Optional[Union[PredictionTarget, str]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, float]]]:
    """Run model inference and TreeSHAP attribution across all features in GeoJSON data, and persist SHAP values.

    Enforces exact additivity: shap_base + sum(shap) == predicted (error < 1e-4).
    Enforces non-causal attribution language.
    """
    resolved_target = (
        str(target.value if isinstance(target, PredictionTarget) else target).lower()
        if target is not None
        else a.get("target", "suhii")
    )
    is_lst_target = "lst" in resolved_target

    frame = extract_feature_frame(data["features"])
    X = a["imputer"].transform(frame[FEATURES])
    predictions = a["model"].predict(X)

    explainer = a.get("explainer") or create_tree_explainer(a["model"])
    shap_values, base_values, importance = explain_predictions(explainer, X, FEATURES)

    for i, f in enumerate(data["features"]):
        p = f["properties"]
        raw_pred = float(predictions[i])
        partition_val = p.get("partition")
        if not partition_val:
            sb = p.get("spatial_block")
            partition_val = (
                "test"
                if sb == 5
                else (
                    "buffer"
                    if sb == 4
                    else "validation" if sb == 3 else "training"
                )
            )

        shap_dict = {
            name: float(shap_values[i, j])
            for j, name in enumerate(FEATURES)
        }
        shap_base = float(base_values[i])

        # Verify exact TreeSHAP additivity (tolerance < 1e-4)
        check_shap_additivity(raw_pred, shap_base, shap_dict, tolerance=1e-4)

        rural_ref = float(p.get("rural_reference", 33.0))
        if is_lst_target:
            pred_lst = raw_pred
            pred_suhii = raw_pred - rural_ref
        else:
            pred_suhii = raw_pred
            pred_lst = raw_pred + rural_ref

        p.update(
            {
                "predicted_suhii": pred_suhii,
                "predicted_lst": pred_lst,
                "prediction": raw_pred,
                "interval_low": raw_pred - a["interval"],
                "interval_high": raw_pred + a["interval"],
                "hotspot": pred_suhii >= 4.0,
                "partition": partition_val,
                "shap": shap_dict,
                "shap_base": shap_base,
                "target_variable": resolved_target,
                "non_causal_disclaimer": NON_CAUSAL_DISCLAIMER,
            }
        )

    # Persist calculated SHAP values
    city = data.get("metadata", {}).get("city", "ahmedabad")
    shap_records = [
        {
            "zone_id": f["properties"]["id"],
            "shap": f["properties"]["shap"],
            "shap_base": f["properties"]["shap_base"],
            "predicted_suhii": f["properties"]["predicted_suhii"],
            "prediction": f["properties"].get("prediction", f["properties"]["predicted_suhii"]),
        }
        for f in data["features"]
    ]
    save_shap_values(city, shap_records, importance)

    return data, importance


__all__ = [
    "DEFAULT_FEATURES",
    "EXTENDED_FEATURES",
    "FEATURE_HUMAN_NAMES",
    "FEATURES",
    "FORBIDDEN_COLUMNS",
    "MODEL_DIR",
    "NON_CAUSAL_DISCLAIMER",
    "PredictionTarget",
    "SpatialFold",
    "SpatialSplitResult",
    "TARGET_COLUMNS",
    "TARGET_DEFINITIONS",
    "TemporalFold",
    "TemporalSplitResult",
    "assign_spatial_partitions",
    "calculate_spatial_morans_i",
    "check_data_provenance",
    "check_shap_additivity",
    "compare_zones_xai",
    "create_tree_explainer",
    "describe",
    "engineer_features",
    "evaluate_models",
    "explain_predictions",
    "explain_target_differentiation",
    "explain_zone",
    "extract_coordinates",
    "extract_feature_frame",
    "format_understandable_contributions",
    "generate_spatial_error_map",
    "get_model_dir",
    "get_spatial_shap_contributions",
    "get_target_definition",
    "infer",
    "is_leakage_free",
    "load_explainer",
    "load_or_train",
    "load_shap_values",
    "metrics",
    "prepare_feature_tensors",
    "sanitize_features",
    "save_explainer",
    "save_shap_values",
    "spatial_split",
    "temporal_split",
    "train",
    "train_candidate_models",
    "validate_no_leakage",
]
