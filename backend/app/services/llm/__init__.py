"""LLM service package providing provider abstraction, strict grounding guardrails, and deterministic fallback."""

from app.services.llm.provider import (
    BaseLLMProvider,
    build_prompt,
    extract_json_str,
    sanitize_error,
)
from app.services.llm.groq import GroqProvider, groq_provider
from app.services.llm.gemini import GeminiProvider, gemini_provider
from app.services.llm.guardrails import (
    ENTITY_WHITELIST,
    NUMERIC_MEASUREMENT_PATTERN,
    ORDERED_LIST_MARKER,
    YEAR_DATE_PATTERN,
    extract_numbers_from_facts,
    validate_action_feasibility,
    validate_citations,
    validate_numeric_guardrails,
)
from app.services.llm.fallback import (
    PROVIDERS,
    SETUP_GUIDANCE,
    call_provider,
    context_for,
    deterministic_placeholder,
    get_provider,
    orchestrate_chat,
    provider_status,
)

__all__ = [
    "BaseLLMProvider",
    "build_prompt",
    "extract_json_str",
    "sanitize_error",
    "GroqProvider",
    "groq_provider",
    "GeminiProvider",
    "gemini_provider",
    "ENTITY_WHITELIST",
    "NUMERIC_MEASUREMENT_PATTERN",
    "ORDERED_LIST_MARKER",
    "YEAR_DATE_PATTERN",
    "extract_numbers_from_facts",
    "validate_action_feasibility",
    "validate_citations",
    "validate_numeric_guardrails",
    "PROVIDERS",
    "SETUP_GUIDANCE",
    "call_provider",
    "context_for",
    "deterministic_placeholder",
    "get_provider",
    "orchestrate_chat",
    "provider_status",
]
