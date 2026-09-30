import re
import pytest
from gpt_researcher.skills import deep_research as dr


def test_parse_research_results_dict_payload_round_164(monkeypatch):
    # Prepare a parsed dict with mixed item shapes: dicts (with different keys) and a plain string
    parsed = {
        "learnings": [
            {"insight": "First insight", "sourceUrl": "http://a"},
            {"learning": "Second", "citation": "http://b"},
            "Third simple"
        ],
        "followUpQuestions": ["Q1", ""]
    }

    # Patch _load_repaired_json to return our prepared parsed dict so the dict branch is taken
    monkeypatch.setattr(dr, "_load_repaired_json", lambda resp: parsed)

    result = dr.parse_research_results_response("irrelevant input", num_learnings=2)

    # Only the first two learnings should be returned (trimmed by num_learnings)
    assert result["learnings"] == ["First insight", "Second"]

    # Follow-up questions should be cleaned (empty strings removed) and trimmed
    assert result["followUpQuestions"] == ["Q1"]

    # Citations should include entries for the items that provided a citation/source
    assert result["citations"] == {"First insight": "http://a", "Second": "http://b"}


def test_parse_research_results_fallback_lines_and_url_extraction_round_164(monkeypatch):
    # Force _load_repaired_json to return a non-dict (the raw string) so fallback line-based parsing runs
    monkeypatch.setattr(dr, "_load_repaired_json", lambda s: s)

    # Patch the line-matching patterns to simple, deterministic regexes appropriate for this test input
    monkeypatch.setattr(dr, "LEARNING_LINE_PATTERN", re.compile(r'^\s*-\s*(?P<learning>.+)$'))
    monkeypatch.setattr(dr, "QUESTION_LINE_PATTERN", re.compile(r'^\s*\?\s*(?P<question>.+)$'))
    monkeypatch.setattr(dr, "URL_PATTERN", re.compile(r'https?://\S+'))

    # Create a response with two learning lines (one includes a URL to be extracted) and one question line
    response = (
        "- A learning http://example.com\n"
        "- Learning no url\n"
        "? Follow up?\n"
    )

    result = dr.parse_research_results_response(response, num_learnings=5)

    # Both learnings should be captured, with the URL removed from the textual learning
    assert result["learnings"] == ["A learning", "Learning no url"]

    # Question should be parsed and returned
    assert result["followUpQuestions"] == ["Follow up?"]

    # Citation should be extracted from the first learning via URL_PATTERN
    assert result["citations"] == {"A learning": "http://example.com"}
