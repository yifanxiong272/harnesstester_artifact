import pytest

from backend.report_type.detailed_report.detailed_report import DetailedReport


class _FakeSubtopic:
    def __init__(self, task):
        # keep as attribute access, matching the code under test
        self.task = task


class _FakeResearcherWithSubtopics:
    def __init__(self, subtopics):
        self._subtopics = subtopics

    async def get_subtopics(self):
        # async method to match the real contract
        return type("SubtopicsData", (), {"subtopics": self._subtopics})()


class _FakeResearcherReturningNone:
    async def get_subtopics(self):
        # explicit None return to exercise the else branch and printed message
        return None


@pytest.mark.asyncio
async def test_get_all_subtopics_with_items_round_121():
    """
    - Arrange: create a DetailedReport instance without running __init__ and attach a fake researcher
      whose get_subtopics returns an object with a truthy .subtopics iterable of objects that have .task.
    - Act: call the async _get_all_subtopics method.
    - Assert: the returned list contains dicts with the 'task' values in order.
    """
    # create instance without invoking potentially heavy __init__
    dr = DetailedReport.__new__(DetailedReport)

    # attach fake researcher that returns two subtopics
    subtopics = [_FakeSubtopic("alpha"), _FakeSubtopic("beta")]
    dr.gpt_researcher = _FakeResearcherWithSubtopics(subtopics)

    result = await dr._get_all_subtopics()

    assert isinstance(result, list)
    # should preserve order and produce dicts with 'task' keys
    assert result == [{"task": "alpha"}, {"task": "beta"}]


@pytest.mark.asyncio
async def test_get_all_subtopics_none_round_121(capsys):
    """
    - Arrange: attach a fake researcher whose get_subtopics returns None.
    - Act: call _get_all_subtopics and capture stdout.
    - Assert: result is an empty list and the printed message mentions the unexpected format.
    """
    dr = DetailedReport.__new__(DetailedReport)
    dr.gpt_researcher = _FakeResearcherReturningNone()

    result = await dr._get_all_subtopics()

    # function should return an empty list when subtopics data is missing
    assert result == []

    # capture printed output from the else branch
    captured = capsys.readouterr()
    assert "Unexpected subtopics data format" in captured.out
    # should include the string representation of the None value
    assert "None" in captured.out
