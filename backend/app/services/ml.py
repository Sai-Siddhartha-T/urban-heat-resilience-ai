"""Spatial holdout evaluation, persisted inference, and actual TreeSHAP."""

import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import shap
from app.services.data import FEATURES
from app.db import ROOT, save

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
MODEL_DIR.mkdir(exist_ok=True, parents=True)


def metrics(y, p):
    return {
        "r2": float(r2_score(y, p)),
        "rmse": float(np.sqrt(mean_squared_error(y, p))),
        "mae": float(mean_absolute_error(y, p)),
    }


def train(data):
    frame = pd.DataFrame([f["properties"] for f in data["features"]])
    tr = frame.spatial_block.isin([0, 1, 2])
    val = frame.spatial_block.eq(3)
    test = frame.spatial_block.eq(5)
    if min(tr.sum(), val.sum(), test.sum()) < 15:
        raise ValueError(
            "Need at least 15 cells in each spatial partition. Use a larger area."
        )
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(frame.loc[tr, FEATURES])
    y = frame.loc[tr, "observed_suhii"].to_numpy()
    Xval = imputer.transform(frame.loc[val, FEATURES])
    Xtest = imputer.transform(frame.loc[test, FEATURES])
    candidates = {
        "Random Forest": RandomForestRegressor(
            n_estimators=180, min_samples_leaf=2, random_state=42, n_jobs=2
        ),
        "XGBoost": XGBRegressor(
            n_estimators=180,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.9,
            random_state=42,
            n_jobs=2,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=180,
            max_depth=4,
            num_leaves=12,
            learning_rate=0.04,
            verbosity=-1,
            random_state=42,
            n_jobs=2,
        ),
    }
    evaluations = []
    for name, model in candidates.items():
        model.fit(X, y)
        evaluations.append(
            {
                "model": name,
                "validation": metrics(
                    frame.loc[val, "observed_suhii"], model.predict(Xval)
                ),
                "test": metrics(
                    frame.loc[test, "observed_suhii"], model.predict(Xtest)
                ),
            }
        )
    winner = min(evaluations, key=lambda m: m["validation"]["rmse"])["model"]
    model = candidates[winner]
    interval = float(
        np.quantile(
            np.abs(frame.loc[val, "observed_suhii"].to_numpy() - model.predict(Xval)),
            0.90,
        )
    )
    artifact = {
        "model": model,
        "imputer": imputer,
        "winner": winner,
        "interval": interval,
        "evaluations": evaluations,
        "features": FEATURES,
        "metadata": data["metadata"],
        "split": {
            "training": int(tr.sum()),
            "validation": int(val.sum()),
            "test": int(test.sum()),
            "buffer": int(frame.spatial_block.eq(4).sum()),
            "method": "Western 9 columns train; next 3 validate; 3-column buffer; eastern 3 test. No coordinates or target-derived predictors.",
        },
    }
    joblib.dump(artifact, MODEL_DIR / f'{data["metadata"]["city"].lower()}.joblib')
    save(
        "model_evaluation",
        describe(artifact),
        record_id=f'model-{data["metadata"]["city"]}',
    )
    return artifact


def describe(a):
    return {
        k: a[k]
        for k in ["winner", "interval", "evaluations", "metadata", "split", "features"]
    }


def load_or_train(data):
    path = MODEL_DIR / f'{data["metadata"]["city"].lower()}.joblib'
    if path.exists():
        a = joblib.load(path)
        if a["metadata"]["generated_at"] == data["metadata"]["generated_at"]:
            return a
    return train(data)


def infer(data, a):
    frame = pd.DataFrame([f["properties"] for f in data["features"]])
    X = a["imputer"].transform(frame[FEATURES])
    predictions = a["model"].predict(X)
    explanation = shap.TreeExplainer(a["model"])(X)
    global_values = np.mean(np.abs(explanation.values), axis=0)
    for i, f in enumerate(data["features"]):
        p = f["properties"]
        value = float(predictions[i])
        p.update(
            {
                "predicted_suhii": value,
                "predicted_lst": value + p["rural_reference"],
                "interval_low": value - a["interval"],
                "interval_high": value + a["interval"],
                "hotspot": value >= 4,
                "partition": (
                    "test"
                    if p["spatial_block"] == 5
                    else (
                        "buffer"
                        if p["spatial_block"] == 4
                        else "validation" if p["spatial_block"] == 3 else "training"
                    )
                ),
                "shap": {
                    name: float(explanation.values[i, j])
                    for j, name in enumerate(FEATURES)
                },
                "shap_base": float(np.asarray(explanation.base_values).reshape(-1)[i]),
            }
        )
    return data, sorted(
        [
            {"feature": name, "importance": float(global_values[i])}
            for i, name in enumerate(FEATURES)
        ],
        key=lambda f: -f["importance"],
    )
