# AI Assistant & LLM Provider Integration

This document outlines the architecture, configuration, credential handling, and response schema for the AI Resilience Assistant in the Urban Heat Resilience platform.

---

## 1. Architecture Overview

The AI Assistant provides evidence-grounded generative reasoning about urban surface heat, feature importance (SHAP contributions), and intervention feasibility. The integration is modularized into discrete provider modules with an abstraction layer, strict grounding guardrails, and deterministic synthetic fallback.

### Modules

- **`backend/app/services/ai_base.py`**  
  Defines the abstract base class `BaseLLMProvider`, shared prompt construction logic, JSON fence stripping, and credential sanitization routines.
- **`backend/app/services/ai_groq.py`**  
  Implements `GroqProvider` wrapping the Groq Cloud OpenAI-compatible Chat Completions API with model list validation.
- **`backend/app/services/ai_gemini.py`**  
  Implements `GeminiProvider` wrapping Google Generative Language API (`v1beta`) with multi-mode credential resolution and model verification.
- **`backend/app/services/ai.py`**  
  Orchestrates provider execution, enforces numeric measurement guardrails and evidence citation audits, checks intervention feasibility, and serves the deterministic placeholder when upstream calls fail.
- **`backend/app/routes/ai.py`**  
  FastAPI route exposing `POST /api/ai/chat`, binding request validation and conversation persistence.

---

## 2. Provider Selection

The `/api/ai/chat` endpoint accepts a `provider` parameter with four supported modes:

| Provider Mode | Behavior | Failover Ladder |
| :--- | :--- | :--- |
| **`auto`** *(default)* | Automatic provider selection with sequential failover. | Attempts **Groq** $\to$ fails over to **Gemini** $\to$ falls back to **Deterministic Placeholder**. |
| **`groq`** | Targets Groq Cloud inference explicitly. | Attempts **Groq** $\to$ falls back directly to **Deterministic Placeholder** (does not silently call Gemini). |
| **`gemini`** | Targets Google Gemini inference explicitly. | Attempts **Gemini** $\to$ falls back directly to **Deterministic Placeholder** (does not silently call Groq). |
| **`local`** | Immediate deterministic template mode. | Directly returns the **Deterministic Placeholder** without issuing any external network calls. |

---

## 3. Credentials & Authentication

Credentials must be configured exclusively through environment variables. Secrets are never hardcoded, checked into version control, or exposed in API error diagnostics.

### Environment Variables

| Variable | Description | Example / Format |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq Cloud API authentication key. | `gsk_...` |
| `GROQ_MODEL` | Groq model identifier. | `llama-3.3-70b-versatile` |
| `GEMINI_API_KEY` | Google Gemini API key. | `AIza...` or `AQ....` |
| `GEMINI_MODEL` | Gemini model identifier. | `gemini-1.5-flash` |
| `GOOGLE_API_KEY` | Standard fallback API key for Gemini. | `AIza...` |
| `AGY_ACCOUNT` | Fallback Google / Antigravity account token or ADC credential. | `ya29...` (Bearer token) or account key |

### Authentication Handling in `ai_gemini.py`
The Gemini provider evaluates credentials in priority order:
1. Direct API key from `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
   - If the key begins with `ya29.`, it is passed via `Authorization: Bearer <token>`.
   - Otherwise, it is transmitted via header `x-goog-api-key: <key>`.
2. `AGY_ACCOUNT`:
   - If structured as an OAuth token (`ya29...`), it is passed via `Authorization: Bearer <token>`.
   - If provided as an API key token, it is sent via `x-goog-api-key`.
   - If set to an account identity, it attempts Google Application Default Credentials (ADC) resolution via `google.auth`.

---

## 4. Grounding Guardrails & Safety Checks

All LLM output must satisfy strict validation before being accepted:

1. **Structured Schema Validation**:  
   The response must parse as valid JSON conforming strictly to `AIResponse` (`summary`, `findings`, `actions`, `limitations`).
2. **Citation Verification**:  
   Every entry in `findings[].fact_ids` must refer exclusively to keys present in the supplied `facts` dictionary (`prediction`, `drivers`, `risk`, `constraints`, `model`, `optimization`, `scenarios`).
3. **Numeric Guardrails (`validate_numeric_guardrails`)**:  
   The prose in `summary` and `findings` is audited against regular expressions for physical measurements, percentages, ranges, and signed numbers. Any numeric value not present in the factual context (within 5% relative or 0.15 absolute tolerance) triggers immediate rejection.
4. **Physical Feasibility Check**:  
   Any suggested intervention action in `actions` is tested via `simulate(zone, {action: 5})`. If the zone's available land, roof, or road area cannot support the intervention, the response is rejected and falls back.

---

## 5. Deterministic Placeholder & Synthetic Fallback

If upstream providers are unconfigured, encounter network errors, or produce outputs that violate schema or guardrails, the service gracefully returns a deterministic placeholder:

- **`fallback`**: Set to `true`.
- **`synthetic_fallback`**: Set to `true`.
- **`label`**: Set to `"synthetic-fallback"`.
- **`provider`**: Labeled `"local evidence summary"`.
- **`failures`**: Contains a list of failed provider attempts and safe error reasons (e.g. `"Not configured"` or `"Provider unavailable or output failed validation"`).
- **`limitations`**: Includes the explicit notice: `"Synthetic-fallback: deterministic evidence summary template, not an LLM response."`

---

## 6. Response Format

### Schema Definition (`ChatResponse`)

```json
{
  "summary": "Building density is strongly associated with elevated surface heat in this zone.",
  "findings": [
    {
      "statement": "High building density and low vegetation fraction explain elevated surface temperatures.",
      "fact_ids": ["drivers", "prediction"]
    },
    {
      "statement": "Available roof and land space offer opportunities for surface treatments.",
      "fact_ids": ["constraints"]
    }
  ],
  "actions": ["cool_roofs", "trees"],
  "limitations": [
    "Synthetic surface heat predictions do not measure direct air temperature.",
    "Ground measurements are required to validate real-world cooling impact."
  ],
  "provider": "groq",
  "fallback": false,
  "synthetic_fallback": false,
  "label": null,
  "facts": {
    "prediction": { "suhii_c": 3.45, "lst_c": 38.2, "synthetic": true },
    "drivers": { "building_density": 1.15, "vegetation_fraction": -0.85 },
    "constraints": { "available_land_pct": 25.0, "roof_pct": 35.0, "road_pct": 20.0, "protected": false }
  },
  "failures": []
}
```

---

## 7. Unit & Integration Testing

Tests verify provider interactions and fallback behavior using mocked HTTP transports without issuing real LLM network calls.

Run all AI tests:
```powershell
pytest backend/tests/test_ai.py backend/tests/test_ai_integration.py
```

### Coverage in `test_ai_integration.py`:
- Direct `GroqProvider` generation with mock transport and authorization header validation.
- Direct `GeminiProvider` generation with mock transport and `x-goog-api-key` validation.
- Gemini authentication via `AGY_ACCOUNT` (Bearer token and API key fallback).
- `/api/ai/chat` endpoint testing across `groq`, `gemini`, `auto`, and `local` modes.
- Sequential failover from Groq to Gemini under `auto` mode upon 500 error.
- Full failover to deterministic placeholder when all providers fail.
- Immediate deterministic fallback for single-provider selection failure (`groq`).
- Immediate deterministic response under `local` mode.
- Fallback triggered by malformed JSON and schema mismatches.
- Fallback triggered by hallucinated numbers (numeric guardrails).
- Fallback triggered by unsupported citation keys.
- Fallback triggered by physically infeasible intervention suggestions.
- Credential safety verification ensuring no secret keys are exposed in responses or failures.
- Accurate provider configuration reporting in `provider_status()`.
