"""Summary service tests with a mocked Gemini client."""

from services.summary_service import MAP_CHUNK_CHARS, generate_summary

STRUCTURED = {
    "key_points": ["Plants make food from sunlight", "Chlorophyll absorbs light"],
    "key_concepts": [
        {"term": "Photosynthesis", "definition": "Process converting light to energy"},
        {"term": "Chlorophyll", "definition": "Green pigment in leaves"},
    ],
    "important_questions": [
        "What is photosynthesis?",
        "Why are leaves green?",
    ],
}


def _fake_generate_text(prompt, system_instruction=None, json_mode=False, temperature=0.3):
    return "FAKE SUMMARY"


def _fake_generate_json(prompt, system_instruction=None, temperature=0.3):
    return STRUCTURED


def test_generate_summary_returns_all_four_outputs(monkeypatch):
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_text", _fake_generate_text
    )
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json", _fake_generate_json
    )
    result = generate_summary("Some study material about plants.")
    assert result["content"] == "FAKE SUMMARY"
    assert result["key_points"] == STRUCTURED["key_points"]
    assert result["key_concepts"] == STRUCTURED["key_concepts"]
    assert result["important_questions"] == STRUCTURED["important_questions"]


def test_generate_summary_short_style_asks_for_bullets(monkeypatch):
    seen = {}

    def capture(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        seen["prompt"] = prompt
        return "short summary"

    monkeypatch.setattr("services.summary_service.gemini.generate_text", capture)
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json", _fake_generate_json
    )
    generate_summary("Material.", style="short")
    assert "bullet points" in seen["prompt"]


def test_generate_summary_detailed_style_asks_for_detail(monkeypatch):
    seen = {}

    def capture(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        seen["prompt"] = prompt
        return "detailed summary"

    monkeypatch.setattr("services.summary_service.gemini.generate_text", capture)
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json", _fake_generate_json
    )
    generate_summary("Material.", style="detailed")
    assert "detailed" in seen["prompt"].lower()


def test_generate_summary_long_text_uses_map_reduce(monkeypatch):
    calls = []

    def counting(prompt, system_instruction=None, json_mode=False, temperature=0.3):
        calls.append(prompt)
        return "section summary"

    monkeypatch.setattr("services.summary_service.gemini.generate_text", counting)
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json", _fake_generate_json
    )
    long_text = "x" * (MAP_CHUNK_CHARS * 2 + 100)  # 3 sections
    result = generate_summary(long_text)
    # 3 map calls (one per section) + 1 reduce call = 4
    assert len(calls) == 4
    assert result["content"] == "section summary"


def test_generate_summary_handles_non_object_json(monkeypatch):
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_text", _fake_generate_text
    )
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json",
        lambda *a, **k: ["not", "an", "object"],
    )
    result = generate_summary("Material.")
    assert result["content"] == "FAKE SUMMARY"
    assert result["key_points"] == []
    assert result["key_concepts"] == []
    assert result["important_questions"] == []


def test_generate_summary_normalises_string_concepts(monkeypatch):
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_text", _fake_generate_text
    )
    monkeypatch.setattr(
        "services.summary_service.gemini.generate_json",
        lambda *a, **k: {
            "key_points": [],
            "key_concepts": ["Mitosis"],
            "important_questions": [],
        },
    )
    result = generate_summary("Material.")
    assert result["key_concepts"] == [{"term": "Mitosis", "definition": ""}]
