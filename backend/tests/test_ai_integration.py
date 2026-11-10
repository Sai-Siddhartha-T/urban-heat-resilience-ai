"""Unit and integration tests for LLM providers (Groq, Gemini) and /api/ai/chat endpoint."""

import asyncio
import json
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_groq import GroqProvider, groq_provider
from app.services.ai_gemini import GeminiProvider, gemini_provider
from app.services import ai


VALID_FACTS = {
    "prediction": {
        "suhii_c": 3.45,
        "lst_c": 38.2,
        "interval": [2.9, 4.0],
        "synthetic": True,
    },
    "drivers": {
        "vegetation_fraction": -0.85,
        "surface_albedo": -0.62,
        "building_density": 1.15,
    },
    "risk": {
        "risk_score": 0.72,
        "hazard": 0.81,
        "exposure": 0.65,
        "vulnerability": 0.70,
    },
    "constraints": {
        "available_land_pct": 25.0,
        "roof_pct": 35.0,
        "road_pct": 20.0,
        "protected": False,
    },
    "model": {
        "winner": "lightgbm",
        "evaluation": {"r2": 0.88},
        "synthetic": True,
    },
    "optimization": {"available": False},
    "scenarios": [],
}

VALID_LLM_OUTPUT = {
    "summary": "Building density is strongly associated with elevated surface heat in this zone.",
    "findings": [
        {
            "statement": "High building density and low vegetation fraction explain elevated surface temperatures.",
            "fact_ids": ["drivers", "prediction"],
        },
        {
            "statement": "Available roof and land space offer opportunities for surface treatments.",
            "fact_ids": ["constraints"],
        },
    ],
    "actions": ["cool_roofs", "trees"],
    "limitations": [
        "Synthetic surface heat predictions do not measure direct air temperature.",
        "Ground measurements are required to validate real-world cooling impact.",
    ],
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_groq_provider_direct_generate(monkeypatch):
    """Test GroqProvider directly with mocked HTTP transport."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_12345")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    recorded_headers = {}

    def groq_handler(request: httpx.Request) -> httpx.Response:
        recorded_headers.update(dict(request.headers))
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [{"id": "llama-3.3-70b-versatile"}]},
            )
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": json.dumps(VALID_LLM_OUTPUT)}}
                    ]
                },
            )
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(groq_handler))
    provider = GroqProvider()
    assert provider.is_configured()

    raw = asyncio.run(
        provider.generate("Explain heat", VALID_FACTS, client=mock_client)
    )
    parsed = json.loads(raw)
    assert parsed["summary"] == VALID_LLM_OUTPUT["summary"]
    assert recorded_headers.get("authorization") == "Bearer gsk_test_key_12345"


def test_gemini_provider_direct_generate(monkeypatch):
    """Test GeminiProvider directly with mocked HTTP transport."""
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test_gemini_key_67890")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    recorded_headers = {}

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        recorded_headers.update(dict(request.headers))
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"models": [{"name": "models/gemini-1.5-flash"}]},
            )
        if ":generateContent" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": json.dumps(VALID_LLM_OUTPUT)}]
                            }
                        }
                    ]
                },
            )
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(gemini_handler))
    provider = GeminiProvider()
    assert provider.is_configured()

    raw = asyncio.run(
        provider.generate("Explain heat", VALID_FACTS, client=mock_client)
    )
    parsed = json.loads(raw)
    assert parsed["summary"] == VALID_LLM_OUTPUT["summary"]
    assert recorded_headers.get("x-goog-api-key") == "AQ.test_gemini_key_67890"


def test_gemini_provider_agy_account_auth(monkeypatch):
    """Test GeminiProvider authentication with AGY_ACCOUNT (Bearer token and API key fallback)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Case A: Bearer token (ya29...)
    monkeypatch.setenv("AGY_ACCOUNT", "ya29.mock_oauth_access_token_123")
    prov = GeminiProvider()
    headers = prov.get_auth_headers()
    assert headers == {"Authorization": "Bearer ya29.mock_oauth_access_token_123"}
    assert prov.is_configured()

    # Case B: Key string token
    monkeypatch.setenv("AGY_ACCOUNT", "AQ.mock_token_account_456")
    headers = prov.get_auth_headers()
    assert headers == {"x-goog-api-key": "AQ.mock_token_account_456"}
    assert prov.is_configured()


def test_chat_endpoint_groq_success(client, monkeypatch):
    """Test /api/ai/chat endpoint with provider='groq' returning successful response."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def groq_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [{"id": "llama-3.3-70b-versatile"}]},
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(VALID_LLM_OUTPUT)}}]},
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(groq_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Why is this area hot?", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq"
    assert data["fallback"] is False
    assert data["synthetic_fallback"] is False
    assert data["label"] is None
    assert len(data["findings"]) == 2
    assert "cool_roofs" in data["actions"]


def test_chat_endpoint_gemini_success(client, monkeypatch):
    """Test /api/ai/chat endpoint with provider='gemini' returning successful response."""
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.valid_key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"models": [{"name": "models/gemini-1.5-flash"}]},
            )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(VALID_LLM_OUTPUT)}]}}
                ]
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(gemini_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Suggest interventions", "provider": "gemini"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "gemini"
    assert data["fallback"] is False
    assert data["synthetic_fallback"] is False
    assert len(data["limitations"]) == 2


def test_chat_endpoint_auto_failover_to_gemini(client, monkeypatch):
    """Test provider='auto' fails over to Gemini when Groq fails with 500 error."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_groq_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.gemini_key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def failover_handler(request: httpx.Request) -> httpx.Response:
        # Groq endpoints fail
        if "groq.com" in request.url.host:
            return httpx.Response(500, json={"error": "Groq internal server error"})
        # Gemini endpoints succeed
        if "generativelanguage.googleapis.com" in request.url.host:
            if request.url.path.endswith("/models"):
                return httpx.Response(
                    200,
                    json={"models": [{"name": "models/gemini-1.5-flash"}]},
                )
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": json.dumps(VALID_LLM_OUTPUT)}]
                            }
                        }
                    ]
                },
            )
        return httpx.Response(404)

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(failover_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain heat with auto", "provider": "auto"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "gemini"
    assert data["fallback"] is False
    assert len(data["failures"]) == 1
    assert data["failures"][0]["provider"] == "groq"


def test_chat_endpoint_auto_all_fail_to_deterministic_placeholder(client, monkeypatch):
    """Test provider='auto' falls back to deterministic placeholder when all providers fail."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "Service unavailable"})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(error_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain evidence", "provider": "auto"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True
    assert data["label"] == "synthetic-fallback"
    assert data["provider"] == "local evidence summary"
    assert len(data["failures"]) == 2
    assert "Synthetic-fallback" in data["limitations"][0]


def test_chat_endpoint_groq_only_fails_to_placeholder(client, monkeypatch):
    """When user selects provider='groq' and it fails, it must fall back to placeholder without trying Gemini."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    def groq_fail_handler(request: httpx.Request) -> httpx.Response:
        if "groq.com" in request.url.host:
            return httpx.Response(500, json={"error": "Internal error"})
        # If Gemini is called, return 200 - but it should NOT be called!
        return httpx.Response(200)

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(groq_fail_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain evidence", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True
    assert len(data["failures"]) == 1
    assert data["failures"][0]["provider"] == "groq"


def test_chat_endpoint_local_mode(client):
    """Test provider='local' immediately returns deterministic placeholder without HTTP calls."""
    response = client.post(
        "/api/ai/chat",
        json={"message": "Analyze local evidence", "provider": "local"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True
    assert data["provider"] == "local evidence summary"
    assert len(data["failures"]) == 0
    assert len(data["actions"]) > 0


def test_chat_schema_validation_failure_triggers_fallback(client, monkeypatch):
    """Test that malformed JSON or schema violation from provider triggers deterministic fallback."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Missing required 'summary' and 'findings'
    invalid_schema_output = {"random_key": "not matching schema"}

    def invalid_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200, json={"data": [{"id": "llama-3.3-70b-versatile"}]}
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(invalid_schema_output)}}
                ]
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(invalid_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True
    assert len(data["failures"]) == 1


def test_chat_hallucinated_number_triggers_fallback(client, monkeypatch):
    """Test that hallucinated numbers in prose trigger numeric guardrails and fall back."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    hallucinated_output = dict(VALID_LLM_OUTPUT)
    hallucinated_output["summary"] = (
        "Surface temperature will drop by exactly 49.7 degrees celsius tomorrow."
    )

    def hallucination_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200, json={"data": [{"id": "llama-3.3-70b-versatile"}]}
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(hallucinated_output)}}
                ]
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(hallucination_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True


def test_chat_unsupported_citation_triggers_fallback(client, monkeypatch):
    """Test that citing non-existent fact_ids triggers citation validation and falls back."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    invalid_citation_output = dict(VALID_LLM_OUTPUT)
    invalid_citation_output["findings"] = [
        {
            "statement": "Evidence comes from an unprovided dataset.",
            "fact_ids": ["non_existent_fact_id"],
        }
    ]

    def citation_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200, json={"data": [{"id": "llama-3.3-70b-versatile"}]}
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(invalid_citation_output)}}
                ]
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(citation_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True


def test_chat_infeasible_action_triggers_fallback(client, monkeypatch):
    """Test that suggesting an intervention infeasible for zone constraints triggers fallback."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    infeasible_output = dict(VALID_LLM_OUTPUT)
    infeasible_output["actions"] = ["cool_roofs"]

    def infeasible_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200, json={"data": [{"id": "llama-3.3-70b-versatile"}]}
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(infeasible_output)}}
                ]
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(infeasible_handler), **kw
        ),
    )

    # Force simulation check to report infeasible
    monkeypatch.setattr(
        ai,
        "simulate",
        lambda p, cov, **kw: {"feasible": False, "violations": ["Infeasible constraint"]},
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Suggest action", "provider": "groq"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["synthetic_fallback"] is True
    assert len(data["failures"]) == 1


def test_no_credentials_leaked_in_failures(client, monkeypatch):
    """Verify that sensitive API keys are never exposed in failure messages."""
    secret_key = "gsk_super_secret_key_9999"
    monkeypatch.setenv("GROQ_API_KEY", secret_key)
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def leak_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"Unauthorized access with {secret_key}")

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_async_client(
            transport=httpx.MockTransport(leak_handler), **kw
        ),
    )

    response = client.post(
        "/api/ai/chat",
        json={"message": "Explain", "provider": "groq"},
    )
    assert response.status_code == 200
    body_text = response.text
    assert secret_key not in body_text


def test_provider_status_reporting(monkeypatch):
    """Test provider_status helper reflects configuration accurately."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("AGY_ACCOUNT", raising=False)

    status = ai.provider_status()
    assert status["groq"]["configured"] is True
    assert status["groq"]["model"] == "llama-3.3-70b-versatile"
    assert status["gemini"]["configured"] is False
