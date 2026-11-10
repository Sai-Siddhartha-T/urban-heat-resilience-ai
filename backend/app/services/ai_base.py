"""Base interfaces and utilities for AI providers (backward-compatibility facade)."""

from app.services.llm.provider import (
    BaseLLMProvider,
    build_prompt,
    extract_json_str,
    sanitize_error,
)

__all__ = [
    "BaseLLMProvider",
    "build_prompt",
    "extract_json_str",
    "sanitize_error",
]
