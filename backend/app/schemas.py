from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict
from shapely.geometry import shape


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AreaRequest(StrictModel):
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"
    latitude: float | None = Field(None, ge=-80, le=80)
    longitude: float | None = Field(None, ge=-180, le=180)
    boundary: dict | None = None
    source: Literal[
        "sample",
        "weather",
        "osm",
        "earth_engine",
        "worldpop",
        "openaq",
        "stac",
        "sentinel_indices",
    ] = "sample"
    start_date: date | None = None
    end_date: date | None = None
    satellite_product: Literal["landsat", "sentinel", "modis", "worldcover", "srtm"] = (
        "landsat"
    )
    rural_reference: float = Field(33, ge=-40, le=70)

    @model_validator(mode="after")
    def validate_area(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both latitude and longitude.")
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Provide both dates.")
        if self.start_date and (
            self.end_date < self.start_date
            or (self.end_date - self.start_date).days > 366
        ):
            raise ValueError("Date range must be ordered and at most one year.")
        if self.boundary:
            geom = shape(self.boundary)
            if geom.geom_type != "Polygon" or not geom.is_valid or geom.is_empty:
                raise ValueError("A valid GeoJSON Polygon is required.")
            a, b, c, d = geom.bounds
            if (
                not (-180 <= a <= c <= 180 and -80 <= b <= d <= 80)
                or (c - a) * (d - b) > 4
            ):
                raise ValueError(
                    "Boundary must be within WGS84 and at most 4 square degrees."
                )
        return self


class ZoneRequest(StrictModel):
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"
    zone_id: str | None = None


class RiskRequest(ZoneRequest):
    hazard_weight: float = Field(1, ge=0.1, le=3)
    exposure_weight: float = Field(1, ge=0.1, le=3)
    vulnerability_weight: float = Field(1, ge=0.1, le=3)


class SimulationRequest(ZoneRequest):
    name: str = Field("New scenario", min_length=1, max_length=80)
    coverage: dict[str, float] = Field(
        default_factory=lambda: {"trees": 10, "cool_roofs": 15}
    )
    water_limit: float = Field(1000, ge=0, le=1e7)
    max_vegetation_pct: float = Field(40, ge=0, le=100)


class OptimizationRequest(ZoneRequest):
    zone_ids: list[str] = Field(default_factory=list, max_length=30)
    water_limit: float = Field(1000, ge=0, le=1e7)
    max_vegetation_pct: float = Field(40, ge=0, le=100)
    land_limit_pct: float = Field(100, ge=0, le=100)
    min_cooling: float = Field(0, ge=0, le=4)


class ChatRequest(ZoneRequest):
    message: str = Field(min_length=1, max_length=2000)
    provider: Literal["auto", "groq", "gemini", "local"] = "auto"


class AIFinding(StrictModel):
    statement: str = Field(max_length=700)
    fact_ids: list[str] = Field(min_length=1, max_length=10)


class AIResponse(StrictModel):
    summary: str = Field(max_length=1500)
    findings: list[AIFinding] = Field(max_length=6)
    actions: list[
        Literal[
            "trees",
            "vegetation",
            "parks",
            "cool_roofs",
            "pavements",
            "corridors",
            "roof_gardens",
            "water",
        ]
    ] = Field(max_length=8)
    limitations: list[str] = Field(max_length=8)


# Stable response contracts retain additional provenance fields for extensibility.
class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)


class HealthResponse(ResponseModel):
    status: Literal["ok"]
    database: str
    synthetic_predictions: bool


class PredictionResponse(ResponseModel):
    id: str
    name: str
    city: str
    predicted_suhii: float
    predicted_lst: float
    interval_low: float
    interval_high: float
    source: str
    shap: dict[str, float]


class PredictionBatchResponse(ResponseModel):
    predictions: list[PredictionResponse]
    model: dict


class ExplanationResponse(ResponseModel):
    zone_id: str
    prediction: float
    base_value: float
    contributions: dict[str, float]
    note: str


class SimulationResponse(ResponseModel):
    zone_id: str
    coverage: dict[str, float]
    feasible: bool
    violations: list[str]
    before_suhii: float
    after_suhii: float | None
    estimated_cooling: float | None
    sensitivity_range: list[float] | None
    water_m3_day: float
    hypothetical: bool
    assumptions: list[str]


class OptimizationResponse(ResponseModel):
    status: str
    feasible: bool
    selections: list[SimulationResponse]
    violations: list[str]
    hypothetical: bool
    assumptions: list[str]


class ChatResponse(AIResponse):
    provider: str
    fallback: bool
    facts: dict
    failures: list[dict[str, str]]
