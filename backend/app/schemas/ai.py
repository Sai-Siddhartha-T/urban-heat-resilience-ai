"""Pydantic v2 schemas for Generative AI decision support and chat contracts."""

import os
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model enforcing strict validation and forbidding arbitrary fields."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ChatRequest(StrictModel):
    """User query and targeting context for the heat resilience assistant."""
    city: Literal["Ahmedabad", "Delhi", "Hyderabad"] = "Ahmedabad"
    mode: Literal["normal", "demo"] | None = None
    zone_id: str | None = None
    features: dict[str, float] | None = None
    message: str = Field(min_length=1, max_length=2000)
    provider: Literal["auto", "groq", "gemini", "local"] = "auto"

    @model_validator(mode="before")
    @classmethod
    def resolve_mode_default(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get("mode") is None:
                if os.getenv("HEATWISE_DEMO_MODE") == "1" or os.getenv("TESTING") == "1":
                    values["mode"] = "demo"
        return values


class AIFinding(StrictModel):
    """Grounded finding strictly citing verified fact identifiers."""
    statement: str = Field(max_length=700)
    fact_ids: list[str] = Field(min_length=1, max_length=10)


class AIResponse(StrictModel):
    """Structured response expected from LLM provider completions."""
    summary: str = Field(max_length=2500)
    findings: list[AIFinding] = Field(max_length=10)
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
    limitations: list[str] = Field(max_length=10)


class ChatResponse(AIResponse):
    """Complete chat response returned to the client with execution metadata."""
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    provider: str
    fallback: bool
    facts: dict[str, Any]
    failures: list[dict[str, str]] = Field(default_factory=list)
    synthetic_fallback: bool = False
    label: str | None = None
    status: Literal["ok", "degraded", "error"] = "ok"
    error_message: str | None = None
    setup_guidance: str | None = None
    citations: list[str] = Field(default_factory=list)
    response: str = ""

    @model_validator(mode="after")
    def populate_response_and_citations(self) -> "ChatResponse":
        if not self.response:
            self.response = self.summary
        if not self.citations and self.findings:
            cits: list[str] = []
            for f in self.findings:
                for fid in f.fact_ids:
                    if fid not in cits:
                        cits.append(fid)
            self.citations = cits
        return self
