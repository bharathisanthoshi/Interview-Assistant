from pathlib import Path
import os

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None else default

GEMINI_API_KEY = _get_env("GEMINI_API_KEY", "")
GEMINI_MODEL = _get_env("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_URL = _get_env(
    "GEMINI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
)

RETRY_ATTEMPTS = int(_get_env("GEMINI_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_BASE_MS = int(_get_env("GEMINI_RETRY_DELAY_BASE_MS", "2000"))
EVALUATION_DELAY_MS = int(_get_env("EVALUATION_DELAY_MS", "1000"))
SUMMARY_DELAY_MS = int(_get_env("SUMMARY_DELAY_MS", "1500"))

GENERATION_TEMPERATURE = float(_get_env("GENERATION_TEMPERATURE", "0.7"))
GENERATION_MAX_TOKENS = int(_get_env("GENERATION_MAX_TOKENS", "200"))

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _get_env(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

ALLOWED_ORIGIN_REGEX = _get_env(
    "ALLOWED_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
).strip() or None
