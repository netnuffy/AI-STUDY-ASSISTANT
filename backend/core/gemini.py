"""Thin wrapper around the Google Gemini API.

The google-generativeai package is imported lazily so the app can start
(and be tested) without it installed. AI features raise ExternalServiceError
only when actually used without the package or API key.
"""

import json

from core.config import get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _configure():
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ExternalServiceError("google-generativeai is not installed") from exc
    if not settings.GEMINI_API_KEY:
        raise ExternalServiceError("GEMINI_API_KEY is not configured")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.3,
) -> str:
    genai = _configure()
    generation_config: dict = {"temperature": temperature}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=generation_config,
    )
    try:
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.error("Gemini generation failed: %s", exc)
        raise ExternalServiceError("AI generation failed, please try again") from exc
    return response.text


def generate_json(
    prompt: str, system_instruction: str | None = None, temperature: float = 0.3
):
    """Generate text in JSON mode and parse it. Returns a dict or list."""
    text = generate_text(
        prompt, system_instruction=system_instruction, json_mode=True, temperature=temperature
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %s", text[:500])
        raise ExternalServiceError("AI returned an unexpected response") from exc


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks (retrieval_document task type)."""
    genai = _configure()
    try:
        result = genai.embed_content(
            model=f"models/{settings.GEMINI_EMBEDDING_MODEL}",
            content=texts,
            task_type="retrieval_document",
        )
    except Exception as exc:
        logger.error("Gemini embedding failed: %s", exc)
        raise ExternalServiceError("Embedding failed") from exc
    return result["embedding"]


def embed_query(text: str) -> list[float]:
    """Embed a single user question (retrieval_query task type)."""
    genai = _configure()
    try:
        result = genai.embed_content(
            model=f"models/{settings.GEMINI_EMBEDDING_MODEL}",
            content=text,
            task_type="retrieval_query",
        )
    except Exception as exc:
        logger.error("Gemini query embedding failed: %s", exc)
        raise ExternalServiceError("Embedding failed") from exc
    return result["embedding"]
