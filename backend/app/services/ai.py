"""AI service layer orchestrating LLM providers with strict grounding, guardrails, and deterministic fallback.

Maintains complete backward compatibility by re-exporting provider interfaces,
guardrails, schemas, and orchestration functions from app.services.llm and app.schemas.ai.
"""

import logging
from typing import Any
import httpx

from app.schemas.ai import (
    AIFinding,
    AIResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.planning import simulate
from app.services.llm import (
    ENTITY_WHITELIST,
    NUMERIC_MEASUREMENT_PATTERN,
    ORDERED_LIST_MARKER,
    YEAR_DATE_PATTERN,
    BaseLLMProvider,
    GeminiProvider,
    GroqProvider,
    PROVIDERS,
    SETUP_GUIDANCE,
    build_prompt,
    call_provider,
    context_for,
    deterministic_placeholder,
    extract_json_str,
    extract_numbers_from_facts,
    gemini_provider,
    get_provider,
    groq_provider,
    orchestrate_chat,
    provider_status,
    sanitize_error,
    validate_action_feasibility,
    validate_citations,
    validate_numeric_guardrails,
)

log = logging.getLogger("heatwise.ai")


async def chat(
    message: str,
    provider: str,
    p: dict[str, Any],
    model: dict[str, Any],
    optimization: dict[str, Any] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Execute grounded chat with multi-provider failover and deterministic fallback."""
    return await orchestrate_chat(
        message=message,
        provider=provider,
        p=p,
        model=model,
        optimization=optimization,
        scenarios=scenarios,
        client=client,
    )


__all__ = [
    "AIFinding",
    "AIResponse",
    "ChatRequest",
    "ChatResponse",
    "BaseLLMProvider",
    "GroqProvider",
    "groq_provider",
    "GeminiProvider",
    "gemini_provider",
    "PROVIDERS",
    "SETUP_GUIDANCE",
    "get_provider",
    "provider_status",
    "build_prompt",
    "extract_json_str",
    "sanitize_error",
    "ENTITY_WHITELIST",
    "ORDERED_LIST_MARKER",
    "YEAR_DATE_PATTERN",
    "NUMERIC_MEASUREMENT_PATTERN",
    "extract_numbers_from_facts",
    "validate_numeric_guardrails",
    "validate_citations",
    "validate_action_feasibility",
    "context_for",
    "call_provider",
    "deterministic_placeholder",
    "chat",
    "simulate",
]
