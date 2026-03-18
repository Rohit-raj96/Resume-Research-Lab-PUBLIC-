import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _unique_models(models: list[str]) -> list[str]:
    seen: list[str] = []
    for model in models:
        if model and model not in seen:
            seen.append(model)
    return seen


GROQ_MODEL = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
GROQ_MODEL_CANDIDATES = _unique_models(
    [
        GROQ_MODEL,
        DEFAULT_GROQ_MODEL,
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant",
    ]
)

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set in environment/.env")
