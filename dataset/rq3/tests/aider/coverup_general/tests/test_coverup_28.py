# file: aider/coders/wholefile_func_coder.py:60-87
# asked: {"lines": [60, 61, 62, 64, 66, 67, 69, 70, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 84, 85, 87], "branches": [[61, 62], [61, 64], [66, 67], [66, 69], [73, 74], [73, 76], [76, 77], [76, 87], [78, 79], [78, 80], [81, 82], [81, 84]]}
# gained: {"lines": [60, 61, 62, 64, 66, 67, 69, 70, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 84, 85, 87], "branches": [[61, 62], [61, 64], [66, 67], [66, 69], [73, 74], [76, 77], [76, 87], [78, 79], [78, 80], [81, 82], [81, 84]]}

import pytest
from types import SimpleNamespace

from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def _make_instance():
    # Create instance without calling __init__ which raises RuntimeError
    return object.__new__(WholeFileFunctionCoder)


def test_render_incremental_returns_partial_and_does_not_call_parse():
    inst = _make_instance()
    inst.partial_response_content = "CACHED_RESPONSE"
    # If parse_partial_args is called, the test should fail
    def _bad_parse():
        pytest.fail("parse_partial_args should not be called when partial_response_content is set")
    inst.parse_partial_args = _bad_parse

    # Should return the cached partial response and not call parse_partial_args
    assert inst.render_incremental_response() == "CACHED_RESPONSE"
    assert inst.render_incremental_response(final=True) == "CACHED_RESPONSE"


def test_render_incremental_returns_none_when_no_args():
    inst = _make_instance()
    inst.partial_response_content = None
    inst.parse_partial_args = lambda: None  # simulate no args available

    # When parse_partial_args returns falsy, render_incremental_response should return None
    assert inst.render_incremental_response() is None


def test_render_incremental_builds_response_and_skips_invalid_entries_final_false():
    inst = _make_instance()
    inst.partial_response_content = None

    explanation = "Planned changes"
    files = [
        {"path": ""},  # missing/falsey path -> skipped
        {"path": "a.py", "content": ""},  # missing/falsey content -> skipped
        {"path": "b.py", "content": "print(1)"},  # should be processed; index 2 of 4 -> this_final True
        {"path": "c.py", "content": "print(2)"},  # last item -> this_final depends on final flag
    ]
    inst.parse_partial_args = lambda: {"explanation": explanation, "files": files}

    calls = []

    def live_diffs(fname, content, final_flag):
        calls.append((fname, content, final_flag))
        return f"DIFF:{fname}:{final_flag}\n"

    inst.live_diffs = live_diffs

    result = inst.render_incremental_response(final=False)

    expected = explanation + "\n\n" + "DIFF:b.py:True\n" + "DIFF:c.py:False\n"
    assert result == expected

    # Ensure live_diffs was called exactly for the two valid file entries in order with correct flags
    assert calls == [
        ("b.py", "print(1)", True),
        ("c.py", "print(2)", False),
    ]


def test_render_incremental_builds_response_and_sets_final_true_for_last_file():
    inst = _make_instance()
    inst.partial_response_content = None

    explanation = "Another plan"
    files = [
        {"path": "only.py", "content": "x = 1"},  # index 0 of 2 -> this_final True because not last? we'll include another to control last
        {"path": "last.py", "content": "y = 2"},
    ]
    inst.parse_partial_args = lambda: {"explanation": explanation, "files": files}

    calls = []

    def live_diffs(fname, content, final_flag):
        calls.append((fname, content, final_flag))
        return f"{fname}|{final_flag}\n"

    inst.live_diffs = live_diffs

    # With final=True, the last file's this_final should be True as well
    result = inst.render_incremental_response(final=True)

    expected = explanation + "\n\n" + "only.py|True\n" + "last.py|True\n"
    assert result == expected

    assert calls == [
        ("only.py", "x = 1", True),
        ("last.py", "y = 2", True),
    ]
