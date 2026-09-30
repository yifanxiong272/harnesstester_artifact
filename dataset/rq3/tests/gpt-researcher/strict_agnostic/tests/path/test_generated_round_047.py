import pytest
from gpt_researcher.skills.image_generator import ImageGenerator


def _make_image_generator_without_init():
    # Bypass __init__ because _extract_sections does not use instance state.
    return object.__new__(ImageGenerator)


def test_extract_sections_single_section_round_047():
    ig = _make_image_generator_without_init()
    report = "## Title\nLine1\nLine2"

    sections = ig._extract_sections(report)

    # Expect a single section with header and two content lines
    assert isinstance(sections, list)
    assert len(sections) == 1

    s = sections[0]
    assert s["header"] == "Title"
    # content should preserve line breaks and be stripped of surrounding whitespace
    assert s["content"] == "Line1\nLine2"
    # header was at line 0, content ends at last line index (2)
    assert s["start_line"] == 0
    assert s["end_line"] == 2


def test_extract_sections_multiple_sections_trailing_round_047():
    ig = _make_image_generator_without_init()
    # Build a report that exercises: headers after non-header lines, saving previous section,
    # multiple header levels (## and ###), blank content lines, and final section append.
    report_lines = [
        "Intro line that should be ignored",
        "## First Header",
        "first content line",
        "",  # blank line should be included in content then stripped
        "### Subheader",
        "sub content",
        "## Second Header",
        "last content",
    ]
    report = "\n".join(report_lines)

    sections = ig._extract_sections(report)

    # We should get three sections: First Header, Subheader, Second Header
    assert isinstance(sections, list)
    assert len(sections) == 3

    first, second, third = sections

    # First section was started at line index 1 and ended at 3 (i-1 when next header at 4)
    assert first["header"] == "First Header"
    # blank line in content should be stripped away, leaving only the non-empty content
    assert first["content"] == "first content line"
    assert first["start_line"] == 1
    assert first["end_line"] == 3

    # Second (###) section
    assert second["header"] == "Subheader"
    assert second["content"] == "sub content"
    assert second["start_line"] == 4
    assert second["end_line"] == 5

    # Third section should include the trailing content and have end_line equal to last index
    assert third["header"] == "Second Header"
    assert third["content"] == "last content"
    assert third["start_line"] == 6
    assert third["end_line"] == len(report_lines) - 1


def test_extract_sections_no_headers_round_047():
    ig = _make_image_generator_without_init()
    report = "no headers here\nstill no headers"

    sections = ig._extract_sections(report)

    # With no markdown headers (## or ###), there should be no extracted sections
    assert isinstance(sections, list)
    assert sections == []
