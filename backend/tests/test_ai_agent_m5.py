"""Acceptance criteria and integration verification for Milestone M5: Grounded Multi-Provider AI Climate Assistant."""

import json
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.migrations import run_migrations
from app.schemas.ai import ChatRequest, ChatResponse
from app.services import ai
from app.services.llm import (
    SETUP_GUIDANCE,
    context_for,
    deterministic_placeholder,
    orchestrate_chat,
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
    "weather": {"temperature_c": 38.5, "humidity_pct": 45.0},
    "air_quality": {"pm2_5": 78.4, "pm10": 142.0},
    "groundwater": {"depth_m": 24.5, "trend": "falling"},
}

SAMPLE_MODEL = {
    "winner": "lightgbm",
    "evaluations": {"r2": 0.91, "rmse": 0.42},
    "synthetic": True,
}

VALID_LLM_OUTPUT = {
    "summary": "Building density is strongly associated with elevated surface heat in this ward.",
    "findings": [
        {
            "statement": "TreeSHAP attributions indicate building density is the primary factor increasing surface heat.",
            "fact_ids": ["drivers", "prediction"],
        },
        {
            "statement": "Roof space provides opportunity for cool roof deployment.",
            "fact_ids": ["constraints"],
        },
    ],
    "actions": ["cool_roofs"],
    "limitations": [
        "Synthetic surface heat predictions do not measure direct air temperature.",
        "Scenario effects are hypothetical and require ground calibration.",
    ],
}


@pytest.mark.asyncio
async def test_m5_provider_downtime_structured_error_no_hallucination(monkeypatch):
    """
    CRITICAL R7 Requirement:
    When configured external providers fail or credentials are missing,
    DO NOT return synthetic hallucinated prose.
    Return structured user-facing error indicators explaining provider downtime,
    accompanied by clear setup documentation (GROQ_API_KEY / GEMINI_API_KEY).
    """
    # Simulate both providers unconfigured / failing
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await orchestrate_chat(
        message="Explain heat causes in this ward",
        provider="auto",
        p=SAMPLE_ZONE,
        model=SAMPLE_MODEL,
    )

    # Must be structured downtime error
    assert result["status"] == "error"
    assert result["fallback"] is True
    assert result["synthetic_fallback"] is True
    assert result["error_message"] is not None
    assert "External AI provider downtime" in result["error_message"]
    assert "groq" in result["error_message"]
    assert "gemini" in result["error_message"]

    # Must include clear setup documentation for GROQ_API_KEY and GEMINI_API_KEY
    assert result["setup_guidance"] is not None
    assert "GROQ_API_KEY" in result["setup_guidance"]
    assert "GEMINI_API_KEY" in result["setup_guidance"]
    assert "https://console.groq.com" in result["setup_guidance"]
    assert "https://aistudio.google.com" in result["setup_guidance"]

    # Must contain failures audit
    assert len(result["failures"]) == 2


def test_m5_summary_delineates_downtime_from_analytical_evidence():
    """Verify that summary explicitly delineates provider downtime and setup guide from analytical evidence."""
    facts = context_for(SAMPLE_ZONE, SAMPLE_MODEL)
    failures = [{"provider": "groq", "reason": "Not configured"}]

    resp = deterministic_placeholder(SAMPLE_ZONE, facts, failures=failures, is_error=True)

    summary = resp["summary"]
    assert "[AI PROVIDER DOWNTIME]" in summary
    assert "[DETERMINISTIC ANALYTICAL EVIDENCE SUMMARY]" in summary
    assert "GROQ_API_KEY" in summary
    assert "GEMINI_API_KEY" in summary
    assert resp["status"] == "error"


@pytest.mark.asyncio
async def test_m5_local_mode_offline_analytical_summary():
    """Verify provider='local' produces offline deterministic evidence analysis with status='ok'."""
    result = await orchestrate_chat(
        message="Show local analysis",
        provider="local",
        p=SAMPLE_ZONE,
        model=SAMPLE_MODEL,
    )

    assert result["status"] == "ok"
    assert result["provider"] == "local evidence summary"
    assert result["fallback"] is True
    assert result["synthetic_fallback"] is True
    assert "[OFFLINE DETERMINISTIC ANALYSIS]" in result["summary"]
    assert result["error_message"] is None
    assert len(result["failures"]) == 0
    assert len(result["citations"]) >= 2


@pytest.mark.asyncio
async def test_m5_multi_provider_failover_groq_to_gemini(monkeypatch):
    """Verify seamless failover from Groq to Gemini on transient error in auto mode."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_groq_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.gemini_key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def failover_transport(request: httpx.Request) -> httpx.Response:
        # Groq endpoints fail with 503
        if "groq.com" in request.url.host:
            return httpx.Response(503, json={"error": "Groq capacity exceeded"})
        # Gemini endpoints succeed
        if "generativelanguage.googleapis.com" in request.url.host:
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"models": [{"name": "models/gemini-1.5-flash"}]})
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_LLM_OUTPUT)}]}}]},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(failover_transport))

    result = await orchestrate_chat(
        message="Suggest mitigation interventions",
        provider="auto",
        p=SAMPLE_ZONE,
        model=SAMPLE_MODEL,
        client=client,
    )

    assert result["provider"] == "gemini"
    assert result["status"] == "ok"
    assert result["fallback"] is False
    assert result["synthetic_fallback"] is False
    assert result["error_message"] is None
    assert len(result["failures"]) == 1
    assert result["failures"][0]["provider"] == "groq"
    assert "citations" in result
    assert "drivers" in result["citations"]


def test_m5_chat_endpoint_contract_compliance(monkeypatch):
    """Verify /api/ai/chat endpoint satisfies complete contract with typed fields."""
    with TestClient(app) as client:
        # 1. Local mode request
        res = client.post(
            "/api/ai/chat",
            json={
                "city": "Ahmedabad",
                "message": "Explain urban heat resilience priority",
                "provider": "local",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "local evidence summary"
        assert data["status"] in ("ok", "degraded")
        assert "response" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert len(data["findings"]) >= 1

        # 2. Unconfigured provider request (downtime reporting)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        res_downtime = client.post(
            "/api/ai/chat",
            json={
                "city": "Ahmedabad",
                "message": "Explain heat causes",
                "provider": "groq",
            },
        )
        assert res_downtime.status_code == 200
        data_down = res_downtime.json()
        assert data_down["status"] == "error"
        assert data_down["fallback"] is True
        assert data_down["error_message"] is not None
        assert "GROQ_API_KEY" in data_down["setup_guidance"]
        assert "GEMINI_API_KEY" in data_down["setup_guidance"]
