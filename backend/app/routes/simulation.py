"""Cooling intervention scenario simulation and physical capacity constraint evaluation."""

from typing import Literal
from fastapi import APIRouter
from app.db import save, records
from app.schemas import SimulationRequest, SimulationResponse
from app.services.planning import simulate, apply_convenience, INTERVENTIONS, ASSUMPTIONS
from app.services.state import zone

router = APIRouter(prefix="/api", tags=["simulation"])


@router.get("/interventions")
def interventions():
    """Catalog of supported cooling interventions, cooling rates, water requirements, and assumptions."""
    return {"interventions": INTERVENTIONS, "assumptions": ASSUMPTIONS}


@router.post("/simulation/run", response_model=SimulationResponse)
def simulation(req: SimulationRequest):
    """Simulate cooling potential and water consumption for user-defined interventions."""
    selected = zone(req.city, req.zone_id, req.mode)
    has_convenience = any(x is not None for x in (req.tree_count, req.roof_treated_pct, req.road_treated_pct))
    base_cov = {} if has_convenience and req.coverage == {"trees": 10, "cool_roofs": 15} else req.coverage
    coverage, notes = apply_convenience(
        selected,
        base_cov,
        req.tree_count,
        req.roof_treated_pct,
        req.road_treated_pct,
    )
    result = {
        **simulate(
            selected,
            coverage,
            req.water_limit,
            req.max_vegetation_pct,
        ),
        "name": req.name,
        "city": req.city,
        "conversion_notes": notes,
    }
    result["id"] = save("scenario", result)
    return result


@router.get("/simulation/results")
def scenarios(city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"):
    """Retrieve historical simulated intervention scenarios for a city."""
    return [r for r in records("scenario") if r.get("city") == city]
