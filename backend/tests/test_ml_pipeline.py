"""Unit and integration test suite for the modular ML pipeline.

Covers:
- Modular sub-service imports and backward compatibility
- Spatial cross-validation (spatial_split using KMeans on centroid coordinates)
- Anti-leakage guarantees (no target or coordinate features in predictors)
- Model tournament (RandomForest, XGBoost, LightGBM; selection by validation RMSE)
- TreeSHAP explainability, additivity, and importance rankings
- Artifact and SHAP persistence
- API endpoints: /api/heat/predict and /api/xai/shap
"""

import math
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.services.data import sample_data
from app.services.features import (
    DEFAULT_FEATURES,
    FEATURES,
    FORBIDDEN_COLUMNS,
    TARGET_COLUMNS,
    SpatialFold,
    SpatialSplitResult,
    extract_coordinates,
    extract_feature_frame,
    prepare_feature_tensors,
    spatial_split,
    validate_no_leakage,
)
from app.services.ml_train import (
    MODEL_DIR,
    assign_spatial_partitions,
    describe,
    evaluate_models,
    infer,
    load_or_train,
    metrics,
    train,
    train_candidate_models,
)
from app.services.xai import (
    create_tree_explainer,
    explain_predictions,
    explain_zone,
    load_explainer,
    load_shap_values,
    save_explainer,
    save_shap_values,
)
import app.services.ml as ml_unified


@pytest.fixture(scope="module")
def synthetic_data():
    """Deterministic synthetic city dataset for pipeline testing."""
    init_db()
    return sample_data("Ahmedabad")


@pytest.fixture(scope="module")
def client():
    """Test client for FastAPI API endpoints."""
    with TestClient(app) as c:
        yield c


# =====================================================================
# 1. MODULAR SUB-SERVICE ARCHITECTURE TESTS
# =====================================================================

def test_modular_architecture_exports():
    """Verify modular pieces are properly decoupled and exposed via ml.py."""
    # Features module
    assert hasattr(ml_unified, "spatial_split")
    assert hasattr(ml_unified, "extract_coordinates")
    assert hasattr(ml_unified, "validate_no_leakage")
    assert hasattr(ml_unified, "FEATURES")

    # Training module
    assert hasattr(ml_unified, "train")
    assert hasattr(ml_unified, "evaluate_models")
    assert hasattr(ml_unified, "metrics")
    assert hasattr(ml_unified, "load_or_train")

    # Explainability module
    assert hasattr(ml_unified, "create_tree_explainer")
    assert hasattr(ml_unified, "explain_predictions")
    assert hasattr(ml_unified, "explain_zone")
    assert hasattr(ml_unified, "save_shap_values")
    assert hasattr(ml_unified, "load_shap_values")

    # Unified infer orchestration
    assert hasattr(ml_unified, "infer")


# =====================================================================
# 2. SPATIAL CROSS-VALIDATION (spatial_split using KMeans on centroids)
# =====================================================================

def test_spatial_split_kmeans_clustering(synthetic_data):
    """Verify spatial_split partitions zones using KMeans on centroid coordinates."""
    features = synthetic_data["features"]
    n_zones = len(features)
    n_folds = 5

    splits = spatial_split(features, n_folds=n_folds, random_state=42)

    assert isinstance(splits, SpatialSplitResult)
    assert len(splits) == n_folds
    assert splits.cluster_labels is not None
    assert len(splits.cluster_labels) == n_zones
    assert splits.cluster_centers is not None
    assert len(splits.cluster_centers) == n_folds

    # Check each fold's disjointness and coverage
    all_val_indices = []
    for k, fold in enumerate(splits):
        assert isinstance(fold, SpatialFold)
        assert len(fold) == 2  # Unpacks as (train, val)
        train_idx, val_idx = fold

        assert len(train_idx) > 0
        assert len(val_idx) > 0
        assert len(train_idx) + len(val_idx) == n_zones

        # Strictly disjoint: train and validation sets have zero index overlap
        assert set(train_idx).isdisjoint(set(val_idx))
        all_val_indices.extend(val_idx.tolist())

    # Every zone must appear in validation exactly once across all folds
    assert sorted(all_val_indices) == list(range(n_zones))


def test_spatial_split_unpacking_and_sklearn_compatibility(synthetic_data):
    """Verify spatial_split can be unpacked as (train, val) and used with sklearn generators."""
    features = synthetic_data["features"][:30]
    splits = spatial_split(features, n_folds=3)

    # Standard unpacking loop
    fold_count = 0
    for train_idx, val_idx in splits:
        assert len(train_idx) > 0
        assert len(val_idx) > 0
        fold_count += 1
    assert fold_count == 3

    # Generator method
    gen_count = 0
    for train_idx, val_idx in splits.split():
        assert len(train_idx) > 0
        assert len(val_idx) > 0
        gen_count += 1
    assert gen_count == 3


def test_spatial_split_edge_cases():
    """Verify boundary conditions and error handling in spatial_split."""
    # Under-threshold folds
    zones = [{"longitude": 72.5 + 0.01 * i, "latitude": 23.0 + 0.01 * i} for i in range(10)]
    with pytest.raises(ValueError, match="n_folds must be at least 2"):
        spatial_split(zones, n_folds=1)

    # More folds than zones
    with pytest.raises(ValueError, match="Need at least 5 zones"):
        spatial_split(zones[:4], n_folds=5)

    # 2-fold split
    splits_2 = spatial_split(zones, n_folds=2)
    assert len(splits_2) == 2
    assert len(splits_2[0].val_indices) + len(splits_2[1].val_indices) == 10

    # Pathological: identical coordinates (zero spatial variance)
    identical_zones = [{"longitude": 72.5, "latitude": 23.0} for _ in range(12)]
    splits_identical = spatial_split(identical_zones, n_folds=3)
    assert len(splits_identical) == 3
    for fold in splits_identical:
        assert len(fold.val_indices) > 0


# =====================================================================
# 3. ANTI-DATA LEAKAGE SAFEGUARDS
# =====================================================================

def test_no_data_leakage_in_features():
    """Verify target and spatial coordinate leakage are strictly excluded."""
    # Target columns must never be in feature set
    for target in TARGET_COLUMNS:
        assert target not in FEATURES

    # Coordinates and identifiers must never be in feature set
    for coord in ["latitude", "longitude", "lat", "lon", "spatial_block", "partition", "id", "name"]:
        assert coord not in FEATURES

    # Validation function behaves as expected
    validate_no_leakage(FEATURES)

    with pytest.raises(ValueError, match="Data leakage detected"):
        validate_no_leakage(FEATURES + ["observed_suhii"])

    with pytest.raises(ValueError, match="Data leakage detected"):
        validate_no_leakage(FEATURES + ["latitude"])


def test_isolated_imputer_fitting(synthetic_data):
    """Verify imputer is fit strictly on training fold to prevent cross-partition leakage."""
    features = synthetic_data["features"]
    frame = extract_feature_frame(features)

    # Create dummy train and val masks
    tr_mask = np.zeros(len(frame), dtype=bool)
    tr_mask[:200] = True
    val_mask = ~tr_mask

    # Fit imputer on training fold ONLY
    X_tr, y_tr, imputer = prepare_feature_tensors(frame[tr_mask], fit_imputer=True)
    assert imputer is not None

    # Transform validation fold using training imputer
    X_val, y_val, _ = prepare_feature_tensors(frame[val_mask], imputer=imputer, fit_imputer=False)
    assert X_val.shape[0] == val_mask.sum()
    assert X_val.shape[1] == len(FEATURES)
    assert not np.isnan(X_val).any()


# =====================================================================
# 4. MODEL TOURNAMENT TRAINING & SELECTION BY VALIDATION RMSE
# =====================================================================

def test_model_tournament_training_and_selection(synthetic_data):
    """Verify RandomForest, XGBoost, and LightGBM are trained and winner selected by RMSE."""
    artifact = train(synthetic_data)

    # All 3 candidate models must be evaluated
    evaluations = artifact["evaluations"]
    assert len(evaluations) == 3
    model_names = [e["model"] for e in evaluations]
    assert "Random Forest" in model_names
    assert "XGBoost" in model_names
    assert "LightGBM" in model_names

    # Check metrics structure
    for eval_item in evaluations:
        for split in ("validation", "test"):
            m = eval_item[split]
            assert "rmse" in m and np.isfinite(m["rmse"]) and m["rmse"] >= 0
            assert "r2" in m and np.isfinite(m["r2"])
            assert "mae" in m and np.isfinite(m["mae"]) and m["mae"] >= 0

    # Best model must be selected by minimum validation RMSE
    expected_winner = min(evaluations, key=lambda m: m["validation"]["rmse"])["model"]
    assert artifact["winner"] == expected_winner

    # 90% confidence interval must be positive
    assert artifact["interval"] > 0


# =====================================================================
# 5. TREESHAP EXPLAINABILITY & ADDITIVITY
# =====================================================================

def test_shap_explainability_and_additivity(synthetic_data):
    """Verify TreeSHAP explanations satisfy the exact additivity property."""
    artifact = train(synthetic_data)
    annotated_data, importance = infer(synthetic_data, artifact)

    # Verify additivity for each zone: base_value + sum(shap_contributions) == predicted_suhii
    for feature in annotated_data["features"][:30]:
        p = feature["properties"]
        predicted = p["predicted_suhii"]
        base = p["shap_base"]
        contributions = p["shap"]

        assert len(contributions) == len(FEATURES)
        reconstructed = base + sum(contributions.values())
        assert abs(reconstructed - predicted) < 1e-4

    # Global importance must be ranked descending
    assert len(importance) == len(FEATURES)
    for i in range(len(importance) - 1):
        assert importance[i]["importance"] >= importance[i + 1]["importance"]


# =====================================================================
# 6. MODEL & SHAP VALUE PERSISTENCE
# =====================================================================

def test_model_and_shap_persistence(synthetic_data):
    """Verify trained model, explainer, and SHAP values are persisted to disk and reloadable."""
    city = synthetic_data["metadata"]["city"].lower()
    artifact = train(synthetic_data)
    annotated_data, importance = infer(synthetic_data, artifact)

    # Model and explainer artifacts must exist on disk
    model_path = MODEL_DIR / f"{city}.joblib"
    explainer_path = MODEL_DIR / f"{city}_explainer.joblib"
    shap_path = MODEL_DIR / f"{city}_shap.joblib"

    assert model_path.exists()
    assert explainer_path.exists()
    assert shap_path.exists()

    # Verify reloadability
    loaded_explainer = load_explainer(explainer_path)
    assert loaded_explainer is not None

    loaded_shap = load_shap_values(city)
    assert loaded_shap is not None
    assert loaded_shap["city"] == synthetic_data["metadata"]["city"]
    assert len(loaded_shap["shap_records"]) == len(synthetic_data["features"])


# =====================================================================
# 7. API ROUTES: /api/heat/predict AND /api/xai/shap
# =====================================================================

def test_api_heat_predict_endpoints(client):
    """Verify POST and GET /api/heat/predict endpoints."""
    # POST single zone prediction
    res_single = client.post("/api/heat/predict", json={"city": "Ahmedabad", "zone_id": "ahmedabad-00-00"})
    assert res_single.status_code == 200
    body = res_single.json()
    assert body["id"] == "ahmedabad-00-00"
    assert "predicted_suhii" in body
    assert "predicted_lst" in body
    assert "interval_low" in body
    assert "interval_high" in body

    # GET single zone prediction
    res_get_single = client.get("/api/heat/predict?city=Ahmedabad&zone_id=ahmedabad-00-00")
    assert res_get_single.status_code == 200
    assert res_get_single.json()["id"] == "ahmedabad-00-00"

    # POST batch city prediction
    res_batch = client.post("/api/heat/predict", json={"city": "Ahmedabad"})
    assert res_batch.status_code == 200
    batch_body = res_batch.json()
    assert "predictions" in batch_body
    assert len(batch_body["predictions"]) > 0
    assert "model" in batch_body

    # GET batch city prediction
    res_get_batch = client.get("/api/heat/predict?city=Ahmedabad")
    assert res_get_batch.status_code == 200
    assert "predictions" in res_get_batch.json()


def test_api_xai_shap_endpoints(client):
    """Verify POST and GET /api/xai/shap endpoints."""
    # POST single zone SHAP
    res_single = client.post("/api/xai/shap", json={"city": "Ahmedabad", "zone_id": "ahmedabad-00-00"})
    assert res_single.status_code == 200
    body = res_single.json()
    assert body["zone_id"] == "ahmedabad-00-00"
    assert "prediction" in body
    assert "base_value" in body
    assert "shap_values" in body
    assert "contributions" in body
    assert len(body["shap_values"]) == len(FEATURES)

    # GET single zone SHAP
    res_get_single = client.get("/api/xai/shap?city=Ahmedabad&zone_id=ahmedabad-00-00")
    assert res_get_single.status_code == 200
    assert res_get_single.json()["zone_id"] == "ahmedabad-00-00"

    # POST city-wide SHAP
    res_city = client.post("/api/xai/shap", json={"city": "Ahmedabad"})
    assert res_city.status_code == 200
    city_body = res_city.json()
    assert "shap_values" in city_body
    assert "global_importance" in city_body
    assert len(city_body["global_importance"]) == len(FEATURES)

    # GET city-wide SHAP
    res_get_city = client.get("/api/xai/shap?city=Ahmedabad")
    assert res_get_city.status_code == 200
    assert "shap_values" in res_get_city.json()
    assert "global_importance" in res_get_city.json()
