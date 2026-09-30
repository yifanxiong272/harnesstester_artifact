from datetime import date
from types import SimpleNamespace

import pytest

from gpt_researcher.prompts import PromptFamily
from gpt_researcher.utils.enum import ReportSource


def test_generate_report_prompt_web_branch_round_160():
    """Cover the branch where report_source == ReportSource.Web.value,
    ensure web-specific reference_prompt and tone_prompt appear, and
    required interpolations (context, question, total_words, date) are present.
    """
    question = "What is the impact of X?"
    context = "Summary of findings"
    # use the enum value to trigger the Web branch
    report_source = ReportSource.Web.value
    report_format = "apa"
    total_words = 150
    tone = SimpleNamespace(value="formal")
    language = "english"

    prompt = PromptFamily.generate_report_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        total_words=total_words,
        tone=tone,
        language=language,
    )

    # reference prompt for web sources must be present
    assert "You MUST write all used source urls" in prompt
    # ensure web-specific guidance about hyperlinks is included
    assert "Every url should be hyperlinked" in prompt
    # tone prompt must be present and use the tone.value
    assert "Write the report in a formal tone." in prompt
    # context and question interpolations
    assert f'Information: "{context}"' in prompt
    assert question in prompt
    # total_words interpolation appears in the instructions
    assert f"at least {total_words} words." in prompt
    # date interpolation must match today's date string
    assert str(date.today()) in prompt


def test_generate_report_prompt_nonweb_branch_no_tone_round_160():
    """Cover the else branch (non-web report_source) and when tone is None,
    ensuring document-specific reference text is used and no tone prompt is inserted.
    """
    question = "Explain Y"
    context = "Local document context"
    # choose a value that is not the Web.value to trigger the else branch
    report_source = "local_documents"
    report_format = "md"
    total_words = 200
    tone = None
    language = "english"

    prompt = PromptFamily.generate_report_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        total_words=total_words,
        tone=tone,
        language=language,
    )

    # else-branch reference_prompt for documents should be present
    assert "You MUST write all used source document names" in prompt
    # tone should be absent when tone is None
    assert "Write the report in a" not in prompt
    # ensure context interpolation included
    assert f'Information: "{context}"' in prompt
    # ensure total_words interpolation is present
    assert f"at least {total_words} words." in prompt
    # date interpolation still present
    assert str(date.today()) in prompt
