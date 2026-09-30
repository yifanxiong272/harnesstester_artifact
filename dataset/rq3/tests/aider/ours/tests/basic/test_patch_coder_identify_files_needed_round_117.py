import pytest
from aider.coders import patch_coder as pc


def test_identify_files_update_and_delete_round_117(monkeypatch):
    """Lines with Update and Delete should be returned (order not important)."""
    # Patch _norm to a deterministic identity function for this test
    monkeypatch.setattr(pc, "_norm", lambda s: s)

    text = (
        "*** Update File: src/foo.py\n"
        "some other line\n"
        "*** Delete File: tests/bar.py\n"
    )

    result = pc.identify_files_needed(text)
    assert isinstance(result, list)
    assert set(result) == {"src/foo.py", "tests/bar.py"}


def test_identify_files_handles_duplicates_and_whitespace_round_117(monkeypatch):
    """Duplicate entries and surrounding whitespace should produce unique normalized paths."""
    # Simulate a normalizer that strips surrounding whitespace
    monkeypatch.setattr(pc, "_norm", lambda s: s.strip())

    text = (
        "   *** Update File: a.txt   \n"
        "*** Update File: a.txt\n"
        "*** Delete File:  b.txt  \n"
        "irrelevant\n"
    )

    result = pc.identify_files_needed(text)
    # set equality to be robust to ordering from set->list conversion
    assert set(result) == {"a.txt", "b.txt"}


def test_identify_files_no_actions_round_117(monkeypatch):
    """When no Update/Delete lines are present, an empty list is returned."""
    # Ensure normalization is deterministic but doesn't introduce action prefixes
    monkeypatch.setattr(pc, "_norm", lambda s: s)

    text = "This has no action lines\nJust plain text\n"
    result = pc.identify_files_needed(text)
    assert result == []
