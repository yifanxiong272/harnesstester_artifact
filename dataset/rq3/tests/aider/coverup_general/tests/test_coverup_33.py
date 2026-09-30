# file: aider/coders/udiff_coder.py:282-309
# asked: {"lines": [283, 284, 286, 289, 290, 292, 293, 294, 296, 297, 298, 300, 301, 303, 305, 307, 308, 309], "branches": [[289, 0], [289, 290], [292, 289], [292, 293], [293, 294], [293, 296], [297, 298], [297, 300], [300, 301], [300, 303], [308, 292], [308, 309]]}
# gained: {"lines": [283, 284, 286, 289, 290, 292, 293, 294, 296, 297, 298, 300, 301, 303, 305, 307, 308, 309], "branches": [[289, 0], [289, 290], [292, 289], [292, 293], [293, 294], [293, 296], [297, 298], [297, 300], [300, 301], [300, 303], [308, 292], [308, 309]]}

import pytest

from aider.coders import udiff_coder


def test_apply_partial_hunk_returns_on_matching_combination(monkeypatch):
    # Prepare contexts such that multiple branches in apply_partial_hunk are exercised:
    # preceding_context has two items, following_context has two items, so use_all = 4
    content = "file-content"
    preceding_context = ["A", "B"]
    changes = ["X"]
    following_context = ["C", "D"]

    calls = []

    # Stub directly_apply_hunk to return None for all calls except when the hunk matches
    # the specific combination we expect: ['B', 'X', 'C'] (use_prec=1, use_foll=1).
    def fake_directly_apply_hunk(got_content, got_hunk):
        # Record the calls for assertions
        calls.append((got_content, list(got_hunk)))
        if list(got_hunk) == ["B", "X", "C"]:
            return "MATCHED"
        return None

    monkeypatch.setattr(udiff_coder, "directly_apply_hunk", fake_directly_apply_hunk)

    res = udiff_coder.apply_partial_hunk(content, preceding_context, changes, following_context)

    # Verify we returned the expected sentinel and that the stub was called
    assert res == "MATCHED"
    assert len(calls) > 0
    # Ensure that at least one call had the expected hunk
    assert any(hunk == ["B", "X", "C"] for _, hunk in calls)


def test_apply_partial_hunk_exhausts_all_options_and_returns_none(monkeypatch):
    # Use slightly different contexts to ensure loops still run through multiple iterations
    content = "another-file"
    preceding_context = ["p1", "p2"]
    changes = ["chg"]
    following_context = ["f1", "f2"]

    call_count = {"n": 0}

    # Stub that always returns falsy so apply_partial_hunk must try all combinations
    def always_none(got_content, got_hunk):
        call_count["n"] += 1
        # return None (falsy)
        return None

    monkeypatch.setattr(udiff_coder, "directly_apply_hunk", always_none)

    res = udiff_coder.apply_partial_hunk(content, preceding_context, changes, following_context)

    # Should have fully exhausted options and returned None
    assert res is None
    # Ensure that at least one invocation happened
    assert call_count["n"] > 0
