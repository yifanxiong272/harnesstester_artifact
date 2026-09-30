# file: gpt_researcher/skills/image_generator.py:423-465
# asked: {"lines": [437, 439, 440, 441, 442, 444, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 461, 463, 464, 465], "branches": [[440, 441], [440, 444], [449, 450], [449, 461], [451, 449], [451, 452]]}
# gained: {"lines": [437, 439, 440, 441, 442, 444, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 461, 463, 464, 465], "branches": [[440, 441], [440, 444], [449, 450], [449, 461], [451, 449], [451, 452]]}

import json
import pytest
from gpt_researcher.skills.image_generator import ImageGenerator


def test_no_json_found_returns_empty_list(monkeypatch):
    # Prevent heavy initialization in __init__
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    gen = ImageGenerator(researcher=type("R", (), {"cfg": type("C", (), {})()})())
    response = "This response contains no json-like braces at all."
    sections = [
        {"header": "Sec 1", "content": "content", "start_line": 1},
    ]
    result = gen._parse_analysis_response(response, sections)
    assert result == []


def test_valid_json_enriches_suggestions_and_truncates_content(monkeypatch):
    # Prevent heavy initialization in __init__
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    gen = ImageGenerator(researcher=type("R", (), {"cfg": type("C", (), {})()})())

    # Create two sections. One with very long content to test truncation.
    long_content = "x" * 1500
    sections = [
        {"header": "Header One", "content": "Short content", "start_line": 10},
        {"header": "Header Two", "content": long_content, "start_line": 20},
    ]

    # Prepare suggestions:
    # - suggestion for section_number 1 -> maps to sections[0]
    # - suggestion for section_number 2 -> maps to sections[1] (long content truncated)
    # - suggestion for section_number 99 -> out of range and should be ignored
    suggestions = [
        {
            "section_number": 1,
            "image_prompt": "a dog running",
            "reason": "Shows action"
        },
        {
            "section_number": 2,
            "image_prompt": "a long landscape",
            "reason": "Sets the scene"
        },
        {
            "section_number": 99,
            "image_prompt": "out of range",
            "reason": "Should be ignored"
        },
    ]

    payload = {"suggestions": suggestions}
    response = "analysis text before " + json.dumps(payload) + " trailing text"

    result = gen._parse_analysis_response(response, sections)

    # Two valid suggestions should be returned (the out-of-range one ignored)
    assert isinstance(result, list)
    assert len(result) == 2

    # Check mapping for first suggestion -> section 0
    first = result[0]
    assert first["section_header"] == "Header One"
    assert first["section_content"] == "Short content"
    assert first["image_prompt"] == "a dog running"
    assert first["reason"] == "Shows action"
    assert first["insert_after_line"] == 10

    # Check mapping for second suggestion -> section 1 and truncated content length 1000
    second = result[1]
    assert second["section_header"] == "Header Two"
    assert len(second["section_content"]) == 1000
    assert second["section_content"] == long_content[:1000]
    assert second["image_prompt"] == "a long landscape"
    assert second["reason"] == "Sets the scene"
    assert second["insert_after_line"] == 20


def test_invalid_json_triggers_json_decode_exception_and_returns_empty(monkeypatch):
    # Prevent heavy initialization in __init__
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    gen = ImageGenerator(researcher=type("R", (), {"cfg": type("C", (), {})()})())

    # Response contains braces but invalid JSON (unquoted key), causing json.loads to raise JSONDecodeError
    response = "some text {invalid: } some more text"

    sections = [
        {"header": "S1", "content": "c", "start_line": 1},
    ]

    # Monkeypatch json.loads to raise json.JSONDecodeError when called.
    def fake_loads(s):
        raise json.JSONDecodeError("Expecting value", s, 0)

    monkeypatch.setattr(json, "loads", fake_loads)

    res = gen._parse_analysis_response(response, sections)
    assert res == []
