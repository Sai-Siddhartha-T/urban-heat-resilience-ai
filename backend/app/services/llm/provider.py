"""Abstract base class and core utilities for LLM provider implementations."""

from abc import ABC, abstractmethod
import json
import logging
import re
from typing import Any
import httpx
from app.schemas.ai import AIResponse

log = logging.getLogger("heatwise.llm.provider")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM inference providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'groq', 'gemini')."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether provider credentials and model identifier are configured."""
        ...

    @abstractmethod
    def get_model(self) -> str | None:
        """Return configured model identifier."""
        ...

    @abstractmethod
    async def check_availability(self, client: httpx.AsyncClient) -> bool:
        """Verify model availability against provider's model discovery endpoint."""
        ...

    @abstractmethod
    async def generate(
        self,
        message: str,
        facts: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """Generate structured reasoning completion from provider, returning raw JSON string."""
        ...


def build_prompt(message: str, facts: dict[str, Any]) -> str:
    """
    Construct strictly grounded decision-support prompt enforcing AIResponse JSON schema.
    
    Guides the assistant to answer key urban heat resilience questions:
    1. Why is this zone experiencing high heat (zone LST, weather, TreeSHAP)?
    2. Which environmental factors contribute most (citing TreeSHAP in 'drivers')?
    3. Which areas should be prioritized (citing 'risk' scores: hazard, exposure, vulnerability)?
    4. Which cooling interventions are suitable (adhering strictly to physical 'constraints')?
    5. Why did the optimizer select a particular combination (referencing 'optimization')?
    6. What happens under alternative scenarios (referencing 'scenarios')?
    7. What environmental conditions apply (referencing 'weather', 'air_quality', 'groundwater')?
    8. What are the limitations of the recommendations (synthetic predictions, air temp differences)?
    """
    return (
        "You are Heatwise's urban heat resilience decision-support assistant. "
        "Explain urban surface heat evidence truthfully, never inventing observations or causality. "
        "All prediction and demographic inputs are SYNTHETIC. Cooling estimates are hypothetical. "
        "Answer the user using only the supplied facts. Do not put any numbers or statistics in prose; "
        "the UI displays verified numerical values separately. "
        "For each finding, cite the exact supplied fact keys (e.g., 'prediction', 'drivers', 'risk', "
        "'constraints', 'model', 'optimization', 'scenarios', 'weather', 'air_quality', 'groundwater'). "
        "The 'drivers' key contains exact additive TreeSHAP attributions; explain them as model associations. "
        "The 'risk' key contains IPCC Hazard, Exposure, Vulnerability components; explain prioritization accordingly. "
        "The 'weather', 'air_quality', and 'groundwater' keys contain local environmental telemetry when available. "
        "Only suggest actions feasible for the supplied constraints; never recommend ground modifications on protected land. "
        "Output ONLY a valid JSON object strictly matching this schema:\n"
        + json.dumps(AIResponse.model_json_schema())
        + "\nFACTS:\n"
        + json.dumps(facts)
        + "\nUSER QUESTION:\n"
        + message
    )


def extract_json_str(text: str) -> str:
    """Strip markdown code block fences and extract clean JSON text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    # If there is leading or trailing prose around the JSON object, extract outermost braces
    if not cleaned.startswith("{") and "{" in cleaned:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1]
    return cleaned


def sanitize_error(err: Exception | str) -> str:
    """Mask credential signatures from error strings to prevent accidental key leakage."""
    msg = str(err)
    return re.sub(
        r"(?:gsk_[a-zA-Z0-9_\-]+|AIza[a-zA-Z0-9_\-]+|ya29\.[a-zA-Z0-9_\-]+|AQ\.[a-zA-Z0-9_\-]+)",
        "[REDACTED]",
        msg,
    )
