"""Thin wrapper around the Google Gemini API (new google-genai SDK).

The google-genai package is imported lazily so the app can start
(and be tested) without it installed. AI features raise ExternalServiceError
only when actually used without the package or API key.

Migrated from the deprecated google-generativeai SDK on 2026-11-23: the old
SDK talks to the Gemini v1beta API, where the text-embedding-004 model does
not exist (404 "models/text-embedding-004 is not found for API version
v1beta"), which broke document processing and chat on the live backend.
The google-genai SDK uses the v1 API, where text-embedding-004 works.
"""

import json

from core.config import get_settings
from core.exceptions import ExternalServiceError
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _client():
    try:
        from google import genai
    except ImportError as exc:
        raise ExternalServiceError("google-genai is not installed") from exc
    if not settings.GEMINI_API_KEY:
        raise ExternalServiceError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.3,
) -> str:
    from google.genai import types

    client = _client()
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
        response_mime_type="application/json" if json_mode else None,
    )
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
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
    from google.genai import types

    client = _client()
    try:
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
    except Exception as exc:
        logger.error("Gemini embedding failed: %s", exc)
        raise ExternalServiceError("Embedding failed") from exc
    return [list(embedding.values) for embedding in result.embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a single user question (retrieval_query task type)."""
    from google.genai import types

    client = _client()
    try:
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
    except Exception as exc:
        logger.error("Gemini query embedding failed: %s", exc)
        raise ExternalServiceError("Embedding failed") from exc
    return list(result.embeddings[0].values)
