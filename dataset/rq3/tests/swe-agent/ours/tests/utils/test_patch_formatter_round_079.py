import pytest

from sweagent.utils.patch_formatter import PatchFormatter


def test_merge_empty_round_079():
    """When both starts and stops are empty, return two empty lists."""
    starts, stops = [], []
    merged_starts, merged_stops = PatchFormatter._merge_intervals(starts, stops)
    assert merged_starts == []
    assert merged_stops == []


def test_merge_empty_stops_raises_assertion_round_079():
    """If starts is empty but stops is non-empty, the function asserts.

    This covers the branch where `if not starts:` leads to an assertion that
    `stops` must also be empty.
    """
    with pytest.raises(AssertionError):
        PatchFormatter._merge_intervals([], [1])


def test_merge_overlapping_and_adjacent_intervals_round_079():
    """Covers overlapping merging and ensures correct merged intervals.

    Uses inputs from the docstring and an adjacent-equals case to force the
    else-branch where intervals are merged.
    """
    # Example from the docstring: overlapping intervals
    starts = [1, 5, 18]
    stops = [10, 13, 20]
    ms, mt = PatchFormatter._merge_intervals(starts, stops)
    assert ms == [1, 18]
    assert mt == [13, 20]

    # Adjacent-equals case: previous stop == next start should merge (because
    # the code uses '<' to detect non-overlap). This ensures the 'else' branch
    # that updates merged[-1][1] = max(...) is executed.
    starts2 = [1, 5]
    stops2 = [5, 8]
    ms2, mt2 = PatchFormatter._merge_intervals(starts2, stops2)
    assert ms2 == [1]
    assert mt2 == [8]
