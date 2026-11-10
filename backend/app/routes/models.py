"""ML model tournament inspection, retraining, TreeSHAP explainability, and feature importance."""

from typing import Literal
from fastapi import APIRouter
from app.schemas import ZoneRequest, ExplanationResponse
from app.services.state import state, zone, retrain_state

router = APIRouter(prefix="/api", tags=["models", "xai"])


@router.get("/models")
def models(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    mode: Literal["normal", "demo"] | None = None,
):
    """Retrieve winning model metadata, validation scores, and spatial holdout split."""
    return state(city, mode)["model"]


@router.post("/models/train")
def train_models(req: ZoneRequest):
    """Force re-run spatial cross-validation tournament across RF, XGBoost, and LightGBM."""
    return retrain_state(req.city, req.mode)["model"]


@router.post("/xai/explain", response_model=ExplanationResponse)
def explain(req: ZoneRequest):
    """TreeSHAP local feature attribution for a specific zone."""
    p = zone(req.city, req.zone_id, req.mode)
    return {
        "zone_id": p["id"],
        "prediction": p["predicted_suhii"],
        "base_value": p["shap_base"],
        "contributions": p["shap"],
        "note": "Actual TreeSHAP model contributions; associations are not causal intervention effects.",
    }


@router.get("/xai/importance")
def importance(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    mode: Literal["normal", "demo"] | None = None,
):
    """Global mean absolute SHAP feature importance rankings."""
    return state(city, mode)["importance"]


@router.post("/xai/shap")
def shap_explain(req: ZoneRequest):
    """TreeSHAP feature attributions and values for a zone or all zones via POST."""
    if req.zone_id:
        p = zone(req.city, req.zone_id, req.mode)
        return {
            "city": req.city,
            "zone_id": p["id"],
            "prediction": p["predicted_suhii"],
            "base_value": p.get("shap_base", 0.0),
            "shap_values": p.get("shap", {}),
            "contributions": p.get("shap", {}),
            "importance": state(req.city, req.mode)["importance"],
            "note": "TreeSHAP local feature contributions; associations are not causal intervention effects.",
        }
    st = state(req.city, req.mode)
    features = st["data"]["features"]
    return {
        "city": req.city,
        "shap_values": [
            {
                "zone_id": f["properties"]["id"],
                "prediction": f["properties"].get("predicted_suhii", 0.0),
                "base_value": f["properties"].get("shap_base", 0.0),
                "shap": f["properties"].get("shap", {}),
            }
            for f in features
        ],
        "global_importance": st["importance"],
        "note": "TreeSHAP global and local feature attributions across zones.",
    }


@router.get("/xai/shap")
def shap_explain_get(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
    zone_id: str | None = None,
    mode: Literal["normal", "demo"] | None = None,
):
    """TreeSHAP feature attributions and values for a zone or all zones via GET."""
    if zone_id:
        p = zone(city, zone_id, mode)
        return {
            "city": city,
            "zone_id": p["id"],
            "prediction": p["predicted_suhii"],
            "base_value": p.get("shap_base", 0.0),
            "shap_values": p.get("shap", {}),
            "contributions": p.get("shap", {}),
            "importance": state(city, mode)["importance"],
            "note": "TreeSHAP local feature contributions; associations are not causal intervention effects.",
        }
    st = state(city, mode)
    features = st["data"]["features"]
    return {
        "city": city,
        "shap_values": [
            {
                "zone_id": f["properties"]["id"],
                "prediction": f["properties"].get("predicted_suhii", 0.0),
                "base_value": f["properties"].get("shap_base", 0.0),
                "shap": f["properties"].get("shap", {}),
            }
            for f in features
        ],
        "global_importance": st["importance"],
        "note": "TreeSHAP global and local feature attributions across zones.",
    }
