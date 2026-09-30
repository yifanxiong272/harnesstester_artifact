import types
from datetime import datetime as real_datetime

import pytest

import gpt_researcher.prompts as prompts
from gpt_researcher.prompts import PromptFamily
from gpt_researcher.utils.enum import ReportType


def _patch_datetime_to_fixed(monkeypatch):
    """Patch prompts.datetime.now(...) to return a fixed timezone-aware datetime.

    Use prompts.timezone.utc (the tzinfo instance) to avoid TypeError.
    """
    fixed_dt = real_datetime(2020, 1, 2, tzinfo=prompts.timezone.utc)
    monkeypatch.setattr(prompts, "datetime", types.SimpleNamespace(now=lambda tz: fixed_dt))


def test_detailed_report_with_context_round_159(monkeypatch):
    _patch_datetime_to_fixed(monkeypatch)

    question = "What is the environmental impact of electric scooters?"
    parent_query = "Urban mobility research"
    report_type = ReportType.DetailedReport.value
    max_iterations = 2
    context = [{"source": "news", "snippet": "e-scooters surge in cities"}]

    result = PromptFamily.generate_search_queries_prompt(
        question, parent_query, report_type, max_iterations, context
    )

    # Basic structure and iteration count
    assert f"Write {max_iterations} google search queries" in result

    # When report_type is DetailedReport, task should combine parent_query and question
    expected_task_fragment = f'"{parent_query} - {question}"'
    assert expected_task_fragment in result

    # Context was provided, so the context prompt should be present and include our context dict
    assert "Context:" in result
    # The list-of-dicts is embedded via f-string; check for key snippets from repr
    assert "'source': 'news'" in result
    assert "'snippet': 'e-scooters surge in cities'" in result

    # dynamic_example should reflect max_iterations = 2
    assert '"query 1", "query 2"' in result

    # Date is patched to a deterministic value (January 02, 2020)
    assert "January 02, 2020" in result


def test_non_detailed_report_no_context_round_159(monkeypatch):
    _patch_datetime_to_fixed(monkeypatch)

    question = "Summarize battery recycling methods"
    parent_query = "SHOULD BE IGNORED"
    # Use a report_type that does not match DetailedReport/SubtopicReport
    report_type = "Summary"

    # Use default max_iterations to verify default dynamic_example (3)
    result = PromptFamily.generate_search_queries_prompt(question, parent_query, report_type)

    # The task should be just the question (not prefixed by parent_query)
    assert f'"{question}"' in result

    # No context was provided, so Context: should not appear
    assert "Context:" not in result

    # dynamic_example default for max_iterations=3
    assert '"query 1", "query 2", "query 3"' in result

    # Date is patched to the same deterministic value
    assert "January 02, 2020" in result
