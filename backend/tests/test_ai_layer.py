"""Comprehensive unit and integration tests for AI Layer: Groq, Gemini, Schemas, Guardrails, and Fallback."""

import asyncio
import json
import os
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    AIFinding as SchemasAIFinding,
    AIResponse as SchemasAIResponse,
    ChatRequest as SchemasChatRequest,
    ChatResponse as SchemasChatResponse,
)
from app.schemas.ai import (
    AIFinding,
    AIResponse,
    ChatRequest,
    ChatResponse,
)
from app.services import ai
from app.services.llm import (
    BaseLLMProvider,
    GeminiProvider,
    GroqProvider,
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
}

SAMPLE_MODEL = {
    "winner": "lightgbm",
    "evaluations": {"r2": 0.91, "rmse": 0.42},
    "synthetic": True,
}

SAMPLE_OPTIMIZATION = {
    "available": True,
    "status": "Optimal",
    "mean_cooling": 1.15,
    "selections": [
        {"zone_id": "ahmedabad_central_1", "coverage": {"cool_roofs": 25.0, "trees": 10.0}}
    ],
}

SAMPLE_SCENARIOS = [
    {
        "name": "Intensive greening",
        "coverage": {"trees": 20.0},
        "cooling": 0.95,
    }
]

VALID_AI_OUTPUT = {
    "summary": "Building density is strongly associated with elevated surface heat in this central ward.",
    "findings": [
        {
            "statement": "TreeSHAP attributions indicate building density is the primary factor increasing surface heat.",
            "fact_ids": ["drivers", "prediction"],
        },
        {
            "statement": "Available roof and land space offer opportunities for cooling surface treatments.",
            "fact_ids": ["constraints"],
        },
    ],
    "actions": ["cool_roofs", "trees"],
    "limitations": [
        "Synthetic surface heat predictions do not measure direct air temperature.",
        "Ground calibration is required before implementing urban interventions.",
    ],
}


# ============================================================================
# 1. Structured Response Schemas & Re-export Tests
# ============================================================================

def test_schemas_types_and_reexports():
    """Verify schemas in app.schemas.ai are identical to app.schemas and app.services.ai re-exports."""
    assert SchemasChatRequest is ChatRequest
    assert SchemasAIFinding is AIFinding
    assert SchemasAIResponse is AIResponse
    assert SchemasChatResponse is ChatResponse
    assert ai.ChatRequest is ChatRequest
    assert ai.ChatResponse is ChatResponse
    assert ai.AIResponse is AIResponse


def test_pydantic_v2_schema_validation():
    """Verify strict Pydantic v2 validation contracts."""
    req = ChatRequest(
        city="Ahmedabad",
        zone_id="ahmedabad_central_1",
        message="Why is this zone so hot?",
        provider="auto",
    )
    assert req.city == "Ahmedabad"
    assert req.provider == "auto"

    # Forbids arbitrary unknown fields
    with pytest.raises(Exception):
        ChatRequest(city="Ahmedabad", message="test", unknown_field=123)

    # Validates AIResponse and ChatResponse
    resp = AIResponse(
        summary="Test summary",
        findings=[AIFinding(statement="Test finding", fact_ids=["drivers"])],
        actions=["cool_roofs"],
        limitations=["Test limitation"],
    )
    assert len(resp.findings) == 1
    assert resp.actions == ["cool_roofs"]

    chat_resp = ChatResponse(
        **resp.model_dump(),
        provider="groq",
        fallback=False,
        facts={"drivers": {}},
        failures=[],
        synthetic_fallback=False,
    )
    assert chat_resp.provider == "groq"
    assert chat_resp.fallback is False


# ============================================================================
# 2. Provider Abstraction & Discovery Tests
# ============================================================================

def test_provider_registry_and_status(monkeypatch):
    """Verify provider registry and configuration status reporting."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy_123")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("AGY_ACCOUNT", raising=False)

    assert get_provider("groq") is groq_provider
    assert get_provider("gemini") is gemini_provider
    assert get_provider("unknown") is None

    status = provider_status()
    assert status["groq"]["configured"] is True
    assert status["groq"]["model"] == "llama-3.3-70b-versatile"
    assert status["gemini"]["configured"] is False


def test_groq_model_discovery(monkeypatch):
    """Verify GroqProvider check_availability against GET /models endpoint."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openai/v1/models"
        assert request.headers.get("authorization") == "Bearer gsk_valid"
        return httpx.Response(
            200,
            json={"data": [{"id": "llama-3.3-70b-versatile"}, {"id": "llama-3.1-8b"}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    available = asyncio.run(groq_provider.check_availability(client))
    assert available is True

    # When model is not in list
    monkeypatch.setenv("GROQ_MODEL", "non-existent-model")
    available_false = asyncio.run(groq_provider.check_availability(client))
    assert available_false is False


def test_gemini_model_discovery(monkeypatch):
    """Verify GeminiProvider check_availability against GET /models endpoint."""
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.valid")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models"
        assert request.headers.get("x-goog-api-key") == "AQ.valid"
        return httpx.Response(
            200,
            json={"models": [{"name": "models/gemini-1.5-flash"}, {"name": "models/gemini-1.5-pro"}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    available = asyncio.run(gemini_provider.check_availability(client))
    assert available is True

    # When model is not in list
    monkeypatch.setenv("GEMINI_MODEL", "gemini-unknown")
    available_false = asyncio.run(gemini_provider.check_availability(client))
    assert available_false is False


# ============================================================================
# 3. Provider Generation, Retries, and Rate-Limit Handling
# ============================================================================

def test_groq_json_object_chat_and_retries(monkeypatch):
    """Verify GroqProvider enforces json_object format, temperature 0.1, and retries on 429."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "llama-3.3-70b-versatile"}]})
        if request.url.path.endswith("/chat/completions"):
            attempts["count"] += 1
            body = json.loads(request.content)
            assert body["model"] == "llama-3.3-70b-versatile"
            assert body["temperature"] == 0.1
            assert body["response_format"] == {"type": "json_object"}
            # Simulate 429 on first attempt, then success
            if attempts["count"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0.1"}, json={"error": "Rate limit"})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps(VALID_AI_OUTPUT)}}]},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    raw = asyncio.run(groq_provider.generate("Explain heat", {"drivers": {}}, client=client))
    parsed = json.loads(raw)
    assert parsed["summary"] == VALID_AI_OUTPUT["summary"]
    assert attempts["count"] == 2


def test_gemini_generate_content_and_retries(monkeypatch):
    """Verify GeminiProvider enforces responseMimeType and retries on 503."""
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"models": [{"name": "models/gemini-1.5-flash"}]})
        if ":generateContent" in request.url.path:
            attempts["count"] += 1
            body = json.loads(request.content)
            gen_config = body.get("generationConfig", {})
            assert gen_config.get("temperature") == 0.1
            assert gen_config.get("responseMimeType") == "application/json"
            if attempts["count"] == 1:
                return httpx.Response(503, json={"error": "Service Unavailable"})
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_AI_OUTPUT)}]}}]},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    raw = asyncio.run(gemini_provider.generate("Suggest actions", {"drivers": {}}, client=client))
    parsed = json.loads(raw)
    assert parsed["summary"] == VALID_AI_OUTPUT["summary"]
    assert attempts["count"] == 2


def test_credential_sanitization_on_error(monkeypatch):
    """Verify error messages mask API keys and bearer tokens."""
    secret = "gsk_topsecrettoken987654321"
    err = RuntimeError(f"Connection failed for {secret}")
    sanitized = sanitize_error(err)
    assert secret not in sanitized
    assert "[REDACTED]" in sanitized

    oauth_token = "ya29.secret_oauth_bearer_12345"
    sanitized_oauth = sanitize_error(f"Expired token: {oauth_token}")
    assert oauth_token not in sanitized_oauth
    assert "[REDACTED]" in sanitized_oauth


# ============================================================================
# 4. Strict Grounding & Numeric Guardrails Tests
# ============================================================================

def test_numeric_guardrails_pass_on_supported_facts():
    """Grounded prose with numbers matching provided facts passes validation."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL, SAMPLE_OPTIMIZATION, SAMPLE_SCENARIOS)
    
    # 3.75 (suhii), 41.5 (lst), 1.45 (shap) are in facts
    valid_text = (
        "The model predicts 3.75 °C SUHII and surface temperature of 41.5 °C. "
        "Building density contributes 1.45 to the model prediction."
    )
    # Should not raise
    validate_numeric_guardrails(valid_text, facts)


def test_numeric_guardrails_whitelisted_entities_do_not_trigger():
    """Domain terms with numbers (Sentinel-2, Landsat-8, 100m, EPSG:4326, 2024) do not trigger audit."""
    facts = {"drivers": {}}
    text = (
        "Derived from Sentinel-2 L2A and Landsat-8 thermal bands at 100m resolution. "
        "Processed in EPSG:4326 for year 2024 baseline. 1. First step. 2. Second step."
    )
    # Should not raise even though 2, 8, 100, 4326, 2024 are in prose
    validate_numeric_guardrails(text, facts)


def test_numeric_guardrails_detects_hallucinated_temperature():
    """Prose inventing ungrounded numbers triggers ValueError."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)
    hallucinated_text = "The surface heat will decrease by exactly 92.4 °C after greening."
    with pytest.raises(ValueError, match="unsupported numeric prose"):
        validate_numeric_guardrails(hallucinated_text, facts)


def test_citation_guardrail_rejects_invented_fact_ids():
    """Findings citing non-existent keys in facts dictionary raise ValueError."""
    facts = {"drivers": {}, "prediction": {}}
    findings = [
        AIFinding(statement="Valid finding", fact_ids=["drivers"]),
        AIFinding(statement="Invented finding", fact_ids=["hallucinated_source"]),
    ]
    with pytest.raises(ValueError, match="unsupported evidence"):
        validate_citations(findings, facts)


def test_action_feasibility_guardrail_with_simulate(monkeypatch):
    """Actions deemed infeasible by simulate() raise ValueError."""
    # When tree planting is feasible
    validate_action_feasibility(["trees"], SAMPLE_ZONE)

    # If simulate marks cool_roofs infeasible, guardrail must reject it
    monkeypatch.setattr(
        ai,
        "simulate",
        lambda p, cov, **kw: {"feasible": False, "violations": ["No roof area"]},
    )
    with pytest.raises(ValueError, match="infeasible intervention"):
        validate_action_feasibility(["cool_roofs"], SAMPLE_ZONE)


# ============================================================================
# 5. Decision-Support Capabilities (7 Resilience Questions)
# ============================================================================

def test_prompt_covers_seven_decision_questions():
    """Verify build_prompt instructs the LLM on all seven decision support requirements."""
    prompt = build_prompt("Why is this zone hot?", {"drivers": {}})
    assert "urban heat resilience decision-support" in prompt
    assert "TreeSHAP" in prompt
    assert "IPCC Hazard, Exposure, Vulnerability" in prompt
    assert "constraints" in prompt
    assert "Do not put any numbers or statistics in prose" in prompt


def test_deterministic_placeholder_answers_seven_decision_questions():
    """Verify deterministic fallback provides grounded answers to key urban heat resilience questions."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL, SAMPLE_OPTIMIZATION, SAMPLE_SCENARIOS)
    res = deterministic_placeholder(SAMPLE_ZONE, facts)

    # 1. Why zone experiences heat & 2. TreeSHAP environmental factors
    assert "Central Ward" in res["summary"]
    assert "high priority" in res["summary"].lower()
    assert "building density" in res["summary"]

    # 3. Prioritized findings citing real fact keys
    assert len(res["findings"]) >= 2
    for f in res["findings"]:
        assert all(k in facts for k in f["fact_ids"])

    # 4. Suitable feasible interventions
    assert isinstance(res["actions"], list)
    assert len(res["actions"]) > 0

    # 7. Limitations of recommendations
    assert any("Synthetic-fallback" in lim for lim in res["limitations"])
    assert any("air temperature" in lim.lower() for lim in res["limitations"])

    # Metadata
    assert res["provider"] == "local evidence summary"
    assert res["fallback"] is True
    assert res["synthetic_fallback"] is True


# ============================================================================
# 6. End-to-End Orchestration & Fallback Chain
# ============================================================================

def test_orchestrate_chat_auto_fallback_chain(monkeypatch):
    """Verify requested provider -> alternative provider -> local deterministic summary fallback."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Scenario A: Groq fails with 500, Gemini succeeds
    def fail_groq_handler(request: httpx.Request) -> httpx.Response:
        if "groq.com" in request.url.host:
            return httpx.Response(500, json={"error": "Groq down"})
        if "generativelanguage.googleapis.com" in request.url.host:
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"models": [{"name": "models/gemini-1.5-flash"}]})
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_AI_OUTPUT)}]}}]},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail_groq_handler))
    res = asyncio.run(
        orchestrate_chat(
            message="Why is this zone hot?",
            provider="auto",
            p=SAMPLE_ZONE,
            model=SAMPLE_MODEL,
            client=client,
        )
    )
    assert res["provider"] == "gemini"
    assert res["fallback"] is False
    assert len(res["failures"]) == 1
    assert res["failures"][0]["provider"] == "groq"

    # Scenario B: Both Groq and Gemini fail -> local deterministic summary
    def all_fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "All down"})

    client_all_fail = httpx.AsyncClient(transport=httpx.MockTransport(all_fail_handler))
    res_fallback = asyncio.run(
        orchestrate_chat(
            message="Why is this zone hot?",
            provider="auto",
            p=SAMPLE_ZONE,
            model=SAMPLE_MODEL,
            client=client_all_fail,
        )
    )
    assert res_fallback["provider"] == "local evidence summary"
    assert res_fallback["fallback"] is True
    assert res_fallback["synthetic_fallback"] is True
    assert len(res_fallback["failures"]) == 2


def test_api_chat_route_local_mode():
    """Verify /api/ai/chat endpoint works seamlessly with provider='local'."""
    with TestClient(app) as client:
        response = client.post(
            "/api/ai/chat",
            json={
                "city": "Ahmedabad",
                "message": "Explain urban heat resilience priority",
                "provider": "local",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "local evidence summary"
        assert data["fallback"] is True
        assert len(data["findings"]) >= 2
        assert len(data["limitations"]) >= 2
