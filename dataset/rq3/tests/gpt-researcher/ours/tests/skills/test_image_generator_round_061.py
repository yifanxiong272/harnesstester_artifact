import json
import re
import pytest

import gpt_researcher.skills.image_generator as ig_mod
from gpt_researcher.skills.image_generator import ImageGenerator

# Create an instance without invoking __init__ to avoid requiring researcher construction
def _make_instance():
    # Bypass __init__ to keep test focused on _parse_analysis_response
    return object.__new__(ImageGenerator)


def test_no_json_round_061():
    inst = _make_instance()
    # Response with no JSON-like braces should trigger the no-json branch and return []
    response = "This response contains no json payload"
    sections = []

    result = inst._parse_analysis_response(response, sections)

    assert result == [], "Expected empty list when no JSON is present in the response"


def test_valid_json_enrichment_round_061():
    inst = _make_instance()
    # Build sections such that only the first suggestion maps to a valid section index
    sections = [
        {"header": "Header One", "content": "Some content for section one.", "start_line": 11},
        {"header": "Header Two", "content": "Second section content.", "start_line": 22},
    ]

    suggestions = [
        {"section_number": 1, "image_prompt": "An image of a blue ball.", "reason": "Illustrates the concept."},
        {"section_number": 3, "image_prompt": "Out of range prompt.", "reason": "Should be ignored."},
    ]

    payload = {"suggestions": suggestions}
    # Put the JSON somewhere inside the response text to mimic LLM output
    response = f"Lead-in text before json {json.dumps(payload)} and some trailing text"

    result = inst._parse_analysis_response(response, sections)

    # Only the first suggestion should yield an enriched entry
    assert isinstance(result, list)
    assert len(result) == 1

    entry = result[0]
    assert entry["section_header"] == sections[0]["header"]
    assert entry["section_content"] == sections[0]["content"][:1000]
    assert entry["image_prompt"] == "An image of a blue ball."
    assert entry["reason"] == "Illustrates the concept."
    assert entry["insert_after_line"] == sections[0]["start_line"]


def test_json_decode_error_round_061(monkeypatch):
    inst = _make_instance()

    # Ensure there is a JSON-like match so code reaches json.loads
    response = "prefix { not valid json } suffix"
    sections = []

    # Patch the module's json.loads to raise JSONDecodeError to exercise the except branch
    def _raises(s):
        # Construct JSONDecodeError with required args: msg, doc, pos
        raise json.JSONDecodeError("fail", s, 0)

    monkeypatch.setattr(ig_mod.json, "loads", _raises)

    # Capture whether logger.error is invoked and what it receives
    recorded = {"called": False, "msg": None}

    def _recorder(msg):
        recorded["called"] = True
        recorded["msg"] = str(msg)

    monkeypatch.setattr(ig_mod.logger, "error", _recorder)

    result = inst._parse_analysis_response(response, sections)

    assert result == [], "On JSONDecodeError the function should return an empty list"
    assert recorded["called"] is True, "logger.error should be called when JSON parsing fails"
    assert "Failed to parse analysis JSON" in recorded["msg"] or "fail" in recorded["msg"], "Error log should contain failure information"
