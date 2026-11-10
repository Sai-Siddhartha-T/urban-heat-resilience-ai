"""Combinatorial discrete optimization via Google OR-Tools CP-SAT solver."""

from typing import Literal
from fastapi import APIRouter
from app.db import save, records
from app.schemas import OptimizationRequest, OptimizationResponse
from app.services.optimization import optimize
from app.services.state import state, zone

router = APIRouter(prefix="/api/optimization", tags=["optimization"])


@router.post("/run", response_model=OptimizationResponse)
def run_optimization(req: OptimizationRequest):
    """Find pareto-optimal intervention allocation across zones given physical, environmental, land & water limits."""
    if len(req.zone_ids) != len(set(req.zone_ids)):
        raise ValueError("Duplicate zones are not allowed.")
    selected = (
        [zone(req.city, z, req.mode) for z in req.zone_ids]
        if req.zone_ids
        else sorted(
            (
                f["properties"]
                for f in state(req.city, req.mode)["data"]["features"]
            ),
            key=lambda p: -p["risk_score"],
        )[:5]
    )
    result = optimize(
        selected,
        water_limit=req.water_limit,
        max_vegetation_pct=req.max_vegetation_pct,
        min_cooling=req.min_cooling,
        land_limit_pct=req.land_limit_pct,
    )
    result["city"] = req.city
    if result["feasible"] and not result.get("alternative"):
        alternate = optimize(
            selected,
            water_limit=req.water_limit * 0.5,
            max_vegetation_pct=req.max_vegetation_pct,
            min_cooling=0,
            land_limit_pct=req.land_limit_pct,
            include_alternative=False,
        )
        result["alternative"] = {"label": "Half-water alternative", **alternate}
    result["id"] = save("optimization", result)
    return result


@router.get("/results")
def optimization_results(
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad",
):
    """Retrieve historical optimization runs for a city."""
    return [r for r in records("optimization") if r.get("city") == city]
