import os
from types import SimpleNamespace
import importlib

import pytest

import aider.watch as watch
from aider.watch import FileWatcher


class DummyIO:
    def __init__(self, file_contents=None):
        self.file_contents = file_contents or {}
        self.outputs = []

    def tool_output(self, msg=None):
        # store the exact message (None if no arg)
        self.outputs.append(msg)

    def read_text(self, fname, silent=False):
        # return stored content or empty string
        return self.file_contents.get(fname, "")


class DummyCoder:
    def __init__(self, root="/root", file_contents=None):
        self.root = root
        self.io = DummyIO(file_contents=file_contents)
        # files currently tracked by AI (absolute paths)
        self.abs_fnames = set()

    def get_rel_fname(self, fname):
        return os.path.basename(fname)


class DummyAnalytics:
    def __init__(self):
        self.events = []

    def event(self, name):
        self.events.append(name)


def _make_watcher(coder=None, analytics=None):
    coder = coder or DummyCoder()
    watcher = FileWatcher(coder, gitignores=None, verbose=False, analytics=analytics, root=None)
    return watcher


def test_no_action_add_file_round_007():
    """When a changed file contains no AI comments we add it and return empty string.

    This covers the branch that adds files, calls analytics event for file-add,
    outputs the "Added ..." message and the guidance message, and returns "".
    """
    coder = DummyCoder(root="/project", file_contents={})
    analytics = DummyAnalytics()
    watcher = _make_watcher(coder=coder, analytics=analytics)

    # Simulate one changed file (absolute path)
    fname = "/project/a.py"
    watcher.changed_files = {fname}

    # Ensure get_ai_comments returns (None, None, None) meaning no AI comments
    watcher.get_ai_comments = lambda f: (None, None, None)

    res = watcher.process_changes()

    # No action -> empty string returned
    assert res == ""

    # The file should have been added to coder.abs_fnames
    assert fname in coder.abs_fnames

    # tool_output called at least three times: initial, Added ..., guidance
    outputs = coder.io.outputs
    assert len(outputs) >= 3
    # The Added message should be present and use the coder.get_rel_fname() value
    assert outputs[1] == f"Added {coder.get_rel_fname(fname)} to the chat"
    # Guidance message when added but no action
    assert "End your comment with AI! to request changes or AI? to ask questions" in outputs[2]

    # Analytics should have recorded the file-add event
    assert "ai-comments file-add" in analytics.events


def test_process_changes_valueerror_path_round_007():
    """When TreeContext raises ValueError we fallback to per-line formatting.

    This tests the branch that handles ValueError from TreeContext and appends
    '  Line N: comment' lines to the prompt. Also verifies the execute analytics
    event and that we use the code prompt for '!' actions.
    """
    coder = DummyCoder(root="/project", file_contents={"/project/changed.txt": "line1\nline2"})
    analytics = DummyAnalytics()
    watcher = _make_watcher(coder=coder, analytics=analytics)

    # Prepare module-level prompts and a TreeContext that raises ValueError
    orig_code_prompt = getattr(watch, "watch_code_prompt", None)
    orig_treecontext = getattr(watch, "TreeContext", None)
    watch.watch_code_prompt = "PROMPT_CODE"

    class RaisingTreeContext:
        def __init__(self, *args, **kwargs):
            raise ValueError("bad context")

    watch.TreeContext = RaisingTreeContext

    try:
        fname = "/project/changed.txt"
        watcher.changed_files = {fname}

        # get_ai_comments: first call (when scanning changed_files) returns an action '!'
        # second call (when refreshing from abs_fnames) returns a line/comment pair
        call_counts = {}

        def _get_ai_comments(fp):
            call_counts[fp] = call_counts.get(fp, 0) + 1
            if call_counts[fp] == 1:
                # first time: mark action so processing continues
                return (None, None, "!")
            # second time: return actual line numbers and comments to be included
            return ([2], ["# ai! do this"], "!")

        watcher.get_ai_comments = _get_ai_comments

        # io.read_text should return something so the code path continues to context handling
        coder.io.file_contents[fname] = "print('hello')\n# ai! do this\n"

        res = watcher.process_changes()

        # Should start with the code prompt and include the human-readable fallback line
        assert "PROMPT_CODE" in res
        assert "changed.txt:" in res
        assert "Line 2: # ai! do this" in res

        # analytics execute event should be recorded
        assert "ai-comments execute" in analytics.events

        # Should have announced processing
        assert any(o == "Processing your request..." for o in coder.io.outputs)

    finally:
        # restore patched module attributes
        if orig_code_prompt is None:
            delattr(watch, "watch_code_prompt")
        else:
            watch.watch_code_prompt = orig_code_prompt
        watch.TreeContext = orig_treecontext


def test_process_changes_treecontext_success_round_007():
    """When TreeContext succeeds we include its formatted text in the result.

    This tests the successful try branch where context.format() is appended to
    the assembled prompt, and ensures the ask prompt is used for '?' actions.
    """
    coder = DummyCoder(root="/project", file_contents={"/project/track.py": "x\n# ai? question\n"})
    analytics = DummyAnalytics()
    watcher = _make_watcher(coder=coder, analytics=analytics)

    # Patch the ask prompt and provide a TreeContext stub that records calls
    orig_ask_prompt = getattr(watch, "watch_ask_prompt", None)
    orig_treecontext = getattr(watch, "TreeContext", None)
    watch.watch_ask_prompt = "PROMPT_ASK"

    class FakeTreeContext:
        def __init__(self, rel_fname, code, **kwargs):
            # store for inspection
            self.rel_fname = rel_fname
            self.code = code
            self._lois = None
            self.lines_of_interest = set()

        def add_lines_of_interest(self, lois):
            self._lois = list(lois)

        def add_context(self):
            # pretend to do work
            pass

        def format(self):
            return "FORMATTED_CONTEXT"

    watch.TreeContext = FakeTreeContext

    try:
        fname = "/project/track.py"
        watcher.changed_files = {fname}

        # Similar two-phase get_ai_comments: first call sets action '?', second returns lines/comments
        call_counts = {}

        def _get_ai_comments(fp):
            call_counts[fp] = call_counts.get(fp, 0) + 1
            if call_counts[fp] == 1:
                return (None, None, "?")
            return ([1], ["# ai? question"], "?")

        watcher.get_ai_comments = _get_ai_comments

        # Ensure read_text returns the code so TreeContext is constructed
        coder.io.file_contents[fname] = "def f():\n    pass\n# ai? question\n"

        res = watcher.process_changes()

        # Uses the ask prompt
        assert "PROMPT_ASK" in res
        assert "track.py:" in res
        # The formatted context should be appended from FakeTreeContext.format()
        assert "FORMATTED_CONTEXT" in res

        # analytics execute event should be recorded
        assert "ai-comments execute" in analytics.events

    finally:
        if orig_ask_prompt is None:
            delattr(watch, "watch_ask_prompt")
        else:
            watch.watch_ask_prompt = orig_ask_prompt
        watch.TreeContext = orig_treecontext
