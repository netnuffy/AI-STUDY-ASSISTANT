"""AI summary generation with a map-reduce strategy for long documents.

One summary produces four outputs:
- content: the summary text itself (short / standard / detailed style)
- key_points: bullet-point takeaways
- key_concepts: key terms with a one-line definition each
- important_questions: exam-style questions the student should be able to answer
"""

from core import gemini
from core.logging import get_logger

logger = get_logger(__name__)

MAP_CHUNK_CHARS = 12000

SUMMARY_SYSTEM_PROMPT = (
    "You are an expert study assistant that writes clear, accurate summaries "
    "of study material."
)


def _summarise_text(text: str, style: str) -> str:
    style_instructions = {
        "short": "Write a very short summary: at most 5 bullet points.",
        "detailed": "Write a detailed, well-structured summary with headings.",
    }
    instruction = style_instructions.get(
        style,
        "Write a clear, well-structured summary with headings and bullet points.",
    )
    prompt = f"{instruction}\n\nText to summarise:\n{text}"
    return gemini.generate_text(
        prompt, system_instruction=SUMMARY_SYSTEM_PROMPT, temperature=0.3
    )


def _extract_structured(content: str) -> dict:
    """One JSON-mode call for key points, key concepts and important questions."""
    prompt = (
        "From the summary below, extract three things as a JSON object with "
        "exactly these keys: key_points, key_concepts, important_questions.\n"
        "- key_points: the 5-8 most important takeaways (array of strings).\n"
        "- key_concepts: 5-10 key terms with a one-line definition each "
        "(array of objects with keys term and definition).\n"
        "- important_questions: 5 exam-style questions a student should be able "
        "to answer after studying this material (array of strings).\n\n"
        f"Summary:\n{content}"
    )
    result = gemini.generate_json(prompt, system_instruction=SUMMARY_SYSTEM_PROMPT)
    if not isinstance(result, dict):
        logger.warning("Summary structured extraction returned non-object JSON")
        return {"key_points": [], "key_concepts": [], "important_questions": []}
    concepts = []
    for item in result.get("key_concepts", []) or []:
        if isinstance(item, dict):
            concepts.append(
                {
                    "term": str(item.get("term", "")),
                    "definition": str(item.get("definition", "")),
                }
            )
        else:
            concepts.append({"term": str(item), "definition": ""})
    return {
        "key_points": [str(p) for p in result.get("key_points", []) or []],
        "key_concepts": concepts,
        "important_questions": [
            str(q) for q in result.get("important_questions", []) or []
        ],
    }


def generate_summary(full_text: str, style: str = "standard") -> dict:
    """Returns {"content", "key_points", "key_concepts", "important_questions"}."""
    if len(full_text) > MAP_CHUNK_CHARS:
        sections = [
            full_text[i : i + MAP_CHUNK_CHARS]
            for i in range(0, len(full_text), MAP_CHUNK_CHARS)
        ]
        section_summaries = [_summarise_text(s, "standard") for s in sections]
        combined = "\n\n".join(section_summaries)
    else:
        combined = full_text

    content = _summarise_text(combined, style)
    structured = _extract_structured(content)
    return {"content": content, **structured}
