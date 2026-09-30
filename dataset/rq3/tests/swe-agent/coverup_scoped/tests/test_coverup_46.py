# file: sweagent/utils/patch_formatter.py:27-49
# asked: {"lines": [35, 36, 46], "branches": [[34, 35], [41, 46]]}
# gained: {"lines": [35, 36, 46], "branches": [[34, 35], [41, 46]]}

import pytest
from sweagent.utils.patch_formatter import PatchFormatter


def test_merge_intervals_empty_both_returns_empty():
    # When both starts and stops are empty, should return two empty lists.
    starts, stops = [], []
    merged_starts, merged_stops = PatchFormatter._merge_intervals(starts, stops)
    assert merged_starts == []
    assert merged_stops == []


def test_merge_intervals_empty_starts_with_nonempty_stops_raises_assertion():
    # When starts is empty but stops is non-empty, the function asserts.
    with pytest.raises(AssertionError):
        PatchFormatter._merge_intervals([], [1])


def test_merge_intervals_merges_overlaps_and_keeps_nonoverlapping():
    # Use unsorted input to also exercise the sorting step.
    starts = [5, 1, 18]
    stops = [13, 10, 20]
    # Expected behavior (after sorting by start):
    # intervals = (1,10), (5,13), (18,20)
    # Merge (1,10) and (5,13) -> (1,13); (18,20) is separate.
    expected_starts = [1, 18]
    expected_stops = [13, 20]

    merged_starts, merged_stops = PatchFormatter._merge_intervals(starts, stops)
    assert merged_starts == expected_starts
    assert merged_stops == expected_stops
