# file: gpt_researcher/prompts.py:257-312
# asked: {"lines": [273, 274, 275, 283, 287, 289, 290, 292, 294, 299, 305, 306, 307, 308, 309, 311], "branches": [[274, 275], [274, 283]]}
# gained: {"lines": [273, 274, 275, 283, 287, 289, 290, 292, 294, 299, 305, 306, 307, 308, 309, 311], "branches": [[274, 275], [274, 283]]}

from datetime import date

import pytest

import gpt_researcher.prompts as prompts_mod
from gpt_researcher.prompts import PromptFamily


class _StubReportSource:
    class Web:
        value = "web"


class _Tone:
    def __init__(self, value):
        self.value = value


def test_generate_report_prompt_web_branch_includes_url_instructions_and_tone(monkeypatch):
    # Arrange: patch the ReportSource used inside the prompts module to a stub that has Web.value == "web"
    monkeypatch.setattr(prompts_mod, "ReportSource", _StubReportSource, raising=False)

    question = "What is the impact of X on Y?"
    context = "Some useful context"
    report_source = "web"  # matches _StubReportSource.Web.value
    report_format = "apa"
    total_words = 500
    tone = _Tone("formal")
    language = "english"

    # Act
    result = PromptFamily.generate_report_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        total_words=total_words,
        tone=tone,
        language=language,
    )

    # Assert: verify that the web-specific reference instructions are present
    assert "You MUST write all used source urls at the end of the report as references" in result
    assert "Every url should be hyperlinked: [url website](url)" in result
    # Assert: tone prompt is included
    assert "Write the report in a formal tone." in result
    # Assert: total_words interpolation
    assert f"at least {total_words} words" in result
    # Assert: report_format interpolation
    assert f"markdown syntax and {report_format} format" in result or f"and {report_format} format" in result
    # Assert: language interpolation
    assert f"You MUST write the report in the following language: {language}" in result
    # Assert: today's date is included
    assert str(date.today()) in result


def test_generate_report_prompt_non_web_branch_no_tone_and_document_instructions(monkeypatch):
    # Arrange: patch the ReportSource used inside the prompts module to the same stub
    monkeypatch.setattr(prompts_mod, "ReportSource", _StubReportSource, raising=False)

    question = "Summarize the findings."
    context = "Different context"
    report_source = "file"  # does NOT match _StubReportSource.Web.value -> triggers else branch
    report_format = "mla"
    total_words = 250
    tone = None
    language = "spanish"

    # Act
    result = PromptFamily.generate_report_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        total_words=total_words,
        tone=tone,
        language=language,
    )

    # Assert: verify non-web-specific reference instructions are present
    assert "You MUST write all used source document names at the end of the report as references" in result
    # Assert: web-specific phrase is NOT present
    assert "Every url should be hyperlinked: [url website](url)" not in result
    # Assert: tone prompt is not present when tone is None
    assert "Write the report in a " not in result
    # Assert: total_words interpolation
    assert f"at least {total_words} words" in result
    # Assert: report_format interpolation
    assert f"markdown syntax and {report_format} format" in result or f"and {report_format} format" in result
    # Assert: language interpolation (case-sensitive as module uses provided value)
    assert f"You MUST write the report in the following language: {language}" in result
    # Assert: today's date is included
    assert str(date.today()) in result
