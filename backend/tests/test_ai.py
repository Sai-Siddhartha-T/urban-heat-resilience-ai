import asyncio, json
import httpx
import pytest
from app.services.ai import call_provider
from app.main import state, zone
from app.services.ai import context_for


def test_provider_schema_and_model_validation(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    real = httpx.AsyncClient
    output = {
        "summary": "The evidence indicates higher surface heat.",
        "findings": [
            {
                "statement": "Building density is associated with the model result.",
                "fact_ids": ["drivers"],
            }
        ],
        "actions": ["cool_roofs"],
        "limitations": ["Synthetic evidence."],
    }

    def handler(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "test-model"}],
                    "models": [{"name": "models/test-model"}],
                },
            )
        if "generateContent" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": json.dumps(output)}]}}
                    ]
                },
            )
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(output)}}]}
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    for provider in ["groq", "gemini"]:
        r = asyncio.run(call_provider(provider, "Explain", {"drivers": {}}))
        assert r["findings"][0]["fact_ids"] == ["drivers"]
    output["findings"][0]["fact_ids"] = ["invented"]
    with pytest.raises(ValueError):
        asyncio.run(call_provider("groq", "Explain", {"drivers": {}}))
    output["findings"][0]["fact_ids"] = ["drivers"]
    output["summary"] = "Cooling is 99 degrees"
    with pytest.raises(ValueError):
        asyncio.run(call_provider("groq", "Explain", {"drivers": {}}))
