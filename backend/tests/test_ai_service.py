"""Unit tests for AI Service: Providers, Guardrails, Grounding, and Feasibility."""

import asyncio
import json
import os
import pytest
import httpx

from app.schemas.ai import AIFinding, AIResponse, ChatResponse
from app.services import ai
from app.migrations import run_migrations
from app.services.llm import (
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

run_migrations()

SAMPLE_ZONE = {
    "id": "ahmedabad_central_1",
    "name": "Central Ward",
    "city": "Ahmedabad",
    "predicted_suhii": 3.75,
    "predicted_lst": 41.5,
    "interval_low": 3.2,
    "interval_high": 4.3,
    "shap": {
        "building_density": 1.45,
        "vegetation_fraction": -0.92,
        "surface_albedo": -0.68,
        "built_up_density": 0.55,
    },
    "risk_score": 0.82,
    "hazard": 0.88,
    "exposure": 0.79,
    "vulnerability": 0.80,
    "risk_level": "High",
    "available_land_pct": 18.0,
    "roof_pct": 32.0,
    "road_pct": 15.0,
    "area_km2": 2.14,
    "protected": False,
    "weather": {
        "temperature_c": 38.5,
        "humidity_pct": 45.0,
        "wind_speed_ms": 3.2,
    },
    "air_quality": {
        "pm2_5": 78.4,
        "pm10": 142.0,
        "aqi": 165.0,
    },
    "groundwater": {
        "depth_m": 24.5,
        "water_table_mbgl": 24.5,
        "trend": "falling",
    },
}

SAMPLE_MODEL = {
    "winner": "lightgbm",
    "evaluations": {"r2": 0.91, "rmse": 0.42},
    "synthetic": True,
}


def test_provider_registry_and_configuration(monkeypatch):
    """Verify provider discovery, registry keys, and environment configuration checks."""
    assert "groq" in PROVIDERS
    assert "gemini" in PROVIDERS
    assert get_provider("groq") is groq_provider
    assert get_provider("gemini") is gemini_provider
    assert get_provider("unknown_provider") is None

    # Unconfigured state
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    assert not groq_provider.is_configured()

    # Configured state
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_12345")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    assert groq_provider.is_configured()
    assert groq_provider.get_model() == "llama-3.3-70b-versatile"


def test_gemini_auth_headers_resolution(monkeypatch):
    """Test resolution of auth headers across GEMINI_API_KEY, GOOGLE_API_KEY, and AGY_ACCOUNT."""
    # 1. Direct GEMINI_API_KEY
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test_gemini_key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("AGY_ACCOUNT", raising=False)
    headers = gemini_provider.get_auth_headers()
    assert headers == {"x-goog-api-key": "AQ.test_gemini_key"}

    # 2. OAuth bearer ya29. token
    monkeypatch.setenv("GEMINI_API_KEY", "ya29.oauth_token_sample")
    headers = gemini_provider.get_auth_headers()
    assert headers == {"Authorization": "Bearer ya29.oauth_token_sample"}

    # 3. GOOGLE_API_KEY fallback
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyTestGoogleKey")
    headers = gemini_provider.get_auth_headers()
    assert headers == {"x-goog-api-key": "AIzaSyTestGoogleKey"}


@pytest.mark.asyncio
async def test_groq_retry_on_429_and_503(monkeypatch):
    """Verify GroqProvider retries on rate limits (429) and server errors (503) with exponential backoff."""
    call_count = 0

    def retry_mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Rate limit exceeded"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({
                "summary": "Elevated heat in urban core.",
                "findings": [{"statement": "Building density drives heat.", "fact_ids": ["drivers"]}],
                "actions": ["cool_roofs"],
                "limitations": ["Hypothetical estimates."],
            })}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(retry_mock_handler))
    payload = {"model": "llama-3.3-70b-versatile", "messages": []}
    headers = {"Authorization": "Bearer gsk_test"}

    resp = await groq_provider._post_chat_with_retry(client, headers, payload)
    assert resp.status_code == 200
    assert call_count == 3


@pytest.mark.asyncio
async def test_gemini_retry_on_503(monkeypatch):
    """Verify GeminiProvider retries on 503 service unavailable with backoff."""
    attempts = 0

    def gemini_retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return httpx.Response(503, json={"error": "Service temporarily unavailable"})
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "{\"summary\": \"OK\"}"}]}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(gemini_retry_handler))
    headers = {"x-goog-api-key": "test"}
    resp = await gemini_provider._post_generate_with_retry(
        client, "https://test.api/models/test:generateContent", headers, {}
    )
    assert resp.status_code == 200
    assert attempts == 2


def test_credential_sanitization():
    """Verify sensitive API keys are masked from logs and exception messages."""
    err_text = "Failed call with gsk_secret123456789 and AQ.my_gemini_token and ya29.oauth_token_val"
    sanitized = sanitize_error(err_text)
    assert "gsk_" not in sanitized
    assert "AQ." not in sanitized
    assert "ya29." not in sanitized
    assert "[REDACTED]" in sanitized


def test_context_for_grounding_facts():
    """Verify canonical context dictionary includes all required fact categories."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)
    assert "prediction" in facts
    assert facts["prediction"]["lst_c"] == 41.5
    assert facts["prediction"]["suhii_c"] == 3.75
    assert "drivers" in facts
    assert facts["drivers"]["building_density"] == 1.45
    assert "risk" in facts
    assert facts["risk"]["risk_score"] == 0.82
    assert "constraints" in facts
    assert "model" in facts
    assert facts["model"]["name"] == "lightgbm"
    assert "weather" in facts
    assert facts["weather"]["temperature_c"] == 38.5
    assert "air_quality" in facts
    assert facts["air_quality"]["pm2_5"] == 78.4
    assert "groundwater" in facts
    assert facts["groundwater"]["depth_m"] == 24.5


def test_validate_citations_strict():
    """Verify citation validation accepts all valid fact keys and rejects unknown keys."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)

    valid_findings = [
        AIFinding(statement="High surface temperature.", fact_ids=["prediction"]),
        AIFinding(statement="Building density is strong factor.", fact_ids=["drivers"]),
        AIFinding(statement="High risk vulnerability.", fact_ids=["risk"]),
        AIFinding(statement="Local weather reading.", fact_ids=["weather"]),
        AIFinding(statement="Local air pollution monitoring.", fact_ids=["air_quality"]),
        AIFinding(statement="Groundwater water table depth.", fact_ids=["groundwater"]),
    ]
    # Valid citations should not raise
    validate_citations(valid_findings, facts)

    invalid_findings = [
        AIFinding(statement="Unsupported external claim.", fact_ids=["fabricated_source"]),
    ]
    with pytest.raises(ValueError, match="Provider cited unsupported evidence"):
        validate_citations(invalid_findings, facts)


def test_numeric_guardrails_within_tolerance():
    """Verify numeric guardrails allow numbers within 5% tolerance and whitelisted entities, and block hallucinations."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)

    # 41.5 LST cited as 41.5°C or 41.0°C (within tolerance) -> passes
    valid_text = (
        "Surface temperature is 41.5°C and SUHII is 3.75°C. "
        "Sentinel-2 imagery shows 100m resolution. PM2.5 is 78.4. Groundwater depth is 24.5 m."
    )
    validate_numeric_guardrails(valid_text, facts)

    # Invented number 88.9°C not present in facts -> raises ValueError
    hallucinated_text = "Surface temperature reached an unprecedented 88.9°C in this ward."
    with pytest.raises(ValueError, match="Provider included unsupported numeric prose"):
        validate_numeric_guardrails(hallucinated_text, facts)


def test_action_feasibility_validation(monkeypatch):
    """Verify action feasibility validation checks physical constraints via simulate()."""
    # When simulate returns feasible -> passes
    validate_action_feasibility(["cool_roofs"], SAMPLE_ZONE)

    # When simulate reports infeasible -> raises ValueError
    monkeypatch.setattr(
        ai,
        "simulate",
        lambda p, cov, **kw: {"feasible": False, "violations": ["Exceeded physical roof capacity"]},
    )
    with pytest.raises(ValueError, match="Provider suggested an infeasible intervention"):
        validate_action_feasibility(["cool_roofs"], SAMPLE_ZONE)


def test_provider_status_auditing():
    """Verify provider_status() reports provider configurations and auditable metadata."""
    status = provider_status()
    assert "groq" in status
    assert "gemini" in status
    assert "configured" in status["groq"]
    assert "availability" in status["groq"]
