"""Deterministic evidence summary fallback and multi-provider failover orchestrator."""

import logging
from typing import Any
import httpx

from app.db import records, save
from app.schemas.ai import AIResponse
from app.services.llm.guardrails import (
    validate_action_feasibility,
    validate_citations,
    validate_numeric_guardrails,
)
from app.services.llm.gemini import gemini_provider
from app.services.llm.groq import groq_provider
from app.services.llm.provider import BaseLLMProvider, sanitize_error

log = logging.getLogger("heatwise.llm.fallback")

SETUP_GUIDANCE = (
    "AI Provider Setup Documentation:\n"
    "1. Groq: Set GROQ_API_KEY in backend/.env (obtain API key from https://console.groq.com). "
    "Optionally set GROQ_MODEL (default: llama-3.3-70b-versatile).\n"
    "2. Google Gemini: Set GEMINI_API_KEY in backend/.env (obtain API key from https://aistudio.google.com). "
    "Optionally set GEMINI_MODEL (default: gemini-1.5-flash).\n"
    "After updating credentials in backend/.env, restart the FastAPI server."
)

PROVIDERS: dict[str, BaseLLMProvider] = {
    "groq": groq_provider,
    "gemini": gemini_provider,
}


def get_provider(name: str) -> BaseLLMProvider | None:
    return PROVIDERS.get(name)


def provider_status() -> dict[str, dict[str, Any]]:
    try:
        history = records("provider_connection", 100)
    except Exception:
        history = []
    result = {}
    for p_name, provider in PROVIDERS.items():
        events = [event for event in history if event.get("provider") == p_name]
        latest = events[0] if events else None
        latest_success = next((event for event in events if event.get("success")), None)
        result[p_name] = {
            "configured": provider.is_configured(),
            "model": provider.get_model(),
            "latest_request_success": latest.get("success") if latest else None,
            "last_attempt_at": latest.get("attempted_at") if latest else None,
            "last_success_at": latest_success.get("attempted_at") if latest_success else None,
            "availability": (
                "verified" if latest and latest.get("success") else
                "failed" if latest else "not_verified"
            ),
        }
    return result


def record_provider_event(provider: str, success: bool, reason: str | None = None) -> None:
    """Persist an auditable connection result without retaining credentials."""
    from datetime import datetime, timezone

    try:
        save(
            "provider_connection",
            {
                "provider": provider,
                "success": success,
                "reason": reason,
                "attempted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        # DB tables may not be migrated in isolated test contexts; never let persistence break LLM response
        pass


def context_for(
    p: dict[str, Any],
    model: dict[str, Any],
    optimization: dict[str, Any] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct canonical facts dictionary grounded on real ML, XAI, risk, and simulation outputs."""
    p = p or {}
    model = model or {}

    # Extract weather facts if present
    weather_data = p.get("weather") or {}
    if not weather_data:
        weather_keys = ["temperature_c", "air_temp_c", "humidity_pct", "wind_speed_ms", "condition"]
        weather_data = {k: p[k] for k in weather_keys if k in p}
    if not weather_data:
        weather_data = {"available": False}

    # Extract air quality facts if present
    aq_data = p.get("air_quality") or {}
    if not aq_data:
        aq_keys = ["pm2_5", "pm10", "no2", "so2", "o3", "aqi"]
        aq_data = {k: p[k] for k in aq_keys if k in p}
    if not aq_data:
        aq_data = {"available": False}

    # Extract groundwater facts if present
    gw_data = p.get("groundwater") or {}
    if not gw_data:
        gw_keys = ["depth_m", "water_table_mbgl", "trend"]
        gw_data = {k: p[k] for k in gw_keys if k in p}
    if not gw_data:
        gw_data = {"available": False}

    facts = {
        "prediction": {
            "suhii_c": p.get("predicted_suhii", p.get("suhii", 0.0)),
            "lst_c": p.get("predicted_lst", p.get("lst", 0.0)),
            "interval": [p.get("interval_low", 0.0), p.get("interval_high", 0.0)],
            "synthetic": True,
        },
        "drivers": p.get("shap", {}),
        "risk": {
            k: p.get(k, 0.0) for k in ["risk_score", "hazard", "exposure", "vulnerability"]
        },
        "constraints": {
            k: p.get(k) for k in ["available_land_pct", "roof_pct", "road_pct", "protected"]
        },
        "model": {
            "name": model.get("winner", "champion"),
            "evaluation": model.get("evaluations", {}),
            "synthetic": True,
        },
        "optimization": optimization or {"available": False},
        "scenarios": scenarios or [],
        "weather": weather_data,
        "air_quality": aq_data,
        "groundwater": gw_data,
    }
    return facts


def deterministic_placeholder(
    p: dict[str, Any],
    facts: dict[str, Any],
    failures: list[dict[str, str]] | None = None,
    is_error: bool = False,
) -> dict[str, Any]:
    """
    Deterministic evidence summary fallback ensuring reliable, grounded output without an LLM.
    
    Directly addresses decision-support queries:
    - High heat causation and TreeSHAP ranking
    - Demographic risk prioritization
    - Feasible cooling interventions
    - Clear scientific limitations
    - User-facing error reporting and setup guidance on provider downtime
    """
    import sys
    ai_mod = sys.modules.get("app.services.ai")
    if ai_mod and hasattr(ai_mod, "simulate"):
        sim_func = ai_mod.simulate
    else:
        from app.services.planning import simulate as sim_func

    p = p or {}
    shap_data = p.get("shap") if isinstance(p, dict) else None
    if isinstance(shap_data, dict) and shap_data:
        drivers = sorted(shap_data, key=lambda k: abs(shap_data[k]), reverse=True)[:3]
    else:
        drivers = ["vegetation_fraction", "surface_albedo", "building_density"]

    p_safe = p if "area_km2" in p else {**p, "area_km2": 1.0}
    candidate_actions = ["trees", "cool_roofs", "pavements"]
    feasible_actions: list[str] = []
    for key in candidate_actions:
        try:
            if sim_func(p_safe, {key: 5}).get("feasible", False):
                feasible_actions.append(key)
        except Exception:
            pass

    name = p.get("name", "Target zone") if isinstance(p, dict) else "Target zone"
    risk_level = (
        str(p.get("risk_level", "demonstration")).lower()
        if isinstance(p, dict)
        else "demonstration"
    )

    failures_list = failures or []
    has_failures = bool(failures_list) or is_error

    analytical_summary = (
        f"{name} has {risk_level} priority under the demonstration risk framework. "
        f"The strongest model associations are {', '.join(k.replace('_', ' ') for k in drivers)}."
    )

    if has_failures:
        error_reasons = "; ".join(
            f"{f.get('provider', 'provider')} ({f.get('reason', 'failed')})"
            for f in failures_list
        ) if failures_list else "Configured provider unavailable"
        error_msg = f"External AI provider downtime: {error_reasons}"
        full_summary = (
            f"[AI PROVIDER DOWNTIME]\n"
            f"{error_msg}\n\n"
            f"{SETUP_GUIDANCE}\n\n"
            f"[DETERMINISTIC ANALYTICAL EVIDENCE SUMMARY]\n"
            f"{analytical_summary}"
        )
        limitations = [
            f"Synthetic-fallback: external AI provider downtime ({error_reasons}). "
            f"Displaying deterministic analytical evidence summary instead of LLM generation.",
            "Synthetic surface-heat predictions are not air temperatures or health-risk forecasts.",
            "Scenario effects are hypothetical and require local calibration.",
        ]
        status = "error"
        setup_guidance = SETUP_GUIDANCE
    else:
        full_summary = f"[OFFLINE DETERMINISTIC ANALYSIS]\n{analytical_summary}"
        limitations = [
            "Synthetic-fallback: deterministic evidence summary template, not an LLM response.",
            "Synthetic surface-heat predictions are not air temperatures or health-risk forecasts.",
            "Scenario effects are hypothetical and require local calibration.",
        ]
        status = "ok"
        error_msg = None
        setup_guidance = None

    findings = [
        {
            "statement": "Feature contributions explain this model prediction; they do not establish causes.",
            "fact_ids": ["drivers", "prediction"],
        },
        {
            "statement": "Prioritize feasible surface treatments and test their land and water requirements before making a plan.",
            "fact_ids": ["constraints"],
        },
    ]

    citations = ["drivers", "prediction", "constraints"]

    return {
        "summary": full_summary,
        "findings": findings,
        "actions": feasible_actions,
        "limitations": limitations,
        "provider": "local evidence summary",
        "fallback": True,
        "synthetic_fallback": True,
        "label": "synthetic-fallback",
        "facts": facts,
        "failures": failures_list,
        "status": status,
        "error_message": error_msg,
        "setup_guidance": setup_guidance,
        "citations": citations,
        "response": full_summary,
    }


async def call_provider(
    provider: str,
    message: str,
    facts: dict[str, Any],
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Execute raw provider generation, validate citations, and audit numeric guardrails."""
    prov = get_provider(provider)
    if not prov:
        raise ValueError(f"Unknown or unsupported provider: {provider}")

    if not prov.is_configured():
        raise ValueError(f"{provider} key and model are not configured")

    raw = await prov.generate(message, facts, client=client)
    parsed = AIResponse.model_validate_json(raw)

    # Validate citations against supplied fact keys
    validate_citations(parsed.findings, facts)

    # Validate numeric guardrails against context facts
    full_prose = parsed.summary + " " + " ".join(f.statement for f in parsed.findings)
    validate_numeric_guardrails(full_prose, facts)

    return parsed.model_dump()


async def orchestrate_chat(
    message: str,
    provider: str,
    p: dict[str, Any],
    model: dict[str, Any],
    optimization: dict[str, Any] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """
    Multi-provider chat orchestrator implementing strict failover:
    requested provider -> alternative provider (in auto mode) -> local deterministic evidence summary fallback.
    """
    facts = context_for(p, model, optimization, scenarios)
    failures: list[dict[str, str]] = []

    if provider == "local":
        attempts: list[str] = []
    elif provider == "auto":
        attempts = ["groq", "gemini"]
    elif provider in PROVIDERS:
        attempts = [provider]
    else:
        attempts = []
        failures.append(
            {
                "provider": str(provider),
                "reason": f"Unsupported provider: {provider}",
            }
        )

    for q in attempts:
        try:
            result = await call_provider(q, message, facts, client=client)
            # Validate physical feasibility of recommended actions using simulate()
            validate_action_feasibility(result.get("actions", []), p)

            record_provider_event(q, True)
            findings = result.get("findings", [])
            citations = list(dict.fromkeys(
                fid for f in findings for fid in (f.get("fact_ids", []) if isinstance(f, dict) else getattr(f, "fact_ids", []))
            ))
            return {
                **result,
                "provider": q,
                "fallback": False,
                "synthetic_fallback": False,
                "label": None,
                "status": "ok",
                "error_message": None,
                "setup_guidance": None,
                "citations": citations,
                "response": result.get("summary", ""),
                "facts": facts,
                "failures": failures,
            }
        except Exception as e:
            prov = get_provider(q)
            is_configured = prov.is_configured() if prov else False
            sanitized = sanitize_error(e)
            reason = (
                "Not configured"
                if not is_configured
                else f"Provider error: {sanitized}"
            )
            failures.append(
                {
                    "provider": q,
                    "reason": reason,
                }
            )
            record_provider_event(q, False, reason)

    is_error = provider != "local" and bool(failures)
    return deterministic_placeholder(p, facts, failures, is_error=is_error)
