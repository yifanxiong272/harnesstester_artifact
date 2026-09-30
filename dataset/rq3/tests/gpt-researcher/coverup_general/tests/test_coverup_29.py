# file: gpt_researcher/skills/image_generator.py:324-369
# asked: {"lines": [333, 334, 335, 336, 337, 339, 341, 343, 345, 346, 347, 348, 349, 350, 354, 355, 356, 357, 358, 361, 362, 363, 364, 365, 366, 369], "branches": [[339, 341], [339, 361], [343, 345], [343, 357], [345, 346], [345, 354], [357, 339], [357, 358], [361, 362], [361, 369]]}
# gained: {"lines": [333, 334, 335, 336, 337, 339, 341, 343, 345, 346, 347, 348, 349, 350, 354, 355, 356, 357, 358, 361, 362, 363, 364, 365, 366, 369], "branches": [[339, 341], [339, 361], [343, 345], [343, 357], [345, 346], [345, 354], [357, 339], [357, 358], [361, 362], [361, 369]]}

import types
import pytest

from gpt_researcher.skills.image_generator import ImageGenerator


def _noop_init_provider(self):
    # no-op to avoid requiring external providers during tests
    return None


def make_generator(monkeypatch, cfg_obj=None):
    # Ensure _init_provider does nothing to allow simple instantiation
    monkeypatch.setattr(ImageGenerator, "_init_provider", _noop_init_provider)
    researcher = types.SimpleNamespace(cfg=cfg_obj or types.SimpleNamespace())
    return ImageGenerator(researcher)


def test_extract_sections_no_headers(monkeypatch):
    gen = make_generator(monkeypatch)
    # No headers with ## or ### present; single-hash should be ignored
    report = "This is some introduction.\n# Not a section\nMore intro text."
    sections = gen._extract_sections(report)
    assert isinstance(sections, list)
    assert sections == []


def test_extract_sections_single_header(monkeypatch):
    gen = make_generator(monkeypatch)
    # Header at the start, followed by two content lines
    report = "## Header\nline1\nline2"
    sections = gen._extract_sections(report)
    assert len(sections) == 1
    sec = sections[0]
    assert sec["header"] == "Header"
    # content should join the two lines and be stripped
    assert sec["content"] == "line1\nline2"
    # header was at line 0, end_line should be last index
    assert sec["start_line"] == 0
    assert sec["end_line"] == 2  # three lines -> last index 2


def test_extract_sections_multiple_headers_and_mixed_hashes(monkeypatch):
    gen = make_generator(monkeypatch)
    # Prepare report with:
    # - a preface line that should be ignored (no current_section yet)
    # - ## First with one content line
    # - ### Sub with one content line
    # - ## Second with one content line and a single-hash line that should be treated as content
    report_lines = [
        "Intro line that should be ignored",
        "## First",
        "content a",
        "### Sub",
        "subcontent",
        "## Second",
        "content2",
        "# single-hash as content"
    ]
    report = "\n".join(report_lines)
    sections = gen._extract_sections(report)

    # Expect three sections: First, Sub, Second
    assert len(sections) == 3

    first, sub, second = sections

    # First section
    assert first["header"] == "First"
    assert first["content"] == "content a"
    # start_line is index of "## First" -> 1
    assert first["start_line"] == 1
    # end_line is line before next header -> index 2
    assert first["end_line"] == 2

    # Sub section (###)
    assert sub["header"] == "Sub"
    assert sub["content"] == "subcontent"
    # start_line index of "### Sub" -> 3
    assert sub["start_line"] == 3
    # end_line is line before next header -> index 4
    assert sub["end_line"] == 4

    # Second section: should include the single-hash line as content
    assert second["header"] == "Second"
    assert second["content"] == "content2\n# single-hash as content"
    # start_line index of "## Second" -> 5
    assert second["start_line"] == 5
    # end_line should be last index -> 7
    assert second["end_line"] == 7
