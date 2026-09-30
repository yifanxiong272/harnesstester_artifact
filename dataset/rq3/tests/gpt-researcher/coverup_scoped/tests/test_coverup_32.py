# file: gpt_researcher/skills/image_generator.py:423-465
# asked: {"lines": [437, 439, 440, 441, 442, 444, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 461, 463, 464, 465], "branches": [[440, 441], [440, 444], [449, 450], [449, 461], [451, 449], [451, 452]]}
# gained: {"lines": [437, 439, 440, 441, 442, 444, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 461, 463, 464, 465], "branches": [[440, 441], [440, 444], [449, 450], [449, 461], [451, 449], [451, 452]]}

import json
import re
import types
from types import SimpleNamespace

import pytest

from gpt_researcher.skills.image_generator import ImageGenerator


@pytest.fixture(autouse=True)
def noop_init_provider(monkeypatch):
    """
    Ensure ImageGenerator._init_provider does nothing during tests to avoid side-effects.
    """
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)
    yield


def _make_generator():
    # Create a minimal dummy researcher with cfg attribute expected by ImageGenerator
    dummy_researcher = SimpleNamespace(cfg=SimpleNamespace(image_generation_max_images=3))
    return ImageGenerator(dummy_researcher)


def test_parse_analysis_response_no_json_returns_empty(monkeypatch):
    gen = _make_generator()

    # Response with no JSON-like braces at all
    response = "This response contains no json object"

    sections = [
        {"header": "Intro", "content": "short", "start_line": 1},
    ]

    result = gen._parse_analysis_response(response, sections)
    assert result == [], "Expected empty list when no JSON found in response"


def test_parse_analysis_response_valid_json_enriches_and_trims_content(monkeypatch):
    gen = _make_generator()

    # Create a long content to verify trimming to 1000 characters
    long_content = "x" * 2000
    sections = [
        {"header": "First Section", "content": long_content, "start_line": 10},
        {"header": "Second Section", "content": "second", "start_line": 50},
    ]

    # Prepare suggestions: one valid (section_number 1), one out-of-range (99)
    suggestions = [
        {
            "section_number": 1,
            "image_prompt": "A diagram of X",
            "reason": "Clarifies process",
        },
        {
            "section_number": 99,
            "image_prompt": "Should be ignored",
            "reason": "Out of range",
        },
    ]

    data = {"suggestions": suggestions}
    # Embed JSON inside surrounding text to ensure regex extraction
    response = f"Some preamble text before the json {json.dumps(data)} some trailing text"

    result = gen._parse_analysis_response(response, sections)

    # Only the valid suggestion (section_number 1) should be present
    assert isinstance(result, list)
    assert len(result) == 1

    enriched = result[0]
    assert enriched["section_header"] == "First Section"
    # Content should be trimmed to 1000 characters
    assert len(enriched["section_content"]) == 1000
    assert enriched["section_content"] == long_content[:1000]
    assert enriched["image_prompt"] == "A diagram of X"
    assert enriched["reason"] == "Clarifies process"
    assert enriched["insert_after_line"] == 10


def test_parse_analysis_response_invalid_json_triggers_jsondecodeerror(monkeypatch):
    gen = _make_generator()

    sections = [
        {"header": "Only", "content": "content", "start_line": 3},
    ]

    # Response with braces but invalid JSON inside -> json.loads should raise JSONDecodeError
    response = "Here is a broken json: {invalid: ,, } end."

    result = gen._parse_analysis_response(response, sections)
    assert result == [], "Expected empty list when JSON is present but invalid (JSONDecodeError)"
