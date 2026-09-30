# file: openhands/resolver/patching/patch.py:770-847
# asked: {"lines": [771, 773, 774, 775, 777, 778, 780, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 793, 794, 796, 797, 799, 800, 801, 802, 803, 804, 805, 806, 807, 809, 810, 811, 812, 813, 814, 815, 816, 817, 821, 822, 823, 824, 825, 826, 829, 830, 831, 832, 833, 834, 835, 836, 837, 840, 842, 844, 845, 847], "branches": [[784, 785], [784, 844], [785, 786], [785, 787], [789, 784], [789, 790], [793, 794], [793, 796], [800, 801], [800, 809], [802, 803], [802, 807], [809, 789], [809, 810], [811, 812], [811, 831], [813, 814], [813, 821], [831, 832], [831, 842], [844, 845], [844, 847]]}
# gained: {"lines": [771, 773, 774, 775, 777, 778, 780, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 793, 794, 796, 797, 799, 800, 801, 802, 803, 804, 805, 806, 807, 809, 810, 811, 812, 813, 814, 815, 816, 817, 821, 822, 823, 824, 825, 826, 829, 830, 831, 832, 833, 834, 835, 836, 837, 840, 842, 844, 845, 847], "branches": [[784, 785], [784, 844], [785, 786], [785, 787], [789, 784], [789, 790], [793, 794], [793, 796], [800, 801], [800, 809], [802, 803], [802, 807], [809, 789], [809, 810], [811, 812], [811, 831], [813, 814], [813, 821], [831, 832], [831, 842], [844, 845], [844, 847]]}

import pytest

from openhands.resolver.patching.patch import parse_ed_diff, Change


def test_parse_ed_diff_delete_single_hunk():
    # Single delete hunk as list input
    lines = ["1d"]
    changes = parse_ed_diff(lines)
    assert changes is not None
    assert isinstance(changes, list)
    # Expect one deletion Change with old=1, new and line are None, hunk index 0
    assert changes == [Change(1, None, None, 0)]


def test_parse_ed_diff_change_hunk_multiple_deletions():
    # Change hunk with old range 2..3, one new line, and end marker '.'
    lines = ["2,3c", "newX", "."]
    changes = parse_ed_diff(lines)
    assert changes is not None
    # Expect two deletions (old 2 and 3) followed by the insertion Change with the new line
    expected = [
        Change(2, None, None, 0),
        Change(3, None, None, 0),
        Change(None, 2, "newX", 0),
    ]
    assert changes == expected


def test_parse_ed_diff_add_hunk_with_string_input():
    # Add hunk provided as a single string (exercise str -> splitlines path)
    text = "4a\nadded1\n."
    changes = parse_ed_diff(text)
    assert changes is not None
    # For an add at old=4 with no prior deletions, new index should be old - r + i + 1 = 4 - 0 + 0 + 1 = 5
    assert changes == [Change(None, 5, "added1", 0)]


def test_parse_ed_diff_no_matches_returns_none():
    # Input with no ed hunk headers should return None
    lines = ["just some text", "no diffs here"]
    changes = parse_ed_diff(lines)
    assert changes is None
