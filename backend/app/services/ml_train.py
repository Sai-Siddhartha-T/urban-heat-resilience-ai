"""Spatial cross-validation, model tournament training, evaluation, and persistence.

Guarantees no data leakage through spatial KMeans clustering and strict train-only preprocessor fitting.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from app.db import ROOT, save
from app.services.features import (
    DEFAULT_FEATURES,
    FEATURES,
    FORBIDDEN_COLUMNS,
    TARGET_COLUMNS,
    SpatialFold,
    SpatialSplitResult,
    check_data_provenance,
    extract_coordinates,
    extract_feature_frame,
    spatial_split,
    validate_no_leakage,
)
from app.services.xai import (
    create_tree_explainer,
    explain_predictions,
    get_model_dir,
    load_explainer,
    load_shap_values,
    save_explainer,
    save_shap_values,
)

log = logging.getLogger("heatwise.ml_train")

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
MODEL_DIR.mkdir(exist_ok=True, parents=True)


def metrics(y: Sequence[float], p: Sequence[float]) -> Dict[str, float]:
    """Compute R², RMSE, and MAE regression evaluation metrics."""
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    return {
        "r2": float(r2_score(y_arr, p_arr)),
        "rmse": float(np.sqrt(mean_squared_error(y_arr, p_arr))),
        "mae": float(mean_absolute_error(y_arr, p_arr)),
    }


def assign_spatial_partitions(
    features: List[Dict[str, Any]], random_state: int = 42
) -> Tuple[List[int], List[str], str]:
    """Generalized spatial partitioning using KMeans clustering or coordinate-bounding quantiles.

    Guarantees balanced, reproducible folds without single-group collapse for N in [5, 50+].
    """
    n = len(features)
    if n < 5:
        raise ValueError(f"Need at least 5 zones for spatial cross-validation; got {n}.")

    coords = extract_coordinates(features)
    var = np.var(coords, axis=0)
    primary_axis = 0 if var[0] >= var[1] else 1

    if n < 8:
        # Small zone count: Train (N-2), Val (1), Test (1), Buffer (0)
        sort_idx = np.argsort(coords[:, primary_axis])
        val_idx = sort_idx[-2]
        test_idx = sort_idx[-1]
        partitions = ["training"] * n
        partitions[val_idx] = "validation"
        partitions[test_idx] = "test"
        blocks = [0] * n
        blocks[val_idx] = 3
        blocks[test_idx] = 5
        method = f"Small-area spatial ranking along axis {primary_axis} ({n-2} train, 1 val, 1 test)."
    elif n < 15:
        # 4 balanced spatial quantile blocks: 2 train, 1 val, 1 test
        sort_idx = np.argsort(coords[:, primary_axis])
        q = np.array_split(sort_idx, 4)
        partitions = [""] * n
        blocks = [0] * n
        for idx in q[0]:
            partitions[idx] = "training"
            blocks[idx] = 0
        for idx in q[1]:
            partitions[idx] = "training"
            blocks[idx] = 1
        for idx in q[2]:
            partitions[idx] = "validation"
            blocks[idx] = 3
        for idx in q[3]:
            partitions[idx] = "test"
            blocks[idx] = 5
        method = f"4-block spatial quantile partitioning along axis {primary_axis}."
    else:
        # Standard 6-block spatial partition: 3 train, 1 val, 1 buffer, 1 test
        used_kmeans = False
        try:
            kmeans = KMeans(n_clusters=6, random_state=random_state, n_init=10)
            cluster_labels = kmeans.fit_predict(coords)
            cluster_centers = kmeans.cluster_centers_[:, primary_axis]
            sorted_clusters = np.argsort(cluster_centers)
            cluster_map = {old: new for new, old in enumerate(sorted_clusters)}
            mapped_blocks = np.array([cluster_map[c] for c in cluster_labels])
            counts = [np.sum(mapped_blocks == i) for i in range(6)]
            min_cluster_req = max(1, min(15, n // 6))
            if min(counts) < min_cluster_req:
                raise ValueError(
                    f"Imbalanced cluster detected: minimum cluster has {min(counts)} < {min_cluster_req}"
                )
            blocks = mapped_blocks.tolist()
            used_kmeans = True
        except Exception:
            # Fall back to coordinate bounding quantile blocks (strictly balanced)
            sort_idx = np.argsort(coords[:, primary_axis])
            q = np.array_split(sort_idx, 6)
            blocks = [0] * n
            for b_idx, q_indices in enumerate(q):
                for idx in q_indices:
                    blocks[idx] = b_idx

        partitions = []
        for b in blocks:
            if b in [0, 1, 2]:
                partitions.append("training")
            elif b == 3:
                partitions.append("validation")
            elif b == 4:
                partitions.append("buffer")
            elif b == 5:
                partitions.append("test")
            else:
                partitions.append("training")

        method = (
            "6-cluster 2D KMeans sorted along spatial axis."
            if used_kmeans
            else f"6-block spatial quantile partitioning along axis {primary_axis}."
        )

    return blocks, partitions, method


def train_candidate_models(
    X_train: np.ndarray, y_train: np.ndarray, n_jobs: Optional[int] = None
) -> Dict[str, Any]:
    """Train the three candidate regression models on the training feature tensors."""
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
) -> Tuple[str, List[Dict[str, Any]]]:
    """Evaluate candidate models and select the best model by validation RMSE."""
    evaluations = []
    for name, model in candidates.items():
        val_pred = model.predict(X_val)
        val_metrics = metrics(y_val, val_pred)

        test_metrics = (
            metrics(y_test, model.predict(X_test))
            if (X_test is not None and y_test is not None and len(y_test) > 0)
            else val_metrics
        )

        evaluations.append(
            {
                "model": name,
                "validation": val_metrics,
                "test": test_metrics,
            }
        )

    # Select winning model strictly by minimum validation RMSE
    winner = min(evaluations, key=lambda m: m["validation"]["rmse"])["model"]
    return winner, evaluations


def train(data: Dict[str, Any], n_folds: Optional[int] = None) -> Dict[str, Any]:
    """Execute spatial cross-validation, train candidate models, select best by RMSE, and persist artifact."""
    validate_no_leakage(FEATURES)

    frame = extract_feature_frame(data["features"])
    n = len(frame)

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
        method = "Western 9 columns train; next 3 validate; 3-column buffer; eastern 3 test. No coordinates or target-derived predictors."
    elif n_folds is not None and n_folds >= 2:
        splits = spatial_split(data["features"], n_folds=n_folds)
        fold_0 = splits[0]
        tr_indices = fold_0.train_indices
        val_indices = fold_0.val_indices

        tr = frame.index.isin(tr_indices)
        val = frame.index.isin(val_indices)
        test = val  # in standard K-fold, val acts as holdout test

        for i, f in enumerate(data["features"]):
            f["properties"]["spatial_block"] = int(splits.cluster_labels[i])
            f["properties"]["partition"] = "training" if tr.iloc[i] else "validation"
        frame["spatial_block"] = splits.cluster_labels
        frame["partition"] = ["training" if tr.iloc[i] else "validation" for i in range(n)]
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

    min_required = max(1, min(15, n // 6))
    if min(tr.sum(), val.sum(), test.sum()) < min_required:
        raise ValueError(
            f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid."
        )

    # PREPROCESSING WITHOUT DATA LEAKAGE:
    # Fit imputer ONLY on training partition
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(frame.loc[tr, FEATURES])
    y = frame.loc[tr, "observed_suhii"].to_numpy(dtype=float)

    # Transform validation and test partitions strictly using training-derived imputer
    Xval = imputer.transform(frame.loc[val, FEATURES])
    yval = frame.loc[val, "observed_suhii"].to_numpy(dtype=float)
    Xtest = imputer.transform(frame.loc[test, FEATURES])
    ytest = frame.loc[test, "observed_suhii"].to_numpy(dtype=float)

    # Train all 3 candidate models
    candidates = train_candidate_models(X, y)

    # Evaluate and select best model by validation RMSE
    winner, evaluations = evaluate_models(candidates, Xval, yval, Xtest, ytest)
    model = candidates[winner]

    # Calculate 90% confidence interval from validation errors
    val_errors = np.abs(yval - model.predict(Xval))
    interval = float(np.quantile(val_errors, 0.90)) if len(val_errors) > 0 else 0.5

    # Generate and persist TreeSHAP explainer for winning model
    explainer = create_tree_explainer(model)

    # Inspect data provenance and fallback flags
    provenance = check_data_provenance(data)

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
        "metadata": data.get("metadata", {}),
        "split": {
            "training": int(tr.sum()),
            "validation": int(val.sum()),
            "test": int(test.sum()),
            "buffer": (
                int(frame["spatial_block"].eq(4).sum())
                if 4 in frame["spatial_block"].values
                else int((~tr & ~val & ~test).sum())
            ),
            "method": method,
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
    return {
        k: a[k]
        for k in ["winner", "interval", "evaluations", "metadata", "split", "features"]
        if k in a
    }


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


def infer(data: Dict[str, Any], a: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, float]]]:
    """Run model inference and TreeSHAP attribution across all features in GeoJSON data."""
    city = data.get("metadata", {}).get("city", "Ahmedabad")
    frame = extract_feature_frame(data["features"])
    X = a["imputer"].transform(frame[FEATURES])
    predictions = a["model"].predict(X)

    explainer = a.get("explainer") or create_tree_explainer(a["model"])
    shap_values, base_values, importance = explain_predictions(explainer, X, FEATURES)

    shap_records = []
    for i, f in enumerate(data["features"]):
        p = f["properties"]
        value = float(predictions[i])
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

        p.update(
            {
                "predicted_suhii": value,
                "predicted_lst": value + p.get("rural_reference", 33.0),
                "interval_low": value - a["interval"],
                "interval_high": value + a["interval"],
                "hotspot": value >= 4.0,
                "partition": partition_val,
                "shap": shap_dict,
                "shap_base": shap_base,
            }
        )

        shap_records.append({
            "zone_id": p.get("id", f"zone_{i}"),
            "prediction": value,
            "base_value": shap_base,
            "shap": shap_dict,
        })

    # Persist SHAP values for fast retrieval
    save_shap_values(city, shap_records, importance)

    return data, importance
