"""Google Gemini LLM provider implementation with model discovery, retries, and rate-limit handling."""

import asyncio
import logging
import os
from typing import Any
import httpx

from app.services.llm.provider import (
    BaseLLMProvider,
    build_prompt,
    extract_json_str,
    sanitize_error,
)

log = logging.getLogger("heatwise.llm.gemini")


class GeminiProvider(BaseLLMProvider):
    name: str = "gemini"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    default_timeout: float = 35.0
    max_retries: int = 2

    def get_auth_headers(self) -> dict[str, str] | None:
        """
        Resolves authentication headers for Gemini / Generative Language API.
        Precedence:
        1. GEMINI_API_KEY or GOOGLE_API_KEY
        2. AGY_ACCOUNT (as API key token, OAuth token, or via google.auth ADC)
        """
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if key:
            if key.startswith("ya29."):
                return {"Authorization": f"Bearer {key}"}
            return {"x-goog-api-key": key}

        agy_account = os.getenv("AGY_ACCOUNT")
        if agy_account:
            if agy_account.startswith("ya29."):
                return {"Authorization": f"Bearer {agy_account}"}
            if len(agy_account) > 15 and "@" not in agy_account:
                return {"x-goog-api-key": agy_account}
            # Attempt resolving OAuth bearer token through google.auth ADC
            try:
                import google.auth
                from google.auth.transport.requests import Request

                credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/generative-language"]
                )
                if credentials:
                    credentials.refresh(Request())
                    if credentials.token:
                        return {"Authorization": f"Bearer {credentials.token}"}
            except Exception:
                pass

        return None

    def get_model(self) -> str | None:
        return os.getenv("GEMINI_MODEL") or None

    def is_configured(self) -> bool:
        return bool(self.get_auth_headers() and self.get_model())

    async def check_availability(self, client: httpx.AsyncClient) -> bool:
        headers = self.get_auth_headers()
        model = self.get_model()
        if not headers or not model:
            return False
        try:
            resp = await client.get(f"{self.base_url}/models", headers=headers, timeout=self.default_timeout)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            norm_model = "models/" + model.removeprefix("models/")
            return norm_model in [m.get("name") for m in models]
        except Exception as e:
            log.warning(f"Gemini availability check failed: {sanitize_error(e)}")
            return False

    async def _post_generate_with_retry(
        self,
        c: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        """Execute generateContent with rate-limit and transient error backoff."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = await c.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.default_timeout,
                )
                if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
                    if attempt < self.max_retries:
                        retry_after = r.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() else (0.5 * (2 ** attempt))
                        await asyncio.sleep(min(delay, 2.0))
                        continue
                r.raise_for_status()
                return r
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Failed to complete request after retries")

    async def generate(
        self,
        message: str,
        facts: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> str:
        headers = self.get_auth_headers()
        model = self.get_model()
        if not headers or not model:
            raise ValueError("gemini key and model are not configured")

        prompt = build_prompt(message, facts)
        norm_model = model.removeprefix("models/")

        async def _execute(c: httpx.AsyncClient) -> str:
            # 1. Model discovery & validation
            available = await c.get(f"{self.base_url}/models", headers=headers, timeout=self.default_timeout)
            available.raise_for_status()
            models_list = available.json().get("models", [])
            avail_names = [m.get("name", "") for m in models_list]
            if f"models/{norm_model}" not in avail_names:
                raise ValueError("Configured Gemini model is not available")

            # 2. Content generation
            url = f"{self.base_url}/models/{norm_model}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }
            r = await self._post_generate_with_retry(c, url, headers, payload)
            candidates = r.json().get("candidates", [])
            if not candidates:
                raise ValueError("Gemini returned empty candidates in response")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("Gemini returned empty parts in response")
            raw = parts[0].get("text", "")
            if not raw:
                raise ValueError("Gemini returned empty candidate text")
            return extract_json_str(raw)

        try:
            if client is not None:
                return await _execute(client)
            else:
                async with httpx.AsyncClient(timeout=self.default_timeout) as c:
                    return await _execute(c)
        except Exception as e:
            sanitized = sanitize_error(e)
            log.warning(f"Gemini generation failed: {sanitized}")
            raise RuntimeError(sanitized) from None


gemini_provider = GeminiProvider()
