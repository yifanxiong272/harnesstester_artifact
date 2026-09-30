import importlib
import sys

import pytest

# Import the module under test
MODULE_PATH = "aider.coders.editblock_coder"


@pytest.fixture(autouse=True)
def reload_module_between_tests():
    # Ensure a fresh import for each test to avoid cross-test pollution
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    yield
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]


def test_main_returns_on_empty_history_round_090(monkeypatch):
    """When Path.read_text returns an empty string, main should return early
    and should not call split_chat_history_markdown.
    """
    m = importlib.import_module(MODULE_PATH)

    # Ensure sys.argv has an entry at index 1 (path passed to Path(...))
    monkeypatch.setattr(sys, "argv", ["prog", "some_path"], raising=False)

    # Patch Path.read_text in the module to return empty content
    monkeypatch.setattr(m.Path, "read_text", lambda self: "")

    # Make split_chat_history_markdown raise if it is invoked (it should not be)
    def _bad_split(*args, **kwargs):
        raise AssertionError("split_chat_history_markdown should not be called when history is empty")

    monkeypatch.setattr(m.utils, "split_chat_history_markdown", _bad_split)

    # Call main - should return None and not raise
    result = m.main()
    assert result is None


def test_main_generates_diff_and_dumps_round_090(monkeypatch):
    """When history contains messages with an edit block, main should compute a
    unified diff and call dump three times: before, after, and diff.
    """
    m = importlib.import_module(MODULE_PATH)

    # Ensure sys.argv has an entry at index 1 (path passed to Path(...))
    monkeypatch.setattr(sys, "argv", ["prog", "some_path"], raising=False)

    # Patch Path.read_text to return a non-empty history markdown string
    monkeypatch.setattr(m.Path, "read_text", lambda self: "some history")

    # Provide a single message with a content key to exercise the loop
    monkeypatch.setattr(
        m.utils,
        "split_chat_history_markdown",
        lambda history: [{"content": "ignored message content"}],
    )

    # Provide a deterministic single edit: (fname, before, after)
    before_text = "line1\nline2\n"
    after_text = "line1\nline2 modified\n"

    monkeypatch.setattr(
        m,
        "find_original_update_blocks",
        lambda content: iter([("some_file.py", before_text, after_text)]),
    )

    # Capture dump calls
    recorded = []

    def _record_dump(x):
        recorded.append(x)

    monkeypatch.setattr(m, "dump", _record_dump)

    # Run main
    result = m.main()
    assert result is None

    # Expect three dump calls: before, after, diff
    assert len(recorded) == 3, f"expected 3 dump calls, got {len(recorded)}"

    # First two dumps should be the before and after texts we supplied
    assert recorded[0] == before_text
    assert recorded[1] == after_text

    # The third dump is the unified diff string. It should include the 'before' and 'after' labels
    diff_text = recorded[2]
    assert isinstance(diff_text, str)
    assert "--- before" in diff_text
    assert "+++ after" not in diff_text  # sanity: there should be '+++ after' but not '+++ after'
    assert "+++ after" in diff_text
    # And there should be at least one hunk header starting with @@
    assert "@@" in diff_text
