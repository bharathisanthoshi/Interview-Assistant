\
import asyncio
from typing import Any, Dict

import httpx

from .config import (
    GEMINI_API_KEY,
    GEMINI_API_URL,
    RETRY_ATTEMPTS,
    RETRY_DELAY_BASE_MS,
    GENERATION_TEMPERATURE,
    GENERATION_MAX_TOKENS,
)


class GeminiApiError(RuntimeError):
    pass


async def call_gemini_api(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise GeminiApiError("Gemini API key is not configured")

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": GENERATION_TEMPERATURE,
            "maxOutputTokens": GENERATION_MAX_TOKENS,
        },
    }

    params = {"key": GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(RETRY_ATTEMPTS):
            if attempt > 0:
                await asyncio.sleep((RETRY_DELAY_BASE_MS * attempt) / 1000)

            try:
                response = await client.post(GEMINI_API_URL, params=params, json=payload)
                        if response.status_code in (429, 503) and attempt < RETRY_ATTEMPTS - 1:
                            continue

                        if response.status_code >= 400:
                            try:
                                error_payload = response.json()
                                error_message = (
                                    error_payload.get("error", {}).get("message")
                                    or error_payload.get("message")
                                    or response.text
                                )
                            except Exception:
                                error_message = response.text
                            raise GeminiApiError(
                                f"{response.status_code} {response.reason_phrase}: {error_message}"
                            )

                        data = response.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    raise GeminiApiError("Invalid response from Gemini API")

                content = candidates[0].get("content", {})
                parts = content.get("parts") or []
                text = parts[0].get("text") if parts else None
                if not text:
                    raise GeminiApiError("Invalid response from Gemini API")

                return text.strip()
            except Exception as exc:
                if attempt >= RETRY_ATTEMPTS - 1:
                    raise GeminiApiError(str(exc)) from exc

    raise GeminiApiError("Max retries reached")
