"""Normal-mode workspace endpoints independent of the analytical demo state."""

from fastapi import APIRouter

from app.schemas.evidence import CityName, WorkspaceResponse
from app.services.evidence import workspace

router = APIRouter(prefix="/api", tags=["workspace"])


@router.get("/workspace", response_model=WorkspaceResponse)
def get_workspace(city: CityName = "Ahmedabad"):
    return workspace(city)
