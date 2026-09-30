import pytest

from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def _new_coder_instance():
    # Bypass __init__ which is deprecated and raises; tests should set needed attributes manually.
    return object.__new__(WholeFileFunctionCoder)


def test_partial_response_content_round_040():
    # If partial_response_content is present, it should be returned immediately
    c = _new_coder_instance()
    c.partial_response_content = "CACHED_RESPONSE"

    # Ensure parse_partial_args is not called by setting a callable that would fail if invoked
    def _fail_parse():
        raise AssertionError("parse_partial_args should not be called when partial_response_content is set")

    c.parse_partial_args = _fail_parse

    out = c.render_incremental_response()
    assert out == "CACHED_RESPONSE"


def test_no_args_round_040():
    # If parse_partial_args returns a falsy value (empty dict), render_incremental_response should return None
    c = _new_coder_instance()
    c.partial_response_content = None
    c.parse_partial_args = lambda: {}

    # live_diffs should not be required for this path, but provide a harmless stub if called
    c.live_diffs = lambda *a, **k: "SHOULD_NOT_BE_CALLED"

    out = c.render_incremental_response()
    assert out is None


def test_files_and_explanation_final_false_round_040():
    # Verify explanation prefix and file processing, including skipping entries without path or content,
    # and that this_final logic sets True for non-last items even when final=False
    c = _new_coder_instance()
    c.partial_response_content = None

    files = [
        {"path": None, "content": "x"},       # should be skipped (no path)
        {"path": "p1", "content": None},     # should be skipped (no content)
        {"path": "p2", "content": "c2"},
        {"path": "p3", "content": "c3"},
    ]

    c.parse_partial_args = lambda: {"explanation": "Expl", "files": files}

    calls = []

    def fake_live_diffs(path, content, this_final):
        # record calls and return a deterministic snippet
        calls.append((path, content, this_final))
        return f"D:{path}:{content}:{this_final}\n"

    c.live_diffs = fake_live_diffs

    out = c.render_incremental_response(final=False)

    # Explanation followed by diffs for p2 and p3. For p2 (index 2 of 4) this_final is True because i < len(files)-1.
    expected = "Expl\n\n" + "D:p2:c2:True\n" + "D:p3:c3:False\n"
    assert out == expected

    # Validate that only p2 and p3 were passed through, with correct final flags
    assert calls == [("p2", "c2", True), ("p3", "c3", False)]


def test_files_and_explanation_final_true_round_040():
    # Same as previous test but final=True: last item should be marked True
    c = _new_coder_instance()
    c.partial_response_content = None

    files = [
        {"path": "a", "content": "A"},
        {"path": "b", "content": "B"},
    ]

    c.parse_partial_args = lambda: {"explanation": "E2", "files": files}

    calls = []

    def fake_live_diffs2(path, content, this_final):
        calls.append((path, content, this_final))
        return f"X:{path}:{content}:{this_final}\n"

    c.live_diffs = fake_live_diffs2

    out = c.render_incremental_response(final=True)

    # Both items should be True: first because i < len(files)-1, second because final=True
    expected = "E2\n\n" + "X:a:A:True\n" + "X:b:B:True\n"
    assert out == expected
    assert calls == [("a", "A", True), ("b", "B", True)]
