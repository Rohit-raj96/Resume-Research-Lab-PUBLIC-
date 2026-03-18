from groq import Groq, NotFoundError

from core.config import GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_CANDIDATES

client = Groq(api_key=GROQ_API_KEY)


def create_chat_completion(**kwargs):
    last_error = None

    for model in GROQ_MODEL_CANDIDATES:
        try:
            return client.chat.completions.create(model=model, **kwargs)
        except NotFoundError as exc:
            last_error = exc

    attempted_models = ", ".join(GROQ_MODEL_CANDIDATES)
    raise RuntimeError(
        "Groq could not find a supported chat model for this deployment. "
        f"Configured model: {GROQ_MODEL}. Attempted: {attempted_models}. "
        "Set GROQ_MODEL in Streamlit Cloud Secrets to a supported model, "
        "for example `llama-3.3-70b-versatile`."
    ) from last_error
