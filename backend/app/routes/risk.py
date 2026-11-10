"""Parametric climate risk calculation across hazard, exposure, and vulnerability."""

from fastapi import APIRouter
from app.db import save
from app.schemas import RiskRequest
from app.services.risk import risk
from app.services.state import state, zone

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/analyze")
def analyze_risk(req: RiskRequest):
    """Compute customized hazard, exposure, vulnerability, and composite risk scores."""
    items = (
        [zone(req.city, req.zone_id, req.mode)]
        if req.zone_id
        else [
            f["properties"]
            for f in state(req.city, req.mode)["data"]["features"]
        ]
    )
    result = {
        "city": req.city,
        "weights": [req.hazard_weight, req.exposure_weight, req.vulnerability_weight],
        "zones": [
            {
                "zone_id": p["id"],
                **risk(
                    p,
                    (req.hazard_weight, req.exposure_weight, req.vulnerability_weight),
                ),
            }
            for p in items
        ],
    }
    save("risk", result)
    return result
