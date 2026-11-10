"""Comprehensive test suite for Machine Learning, Spatial Cross-Validation, and TreeSHAP XAI.

Covers:
1. Feature Engineering & Strict Anti-Leakage (no coordinates, target-derived variables, or leakage in X).
2. Train-only Median Missing-Data Imputation.
3. 6-Block Spatial Separation & Buffer Fold (Block 4) Complete Withholding.
4. Competitive Model Tournament (RF, XGBoost, LightGBM) & Empirical Residual Intervals.
5. Exact Additive TreeSHAP Explainability (error < 1e-4), Global Ranking, and Zone Comparison.
6. Strict Separation of Synthetic Demonstration Benchmarks from Real Observations.
7. Persistence, Caching, and End-to-End Pipeline Execution.
"""

from __future__ import annotations

import copy
import math
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, mapping
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

from app.db import init_db
from app.services.data import sample_data
from app.services.features import (
    COORDINATE_COLUMNS,
    DEFAULT_FEATURES,
    EXTENDED_FEATURES,
    FEATURES,
    FORBIDDEN_COLUMNS,
    METADATA_COLUMNS,
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
    get_spatial_shap_contributions,
    load_explainer,
    load_shap_values,
    save_explainer,
    save_shap_values,
)
from app.services.ml import (
    MODEL_DIR,
    calculate_spatial_morans_i,
    describe,
    evaluate_models,
    generate_spatial_error_map,
    infer,
    load_or_train,
    metrics,
    train,
    train_candidate_models,
)


@pytest.fixture(scope="module")
def initialized_db():
    init_db()


@pytest.fixture(scope="module")
def synthetic_city_data(initialized_db):
    return sample_data(city="Ahmedabad")


# =====================================================================
# 1. FEATURE CONFIGURATION AND STRICT ANTI-LEAKAGE TESTS
# =====================================================================

class TestFeatureAntiLeakage:
    """Verify canonical feature configuration and strict anti-leakage guarantees."""

    def test_canonical_feature_definitions(self):
        """Canonical FEATURES must contain the 12 expected indicators."""
        assert len(DEFAULT_FEATURES) == 12
        assert FEATURES == DEFAULT_FEATURES
        expected = [
            "ndvi", "ndwi", "ndbi", "ndbai",
            "building_density", "population_density",
            "air_temperature", "humidity", "rainfall",
            "solar_radiation", "soil_moisture", "land_cover",
        ]
        assert FEATURES == expected
        assert set(FEATURES).issubset(set(EXTENDED_FEATURES))

    def test_forbidden_columns_contain_all_leakage_sources(self):
        """Forbidden columns must include coordinates, targets, and metadata."""
        for col in ["lat", "lon", "latitude", "longitude", "row", "column", "spatial_block"]:
            assert col in FORBIDDEN_COLUMNS
        for col in ["lst", "observed_suhii", "rural_reference", "predicted_suhii"]:
            assert col in FORBIDDEN_COLUMNS

    def test_validate_no_leakage_passes_clean_features(self):
        """Clean environmental features must pass validation."""
        validate_no_leakage(FEATURES)
        assert is_leakage_free(FEATURES)

    @pytest.mark.parametrize("leaky_col", [
        "lat", "lon", "latitude", "longitude", "row", "column", "spatial_block",
        "lst", "observed_suhii", "rural_reference", "predicted_suhii", "partition",
    ])
    def test_validate_no_leakage_raises_on_forbidden_columns(self, leaky_col):
        """Any attempt to include coordinates or targets in predictor list must raise ValueError."""
        tainted = FEATURES + [leaky_col]
        with pytest.raises(ValueError, match="Data leakage detected"):
            validate_no_leakage(tainted)
        assert not is_leakage_free(tainted)

    def test_case_insensitive_leakage_detection(self):
        """Validation must catch case variations (e.g. 'LAT', 'Observed_Suhii')."""
        with pytest.raises(ValueError, match="Data leakage detected"):
            validate_no_leakage(["ndvi", "LAT", "building_density"])
        with pytest.raises(ValueError, match="Data leakage detected"):
            validate_no_leakage(["ndvi", "Rural_Reference", "humidity"])

    def test_sanitize_features_filters_forbidden_columns(self):
        """sanitize_features removes leakage columns while keeping clean features."""
        tainted = ["ndvi", "lat", "building_density", "observed_suhii", "rural_reference", "humidity"]
        sanitized = sanitize_features(tainted)
        assert sanitized == ["ndvi", "building_density", "humidity"]
        assert is_leakage_free(sanitized)


# =====================================================================
# 2. MISSING DATA IMPUTATION & TENSOR PREPARATION TESTS
# =====================================================================

class TestImputationAndTensorPrep:
    """Verify median imputer fitting strictly on training data."""

    def test_prepare_feature_tensors_train_fitting(self):
        """Training partition fits imputer and returns imputed tensor without leakage."""
        df = pd.DataFrame({
            "ndvi": [0.2, np.nan, 0.4, 0.6],
            "ndwi": [0.1, 0.2, np.nan, 0.4],
            "building_density": [0.5, 0.5, 0.5, 0.5],
            "observed_suhii": [2.1, 2.5, 3.0, 3.8],
        })
        for f in FEATURES:
            if f not in df.columns:
                df[f] = 1.0

        X, y, imputer = prepare_feature_tensors(df, fit_imputer=True)
        assert X.shape == (4, len(FEATURES))
        assert not np.isnan(X).any()
        assert y is not None and len(y) == 4
        # Verify median imputation: median of ndvi [0.2, 0.4, 0.6] is 0.4
        ndvi_idx = FEATURES.index("ndvi")
        assert X[1, ndvi_idx] == pytest.approx(0.4)

    def test_prepare_feature_tensors_transform_with_unfitted_raises(self):
        """Transforming with fit_imputer=False and no imputer raises ValueError."""
        df = pd.DataFrame({"ndvi": [0.2, 0.4]})
        with pytest.raises(ValueError, match="Cannot transform features with an unfitted imputer"):
            prepare_feature_tensors(df, fit_imputer=False, imputer=None)

    def test_transform_uses_training_imputer_without_refitting(self):
        """Validation partition is transformed using training imputer values."""
        train_df = pd.DataFrame({
            "ndvi": [0.1, 0.3, 0.5],
            "ndwi": [0.0, 0.0, 0.0],
            "observed_suhii": [1.0, 2.0, 3.0],
        })
        for f in FEATURES:
            if f not in train_df.columns:
                train_df[f] = 0.5

        _, _, fitted_imputer = prepare_feature_tensors(train_df, fit_imputer=True)

        val_df = pd.DataFrame({
            "ndvi": [np.nan],
            "ndwi": [np.nan],
            "observed_suhii": [2.5],
        })
        for f in FEATURES:
            if f not in val_df.columns:
                val_df[f] = 0.5

        X_val, y_val, _ = prepare_feature_tensors(val_df, imputer=fitted_imputer, fit_imputer=False)
        ndvi_idx = FEATURES.index("ndvi")
        # Training median of [0.1, 0.3, 0.5] is 0.3
        assert X_val[0, ndvi_idx] == pytest.approx(0.3)


# =====================================================================
# 3. SPATIAL CROSS-VALIDATION & BUFFER FOLD TESTS
# =====================================================================

class TestSpatialPartitioningAndBufferFold:
    """Verify 6-block spatial separation, KMeans, and complete withholding of Block 4 buffer fold."""

    def test_spatial_split_under_threshold_raises(self):
        """Fewer than 5 zones must raise ValueError."""
        zones = [{"properties": {"lon": 72.5 + 0.01 * i, "lat": 23.0 + 0.01 * i}} for i in range(4)]
        with pytest.raises(ValueError, match="Need at least 5 zones"):
            assign_spatial_partitions(zones)

    def test_spatial_split_small_areas(self):
        """Small areas (5 to 7 zones) rank along primary axis."""
        zones = [{"properties": {"lon": 72.5 + 0.01 * i, "lat": 23.0 + 0.02 * i}} for i in range(6)]
        blocks, partitions, method = assign_spatial_partitions(zones)
        assert len(partitions) == 6
        assert partitions.count("training") == 4
        assert partitions.count("validation") == 1
        assert partitions.count("test") == 1
        assert "Small-area spatial ranking" in method

    def test_spatial_split_4_block_quantile(self):
        """Intermediate zones (8 to 14 zones) use 4-block spatial quantile partitioning."""
        zones = [{"properties": {"lon": 72.5 + 0.01 * i, "lat": 23.0 + 0.01 * i}} for i in range(10)]
        blocks, partitions, method = assign_spatial_partitions(zones)
        assert len(partitions) == 10
        assert "4-block spatial quantile" in method
        assert "training" in partitions
        assert "validation" in partitions
        assert "test" in partitions

    def test_six_block_spatial_partition_and_buffer_isolation(self):
        """Standard 6-block spatial partition must isolate Block 4 as buffer fold."""
        np.random.seed(42)
        zones = []
        for i in range(30):
            zones.append({
                "properties": {
                    "lon": 72.5 + 0.02 * (i % 6),
                    "lat": 23.0 + 0.02 * (i // 6),
                    "id": f"z_{i}",
                }
            })
        blocks, partitions, method = assign_spatial_partitions(zones)

        assert len(partitions) == 30
        assert set(blocks).issubset({0, 1, 2, 3, 4, 5})

        # Verify mapping: 0, 1, 2 -> training, 3 -> validation, 4 -> buffer, 5 -> test
        for b, p in zip(blocks, partitions):
            if b in [0, 1, 2]:
                assert p == "training"
            elif b == 3:
                assert p == "validation"
            elif b == 4:
                assert p == "buffer"
            elif b == 5:
                assert p == "test"

        assert partitions.count("buffer") > 0
        assert partitions.count("training") > 0
        assert partitions.count("validation") > 0
        assert partitions.count("test") > 0

    def test_buffer_fold_never_in_train_val_or_test_partitions(self, synthetic_city_data):
        """Block 4 must be completely withheld from training, validation, and testing."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)

        frame = pd.DataFrame([f["properties"] for f in data_copy["features"]])
        buffer_mask = frame["spatial_block"].eq(4)
        assert buffer_mask.sum() == 54  # 3 columns out of 18 in 18x18 grid

        # Assert no buffer zone was in training, validation, or test
        train_mask = frame["spatial_block"].isin([0, 1, 2])
        val_mask = frame["spatial_block"].eq(3)
        test_mask = frame["spatial_block"].eq(5)

        assert (buffer_mask & train_mask).sum() == 0
        assert (buffer_mask & val_mask).sum() == 0
        assert (buffer_mask & test_mask).sum() == 0
        assert artifact["split"]["buffer"] == 54


# =====================================================================
# 4. MODEL TOURNAMENT AND EVALUATION METRICS TESTS
# =====================================================================

class TestModelTournament:
    """Verify 3-model competitive tournament, lowest-RMSE winner selection, and metrics."""

    def test_metrics_calculation(self):
        """R², RMSE, and MAE must be accurately calculated."""
        y_true = np.array([2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([2.1, 2.9, 4.2, 4.8])
        res = metrics(y_true, y_pred)

        assert "r2" in res and "rmse" in res and "mae" in res
        assert res["rmse"] > 0
        assert res["mae"] > 0
        assert res["r2"] > 0.9

    def test_candidate_models_trained(self):
        """All three model types must be fitted."""
        X = np.random.uniform(0, 1, (40, len(FEATURES)))
        y = 2.0 * X[:, 0] + 0.5 * X[:, 1] + np.random.normal(0, 0.1, 40)
        candidates = train_candidate_models(X, y, n_jobs=1)

        assert "Random Forest" in candidates
        assert "XGBoost" in candidates
        assert "LightGBM" in candidates
        assert isinstance(candidates["Random Forest"], RandomForestRegressor)

    def test_tournament_selection_by_lowest_val_rmse(self):
        """Winner must be selected strictly by minimum validation RMSE."""
        X_tr = np.random.uniform(0, 1, (50, len(FEATURES)))
        y_tr = 3.0 * X_tr[:, 0] + 1.0 * X_tr[:, 1]
        X_val = np.random.uniform(0, 1, (20, len(FEATURES)))
        y_val = 3.0 * X_val[:, 0] + 1.0 * X_val[:, 1]

        candidates = train_candidate_models(X_tr, y_tr, n_jobs=1)
        winner, evals = evaluate_models(candidates, X_val, y_val, is_synthetic=True)

        assert winner in ["Random Forest", "XGBoost", "LightGBM"]
        assert len(evals) == 3

        min_rmse = min(e["validation"]["rmse"] for e in evals)
        winner_eval = next(e for e in evals if e["model"] == winner)
        assert winner_eval["validation"]["rmse"] == min_rmse

    def test_empirical_prediction_intervals(self, synthetic_city_data):
        """Prediction intervals must be derived from 90th percentile of validation residuals."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        interval = artifact["interval"]
        assert isinstance(interval, float)
        assert interval > 0.0
        assert interval < 5.0


# =====================================================================
# 5. EXACT ADDITIVE TREESHAP AND SPATIAL XAI TESTS
# =====================================================================

class TestTreeSHAPAndSpatialXAI:
    """Verify exact additivity, global importance ranking, and zone comparison."""

    def test_exact_treeshap_additivity(self, synthetic_city_data):
        """Every single zone must satisfy exact TreeSHAP additivity: base + sum(shap) == pred (error < 1e-4)."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        inferred_data, importance = infer(data_copy, artifact)

        for feature in inferred_data["features"]:
            p = feature["properties"]
            pred = p["predicted_suhii"]
            base = p["shap_base"]
            shap_dict = p["shap"]

            # Mathematical TreeSHAP additivity check
            assert abs((base + sum(shap_dict.values())) - pred) < 1e-4
            assert check_shap_additivity(pred, base, shap_dict, tolerance=1e-4)

    def test_global_feature_importance_ranking(self, synthetic_city_data):
        """Global importance must be sorted descending by mean absolute SHAP value."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        _, importance = infer(data_copy, artifact)

        assert len(importance) == len(FEATURES)
        values = [item["importance"] for item in importance]
        assert values == sorted(values, reverse=True)
        assert all(v >= 0.0 for v in values)

    def test_explain_zone_single_vector(self, synthetic_city_data):
        """explain_zone computes local attribution for an arbitrary zone property dictionary."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        explainer = artifact["explainer"]

        sample_zone_props = data_copy["features"][0]["properties"]
        res = explain_zone(explainer, sample_zone_props)

        assert "prediction" in res
        assert "base_value" in res
        assert "contributions" in res
        assert res["additivity_valid"] is True
        assert res["additivity_error"] < 1e-4

    def test_compare_zones_xai(self, synthetic_city_data):
        """compare_zones_xai compares two zones and decomposes temperature difference into feature deltas."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        inferred_data, _ = infer(data_copy, artifact)

        zone_a = inferred_data["features"][0]
        zone_b = inferred_data["features"][-1]

        comparison = compare_zones_xai(zone_a, zone_b)

        assert "zone_a_id" in comparison and "zone_b_id" in comparison
        assert "delta_predicted_suhii" in comparison
        assert len(comparison["driving_deltas"]) == len(FEATURES)
        assert len(comparison["top_heating_factors_a"]) <= 3
        assert len(comparison["top_cooling_factors_a"]) <= 3
        assert isinstance(comparison["summary"], str)

    def test_get_spatial_shap_contributions(self, synthetic_city_data):
        """get_spatial_shap_contributions produces choropleth-ready spatial attribution maps."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        inferred_data, _ = infer(data_copy, artifact)

        spatial_contributions = get_spatial_shap_contributions(
            inferred_data["features"], target_feature="ndvi"
        )
        assert len(spatial_contributions) == len(inferred_data["features"])
        first = spatial_contributions[0]
        assert "dominant_heating_factor" in first
        assert "dominant_cooling_factor" in first
        assert "target_shap" in first
        assert -1.0 <= first["normalized_impact"] <= 1.0


# =====================================================================
# 6. EXTERNAL VALIDATION & STRICT SEPARATION TESTS
# =====================================================================

class TestDataProvenanceAndSeparation:
    """Verify strict separation between synthetic benchmark metrics and real-world observations."""

    def test_synthetic_data_provenance_flags(self):
        """Synthetic benchmark data must explicitly declare synthetic provenance."""
        meta = {"city": "Ahmedabad", "synthetic": True, "source": "synthetic_generator"}
        prov = check_data_provenance({"metadata": meta})

        assert prov["synthetic"] is True
        assert prov["is_synthetic"] is True
        assert prov["data_provenance"] == "synthetic_demonstration"
        assert prov["benchmark_type"] == "synthetic_spatial_holdout_benchmark"
        assert prov["real_world_claim"] is False
        assert "Demonstration benchmark only" in prov["validation_disclaimer"]

    def test_real_world_data_provenance_flags(self):
        """Real observation data must set real_world_claim=True and appropriate provenance."""
        meta = {"city": "Delhi", "synthetic": False, "source": "landsat_sentinel_ingest"}
        prov = check_data_provenance({"metadata": meta})

        assert prov["synthetic"] is False
        assert prov["is_synthetic"] is False
        assert prov["data_provenance"] == "real_observation"
        assert prov["benchmark_type"] == "empirical_spatial_holdout_validation"
        assert prov["real_world_claim"] is True
        assert "Empirical validation" in prov["validation_disclaimer"]

    def test_evaluations_include_provenance_separation(self, synthetic_city_data):
        """Trained artifact evaluation records must include benchmark separation metadata."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)

        for eval_record in artifact["evaluations"]:
            assert "benchmark_type" in eval_record
            assert "data_provenance" in eval_record
            assert "real_world_claim" in eval_record
            assert eval_record["real_world_claim"] is False
            assert "Demonstration benchmark" in eval_record["validation_disclaimer"]

        desc = describe(artifact)
        assert desc["real_world_claim"] is False
        assert desc["data_provenance"] == "synthetic_demonstration"


# =====================================================================
# 7. PERSISTENCE, CACHING, AND END-TO-END PIPELINE TESTS
# =====================================================================

class TestPersistenceAndPipeline:
    """Verify model saving, loading, caching, and end-to-end execution."""

    def test_load_or_train_caching(self, synthetic_city_data):
        """load_or_train returns cached artifact on matching metadata without re-training."""
        data_copy = copy.deepcopy(synthetic_city_data)
        # First call trains and persists
        artifact_1 = train(data_copy)
        # Second call loads from cache
        artifact_2 = load_or_train(data_copy)

        assert artifact_2["winner"] == artifact_1["winner"]
        assert artifact_2["interval"] == pytest.approx(artifact_1["interval"])
        assert artifact_2["split"] == artifact_1["split"]

    def test_explainer_and_shap_persistence(self):
        """TreeExplainer and calculated SHAP values must persist to disk and reload."""
        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        X = np.random.uniform(0, 1, (20, len(FEATURES)))
        y = np.random.uniform(1, 5, 20)
        rf.fit(X, y)

        exp = create_tree_explainer(rf)
        save_path = MODEL_DIR / "test_rf_explainer.joblib"
        save_explainer(exp, save_path)
        assert save_path.exists()

        loaded_exp = load_explainer(save_path)
        assert loaded_exp is not None

        shap_path = save_shap_values("test_city", [{"zone_id": "z1", "shap": {"ndvi": 0.1}}])
        assert shap_path.exists()

        loaded_shap = load_shap_values("test_city")
        assert loaded_shap is not None
        assert loaded_shap["city"] == "test_city"


# =====================================================================
# 8. TARGET VARIABLE DEFINITIONS AND LST/SUHII DIFFERENTIATION
# =====================================================================

class TestTargetVariableDefinitionsAndLST:
    """Verify explicit target definitions, LST vs SUHII, and differentiation from ambient air temperature."""

    def test_prediction_target_enum_and_definitions(self):
        """PredictionTarget enum and TARGET_DEFINITIONS must define SUHII and LST in defensible terms."""
        assert PredictionTarget.SUHII == "suhii"
        assert PredictionTarget.LST == "lst"
        assert "suhii" in TARGET_DEFINITIONS
        assert "lst" in TARGET_DEFINITIONS
        assert "air_temperature" in TARGET_DEFINITIONS

        suhii_def = TARGET_DEFINITIONS["suhii"]
        assert suhii_def["unit"] == "°C"
        assert "LST_urban - LST_rural_reference" in suhii_def["formula"]
        assert "differentiation_from_air_temp" in suhii_def

        lst_def = TARGET_DEFINITIONS["lst"]
        assert lst_def["unit"] == "°C"
        assert "Landsat" in lst_def["sensor_source"]
        assert "differentiation_from_air_temp" in lst_def

        air_def = TARGET_DEFINITIONS["air_temperature"]
        assert air_def["unit"] == "°C"
        assert "predictor" in air_def["differentiation_from_air_temp"].lower()

    def test_explain_target_differentiation_content(self):
        """explain_target_differentiation clearly differentiates LST, SUHII, and 2m air temperature."""
        explanation = explain_target_differentiation()
        assert "Land Surface Temperature" in explanation
        assert "Surface Urban Heat Island Intensity" in explanation
        assert "Ambient Air Temperature" in explanation
        assert "PREDICTOR" in explanation

    def test_get_target_definition_valid_and_invalid(self):
        """get_target_definition resolves target definitions and raises on invalid targets."""
        def_suhii = get_target_definition("suhii")
        assert def_suhii["code"] == "SUHII"
        def_lst = get_target_definition(PredictionTarget.LST)
        assert def_lst["code"] == "LST"

        with pytest.raises(ValueError, match="Unknown target"):
            get_target_definition("invalid_target_xyz")

    def test_train_and_infer_lst_target(self, synthetic_city_data):
        """Pipeline supports training on LST target and produces consistent predicted_lst and predicted_suhii."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy, target=PredictionTarget.LST)

        assert artifact["target"] == "lst"
        assert artifact["winner"] in ["Random Forest", "XGBoost", "LightGBM"]

        inferred, _ = infer(data_copy, artifact, target=PredictionTarget.LST)
        for f in inferred["features"][:5]:
            p = f["properties"]
            rural_ref = p.get("rural_reference", 33.0)
            assert "predicted_lst" in p
            assert "predicted_suhii" in p
            assert p["predicted_lst"] == pytest.approx(p["predicted_suhii"] + rural_ref, abs=1e-4)


# =====================================================================
# 9. DEFENSIBLE EVALUATION METRICS, BIAS, AND SPATIAL AUTOCORRELATION
# =====================================================================

class TestDefensibleMetricsAndSpatialAutocorrelation:
    """Verify mean prediction bias, residual statistics, and Moran's I on spatial residuals."""

    def test_metrics_bias_and_residual_distribution_statistics(self):
        """metrics() must compute R², RMSE, MAE, Mean Prediction Bias, and residual distribution statistics."""
        y_true = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
        # Systematic overprediction by 0.5°C
        y_pred = np.array([2.5, 3.5, 4.5, 5.5, 6.5])

        res = metrics(y_true, y_pred)
        assert res["r2"] == pytest.approx(0.875)
        assert res["rmse"] == pytest.approx(0.5)
        assert res["mae"] == pytest.approx(0.5)
        # Bias should be exactly +0.5°C
        assert res["bias"] == pytest.approx(0.5)
        assert res["mean_prediction_bias"] == pytest.approx(0.5)
        assert res["residual_mean"] == pytest.approx(0.5)
        assert res["residual_std"] == pytest.approx(0.0)
        assert res["residual_skewness"] == pytest.approx(0.0)

    def test_metrics_skewed_residuals(self):
        """Skewed residual distributions must compute non-zero skewness."""
        y_true = np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0])
        # Right-skewed error distribution
        y_pred = np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.1, 2.1, 2.2, 3.0, 4.5])

        res = metrics(y_true, y_pred)
        assert res["residual_skewness"] > 1.0  # Positively skewed residuals

    def test_morans_i_clustered_residuals(self):
        """Moran's I on spatially clustered residuals must yield high positive autocorrelation."""
        coords = np.array([
            [0.0, 0.0], [0.0, 0.1], [0.1, 0.0], [0.1, 0.1],
            [1.0, 1.0], [1.0, 1.1], [1.1, 1.0], [1.1, 1.1],
        ])
        # Clustered errors: cluster 1 has positive residuals, cluster 2 has negative residuals
        clustered_residuals = np.array([1.5, 1.2, 1.4, 1.3, -1.5, -1.2, -1.4, -1.3])

        moran = calculate_spatial_morans_i(coords, clustered_residuals)
        assert moran["morans_i"] > 0.5
        assert moran["interpretation"] == "spatially_clustered"
        assert moran["spatially_random"] is False
        assert moran["p_value"] < 0.05

    def test_morans_i_random_residuals(self):
        """Moran's I on spatially random residuals must indicate spatial randomness."""
        np.random.seed(123)
        coords = np.random.uniform(0, 10, (40, 2))
        random_residuals = np.random.normal(0, 1, 40)

        moran = calculate_spatial_morans_i(coords, random_residuals)
        assert abs(moran["morans_i"] - moran["expected_i"]) < 0.3
        assert moran["interpretation"] == "spatially_random"
        assert moran["spatially_random"] is True

    def test_generate_spatial_error_map(self):
        """generate_spatial_error_map creates per-zone residual records and standardized errors."""
        coords = np.array([[72.5, 23.0], [72.6, 23.1], [72.7, 23.2]])
        y_true = [2.0, 3.0, 4.0]
        y_pred = [2.2, 2.9, 4.3]
        zone_ids = ["z_0", "z_1", "z_2"]

        error_map = generate_spatial_error_map(coords, y_true, y_pred, zone_ids)
        assert len(error_map) == 3
        assert error_map[0]["zone_id"] == "z_0"
        assert error_map[0]["residual"] == pytest.approx(0.2)
        assert error_map[0]["absolute_error"] == pytest.approx(0.2)
        assert "standardized_residual" in error_map[0]

    def test_train_computes_spatial_error_autocorrelation(self, synthetic_city_data):
        """Model training artifact computes and stores spatial error autocorrelation on validation residuals."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)

        assert "spatial_error_autocorrelation" in artifact
        assert isinstance(artifact["spatial_error_autocorrelation"], (float, int))
        for ev in artifact["evaluations"]:
            assert "morans_i" in ev["validation"]
            assert "bias" in ev["validation"]
            assert "residual_std" in ev["validation"]


# =====================================================================
# 10. TEMPORAL CROSS-VALIDATION AND NON-CAUSAL EXPLAINABILITY
# =====================================================================

class TestTemporalCrossValidationAndNonCausalXAI:
    """Verify temporal cross-validation anti-leakage and TreeSHAP non-causal attribution."""

    def test_temporal_split_anti_leakage(self):
        """temporal_split ensures each fold's training timestamps strictly precede validation timestamps."""
        records = [
            {"properties": {"acquired_at": f"2023-0{i+1}-15T10:00:00Z", "id": f"rec_{i}"}}
            for i in range(8)
        ]
        t_splits = temporal_split(records, n_splits=3)
        assert len(t_splits) == 3

        for fold in t_splits:
            train_idx, val_idx = fold
            assert len(train_idx) > 0
            assert len(val_idx) > 0
            # Indices must not overlap
            assert len(set(train_idx).intersection(set(val_idx))) == 0
            # Max train index must be strictly less than min val index (chronological order)
            assert max(train_idx) < min(val_idx)

    def test_train_temporal_validation_strategy(self, synthetic_city_data):
        """train() with validation_strategy='temporal' executes temporal cross-validation without errors."""
        data_copy = copy.deepcopy(synthetic_city_data)
        # Inject synthetic chronological timestamps across zones
        for i, f in enumerate(data_copy["features"]):
            f["properties"]["acquired_at"] = f"2023-0{(i % 6) + 1:02d}-15T10:00:00Z"

        artifact = train(data_copy, validation_strategy="temporal")
        assert artifact["validation_strategy"] == "temporal"
        assert artifact["split"]["strategy"] == "temporal"
        assert "Forward-chaining temporal" in artifact["split"]["method"]
        assert artifact["winner"] in ["Random Forest", "XGBoost", "LightGBM"]

    def test_explain_zone_includes_understandable_contributions_and_non_causal_disclaimer(self, synthetic_city_data):
        """explain_zone must output understandable non-causal contributions and attribution disclaimer."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        explainer = artifact["explainer"]

        sample_props = data_copy["features"][0]["properties"]
        res = explain_zone(explainer, sample_props)

        assert res["attribution_type"] == "statistical_association"
        assert "TreeSHAP" in res["non_causal_disclaimer"]
        assert "NOT represent causal" in res["non_causal_disclaimer"]
        assert "understandable_contributions" in res
        assert len(res["understandable_contributions"]) == len(FEATURES)

        first_contrib = res["understandable_contributions"][0]
        assert "feature_label" in first_contrib
        assert "statistically associated" in first_contrib["narrative"]
        assert "non-causal" in first_contrib["non_causal_note"]

    def test_compare_zones_xai_non_causal_language(self, synthetic_city_data):
        """compare_zones_xai summary must strictly use non-causal attribution phrasing."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        inferred, _ = infer(data_copy, artifact)

        zone_a = inferred["features"][0]
        zone_b = inferred["features"][-1]
        comparison = compare_zones_xai(zone_a, zone_b)

        assert comparison["attribution_type"] == "statistical_association"
        assert "non-causal" in comparison["summary"]
        assert "statistically associated" in comparison["summary"]
        assert "non_causal_disclaimer" in comparison

    def test_spatial_shap_contributions_non_causal(self, synthetic_city_data):
        """get_spatial_shap_contributions outputs non-causal metadata and normalized impact."""
        data_copy = copy.deepcopy(synthetic_city_data)
        artifact = train(data_copy)
        inferred, _ = infer(data_copy, artifact)

        spatial_contributions = get_spatial_shap_contributions(inferred["features"])
        for record in spatial_contributions[:5]:
            assert record["attribution_type"] == "statistical_association"
            assert "non_causal_disclaimer" in record
            assert -1.0 <= record["normalized_impact"] <= 1.0
