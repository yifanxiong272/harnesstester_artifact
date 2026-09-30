# file: aider/coders/editblock_coder.py:631-653
# asked: {"lines": [632, 633, 634, 636, 638, 639, 640, 642, 644, 645, 646, 647, 648, 650, 651, 652, 653], "branches": [[633, 634], [633, 636], [638, 0], [638, 639], [642, 638], [642, 644]]}
# gained: {"lines": [632, 633, 634, 636, 638, 639, 640, 642, 644, 645, 646, 647, 648, 650, 651, 652, 653], "branches": [[633, 634], [633, 636], [638, 0], [638, 639], [642, 638], [642, 644]]}

import importlib
import sys
from pathlib import Path

import pytest


def _reload_module():
    # Import and reload to ensure tests run against the current module object
    import aider.coders.editblock_coder as mod

    importlib.reload(mod)
    return mod


def test_main_returns_early_on_empty_history(monkeypatch):
    mod = _reload_module()

    # Make Path.read_text return empty string
    monkeypatch.setattr(Path, "read_text", lambda self: "")

    # Ensure dump is not called; make it raise if called
    def _bad_dump(*a, **k):
        raise AssertionError("dump should not be called for empty history")

    monkeypatch.setattr(mod, "dump", _bad_dump)

    # Provide argv with a dummy path
    monkeypatch.setattr(sys, "argv", ["prog", "dummy_path"])

    # Should not raise and should return None / exit normally
    result = mod.main()
    assert result is None


def test_main_processes_edits_and_dumps_diff(monkeypatch):
    mod = _reload_module()

    # Provide non-empty history content
    history_content = "some history content"
    monkeypatch.setattr(Path, "read_text", lambda self: history_content)

    # Make split_chat_history_markdown return one message with 'content'
    monkeypatch.setattr(
        mod.utils,
        "split_chat_history_markdown",
        lambda md: [{"content": "message content"}],
    )

    # Prepare before/after strings that will produce a small diff
    before = "line1\nline2\n"
    after = "line1\nline2_changed\n"

    # Stub find_original_update_blocks to yield one edit tuple
    monkeypatch.setattr(
        mod,
        "find_original_update_blocks",
        lambda msg: iter([("somefile.py", before, after)]),
        raising=False,
    )

    # Capture dump calls
    dumped = []

    def _capture_dump(arg):
        dumped.append(arg)

    monkeypatch.setattr(mod, "dump", _capture_dump)

    # Set argv
    monkeypatch.setattr(sys, "argv", ["prog", "dummy_path"])

    # Run main
    result = mod.main()
    assert result is None

    # Verify dump was called three times: before, after, diff
    assert len(dumped) == 3
    assert dumped[0] == before
    assert dumped[1] == after

    diff_text = dumped[2]
    # Diff should mention the from/to filenames used in unified_diff
    assert "--- before" in diff_text
    assert "+++ after" in diff_text
    # And the changed line should appear in the diff
    assert "line2_changed" in diff_text
