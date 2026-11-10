"""Groq LLM provider facade (backward-compatibility module)."""

from app.services.llm.groq import GroqProvider, groq_provider

__all__ = ["GroqProvider", "groq_provider"]
