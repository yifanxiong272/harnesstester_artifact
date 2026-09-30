import pytest

from gpt_researcher.skills.image_generator import ImageGenerator


def test_no_headers_round_047():
    """When the report has no markdown headers (## or ###), no sections should be extracted."""
    report = "Just some text\nAnother line"

    sections = ImageGenerator._extract_sections(None, report)

    assert isinstance(sections, list)
    assert sections == []


def test_single_section_round_047():
    """A single top-level section header with multiple content lines should produce one section
    with correct header, joined content (stripped), start_line 0 and end_line equal to len(lines)-1.
    """
    report = "## Intro\nThis is line1\nThis is line2\n"

    sections = ImageGenerator._extract_sections(None, report)

    assert len(sections) == 1
    sec = sections[0]
    assert sec["header"] == "Intro"
    # content should join the two content lines and be stripped of trailing newline
    assert sec["content"] == "This is line1\nThis is line2"
    assert sec["start_line"] == 0
    # there are 4 lines when splitting the report (last is empty), so end_line is 3
    assert sec["end_line"] == 3


def test_multiple_sections_and_consecutive_headers_round_047():
    """Covers multiple headers including a header that follows immediately after another (empty section content)
    and verifies that single-# lines are not treated as headers but as content when inside a section.
    """
    report_lines = [
        "## First",          # 0 -> header
        "content A",         # 1 -> content for First
        "# not header",      # 2 -> should be treated as content (only ## or ### are headers)
        "### Second",        # 3 -> header; Second will have empty content
        "## Third",          # 4 -> header immediately after Second (Second has empty content)
        "content third",     # 5 -> content for Third
    ]
    report = "\n".join(report_lines)

    sections = ImageGenerator._extract_sections(None, report)

    # Expect three sections: First, Second, Third
    assert len(sections) == 3

    first, second, third = sections

    # First: header and two content lines (including the single-# line as content)
    assert first["header"] == "First"
    assert first["content"] == "content A\n# not header"
    assert first["start_line"] == 0
    # end_line for First should be index 2 (i - 1 where i was the index of the next header)
    assert first["end_line"] == 2

    # Second: header with no content (empty string), start_line should be 3, end_line should be 3
    assert second["header"] == "Second"
    assert second["content"] == ""
    assert second["start_line"] == 3
    assert second["end_line"] == 3

    # Third: header with one content line, start_line 4, end_line equals last index (5)
    assert third["header"] == "Third"
    assert third["content"] == "content third"
    assert third["start_line"] == 4
    assert third["end_line"] == 5
