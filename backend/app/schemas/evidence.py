"""Versioned contracts for partial environmental evidence and geographic layers."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CityName = Literal["Ahmedabad", "Delhi", "Hyderabad"]
EvidenceKind = Literal["observed", "modelled", "forecast", "predicted", "hypothetical"]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EvidenceProvenance(EvidenceModel):
    source: str
    category: str
    mode: Literal["live", "demo"] = "live"
    kind: EvidenceKind = "observed"
    status: str = "latest_available"
    retrieved_at: str
    observation_time: str | list[str] | None = None
    city: str | None = None
    coverage: str | None = None
    resolution: str | None = None
    units: dict[str, str] = Field(default_factory=dict)
    processing: str | None = None
    quality: str | None = None
    freshness: Literal["current", "latest_available", "historical", "stale", "unknown"] = "unknown"
    analysis_ready: bool = False
    limitations: list[str] = Field(default_factory=list)


class EvidenceAssetSummary(EvidenceModel):
    id: str
    city: str | None
    category: str
    source: str
    mode: Literal["live", "demo"]
    analysis_ready: bool
    provenance: EvidenceProvenance
    created_at: str | None


class EvidenceAsset(EvidenceAssetSummary):
    payload: dict[str, Any]


class RasterGrid(EvidenceModel):
    """Measured grid: affine coefficients a,b,c,d,e,f in the stated CRS."""

    crs: str
    transform: list[float] = Field(min_length=6, max_length=6)
    shape: tuple[int, int]
    values: list[list[float | None]]
    bounds: tuple[float, float, float, float] | None = None

    @model_validator(mode="after")
    def grid_dimensions(self):
        height, width = self.shape
        if height < 1 or width < 1 or height > 2048 or width > 2048:
            raise ValueError("Raster display grid dimensions must be between 1 and 2048.")
        if len(self.values) != height or any(len(row) != width for row in self.values):
            raise ValueError("Raster values must match the declared grid shape.")
        return self


class MapLayer(EvidenceModel):
    id: str
    name: str
    variable: str
    status: Literal["available", "unavailable"]
    kind: EvidenceKind
    source: str | None = None
    observation_time: str | list[str] | None = None
    retrieved_at: str | None = None
    resolution: str | None = None
    unit: str | None = None
    asset_id: str | None = None
    geojson: dict[str, Any] | None = None
    raster: RasterGrid | None = None
    reason: str | None = None
    limitations: list[str] = Field(default_factory=list)


class Capability(EvidenceModel):
    status: Literal["available", "unavailable", "partial"]
    reason: str | None = None
    asset_ids: list[str] = Field(default_factory=list)


class AnalysisAvailability(EvidenceModel):
    status: Literal["available", "unavailable"]
    reason: str | None
    synthetic: bool = False
    dataset_id: str | None = None


class WorkspaceResponse(EvidenceModel):
    schema_version: Literal["1"] = "1"
    city: CityName
    center: tuple[float, float]
    mode: Literal["normal"] = "normal"
    analysis: AnalysisAvailability
    assets: list[EvidenceAssetSummary]
    layers: list[MapLayer]
    capabilities: dict[str, Capability]
    limitations: list[str]


class LayersResponse(EvidenceModel):
    city: CityName
    layers: list[MapLayer]
