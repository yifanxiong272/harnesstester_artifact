import types
from types import SimpleNamespace
import gpt_researcher.prompts as prompts


def test_generate_deep_research_prompt_web_branch_round_161(monkeypatch):
    """Covers the branch where report_source == ReportSource.Web.value and tone is provided.

    We monkeypatch the ReportSource symbol inside the prompts module so the staticmethod
    compares against a known value. We provide a simple tone object with a .value attribute
    to exercise the tone formatting branch.
    """
    # Patch the ReportSource used inside the module
    monkeypatch.setattr(
        prompts,
        "ReportSource",
        SimpleNamespace(Web=SimpleNamespace(value="web")),
    )

    question = "What are the effects of X on Y?"
    context = "Level 1: finding A. Level 2: finding B."
    report_source = "web"
    report_format = "mla"
    tone = SimpleNamespace(value="formal")
    total_words = 1500
    language = "english"

    result = prompts.PromptFamily.generate_deep_research_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        tone=tone,
        total_words=total_words,
        language=language,
    )

    # Assertions verify branch-specific strings and core interpolations
    assert "write all used source urls" in result.lower()
    assert "every url should be hyperlinked" in result
    # Tone branch exercised: should include the tone phrase
    assert "Write the report in a formal tone." in result
    # Core interpolations
    assert context in result
    assert question in result
    assert str(total_words) in result
    assert report_format in result
    # Date line is present (we don't assert exact date to keep deterministic)
    assert "Assume the current date is" in result


def test_generate_deep_research_prompt_nonweb_branch_no_tone_round_161(monkeypatch):
    """Covers the non-web branch (documents) and the case where tone is omitted.

    We reuse the same monkeypatch for ReportSource but pass a different report_source
    value so the else branch is executed. Tone is None to ensure the tone_prompt is empty.
    """
    monkeypatch.setattr(
        prompts,
        "ReportSource",
        SimpleNamespace(Web=SimpleNamespace(value="web")),
    )

    question = "How does Z influence Q?"
    context = "Short context snippet."
    report_source = "local_doc"
    report_format = "apa"
    tone = None
    total_words = 2000
    language = "english"

    result = prompts.PromptFamily.generate_deep_research_prompt(
        question=question,
        context=context,
        report_source=report_source,
        report_format=report_format,
        tone=tone,
        total_words=total_words,
        language=language,
    )

    # Document-specific reference instructions exist in the else branch
    assert "write all used source document names" in result.lower()
    # Since tone is None, the tone sentence should not be present
    assert "Write the report in a" not in result
    # Core interpolations remain
    assert context in result
    assert question in result
    assert str(total_words) in result
    assert report_format in result
    assert "Assume the current date is" in result
