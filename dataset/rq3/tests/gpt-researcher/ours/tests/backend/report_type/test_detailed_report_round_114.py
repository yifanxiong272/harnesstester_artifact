import asyncio
import types
from backend.report_type.detailed_report.detailed_report import DetailedReport


def test_generate_subtopic_reports_empty_round_114():
    """When given an empty subtopics list, the method returns an empty list and empty body."""
    # Bypass __init__ to avoid heavy setup; the method does not use other instance state for empty input
    inst = object.__new__(DetailedReport)

    result = asyncio.run(inst._generate_subtopic_reports([]))

    assert isinstance(result, tuple) and len(result) == 2
    subtopic_reports, subtopics_report_body = result
    assert subtopic_reports == []
    assert subtopics_report_body == ""


def test_generate_subtopic_reports_mixed_round_114():
    """Covers branches where individual _get_subtopic_report results have falsy and truthy 'report' values.

    We bind a deterministic async helper to the instance to avoid any external calls.
    """
    inst = object.__new__(DetailedReport)

    async def fake_get_subtopic_report(self, subtopic):
        # Deterministic behavior driven by subtopic['id']
        sid = subtopic.get("id")
        if sid == 1:
            return {"report": ""}  # falsy -> should NOT be appended
        if sid == 2:
            return {"report": "Report Two"}  # truthy -> should be appended
        if sid == 3:
            return {"report": "Report Three"}  # truthy -> should be appended
        return {"report": None}  # falsy

    # Bind the coroutine as a method on the instance so calls use the instance correctly
    inst._get_subtopic_report = types.MethodType(fake_get_subtopic_report, inst)

    subtopics = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]

    subtopic_reports, subtopics_report_body = asyncio.run(inst._generate_subtopic_reports(subtopics))

    # Only id 2 and 3 should have been appended
    assert isinstance(subtopic_reports, list)
    assert len(subtopic_reports) == 2
    assert [r["report"] for r in subtopic_reports] == ["Report Two", "Report Three"]

    # Body should concatenate the two reports each preceded by three newlines
    assert subtopics_report_body == "\n\n\nReport Two\n\n\nReport Three"
