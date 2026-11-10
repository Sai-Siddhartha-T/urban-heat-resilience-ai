"""AI Resilience Assistant with citation validation and multi-provider failover."""

import asyncio
from fastapi import APIRouter
from app.db import save, records
from app.schemas import ChatRequest, ChatResponse
from app.services import ai
from app.services.state import state, zone

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(req: ChatRequest):
    """Context-aware generative reasoning with strict grounding against model facts and simulations."""
    p = await asyncio.to_thread(zone, req.city, req.zone_id, req.mode)
    opts = [r for r in records("optimization") if r.get("city") == req.city]
    sims = [r for r in records("scenario") if r.get("city") == req.city]
    result = await ai.chat(
        req.message,
        req.provider,
        p,
        state(req.city, req.mode)["model"],
        opts[0] if opts else None,
        sims[:3],
    )
    save(
        "conversation", {"city": req.city, "question": req.message, "response": result}
    )
    return result
