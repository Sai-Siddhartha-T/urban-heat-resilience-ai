"""Routes package: exports all subdivided APIRouter instances."""

from app.routes.heat import router as heat_router
from app.routes.models import router as models_router
from app.routes.simulation import router as simulation_router
from app.routes.optimization import router as optimization_router
from app.routes.risk import router as risk_router
from app.routes.data import router as data_router
from app.routes.ai import router as ai_router
from app.routes.reports import router as reports_router
from app.routes.workspace import router as workspace_router

__all__ = [
    "heat_router",
    "models_router",
    "simulation_router",
    "optimization_router",
    "risk_router",
    "data_router",
    "ai_router",
    "reports_router",
    "workspace_router",
]
