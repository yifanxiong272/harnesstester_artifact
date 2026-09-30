import types
import pytest
import aider.watch as watch


class DummyCoder:
    def __init__(self, abs_fnames=None):
        self.abs_fnames = set(abs_fnames or [])

    def get_rel_fname(self, fname):
        # deterministic rel name for assertions
        return fname.split("/")[-1]


class DummyIO:
    def __init__(self, texts=None):
        self.outputs = []
        self._texts = texts or {}

    def tool_output(self, text=None):
        # capture every call including calls without args
        self.outputs.append(text)

    def read_text(self, fname):
        # return provided mapping or a default non-empty string
        return self._texts.get(fname, "def foo(): pass\n")


class DummyAnalytics:
    def __init__(self):
        self.events = []

    def event(self, name):
        self.events.append(name)


def make_watcher_instance():
    # create a FileWatcher instance without invoking __init__ to control attributes directly
    fw = watch.FileWatcher.__new__(watch.FileWatcher)
    return fw


def test_process_changes_add_file_no_action_round_007():
    """Scenario: a changed file is added, has no AI action; ensure added messages and end-message path executes"""
    fw = make_watcher_instance()

    # prepare coder, io, analytics
    coder = DummyCoder(abs_fnames=set())
    io = DummyIO()
    analytics = DummyAnalytics()

    # single changed file with no action (get_ai_comments returns no action)
    fname = "/project/path/new_file.py"
    fw.changed_files = [fname]

    # inject collaborators
    fw.coder = coder
    fw.io = io
    fw.analytics = analytics

    # get_ai_comments: return (line_nums, comments, action). action is None here
    def get_ai_comments_local(f):
        assert f == fname
        return ([], [], None)

    fw.get_ai_comments = get_ai_comments_local

    # Call method
    res = watch.FileWatcher.process_changes(fw)

    # Expected: when no has_action and something was added, the method returns empty string
    assert res == ""

    # Verify io.tool_output calls: first a call with no args, then an "Added ..." message, then the end message
    # tool_output first call was with no args -> recorded as None
    assert io.outputs[0] is None
    assert io.outputs[1] == "Added new_file.py to the chat"
    assert io.outputs[2] == "End your comment with AI! to request changes or AI? to ask questions"

    # analytics should have been notified of an add
    assert analytics.events == ["ai-comments file-add"]


def test_process_changes_with_action_treecontext_exception_round_007(monkeypatch):
    """Scenario: a changed file contains an AI action '!' and TreeContext construction fails -> fallback formatting used"""
    fw = make_watcher_instance()

    # prepare coder, io, analytics
    coder = DummyCoder(abs_fnames=set())
    # provide a non-empty read_text mapping so code would try to create TreeContext
    io = DummyIO(texts={"/project/path/target.py": "line1\nline2\n"})
    analytics = DummyAnalytics()

    fw.changed_files = ["/project/path/target.py"]
    fw.coder = coder
    fw.io = io
    fw.analytics = analytics

    # Map get_ai_comments to return a single-line comment and an action '!'
    def get_ai_comments_map(f):
        # For both the pass-through during changed_files loop and later in the abs_fnames iteration
        # return one line number and one comment, with action '!' only for the initial discovery
        return ([1], ["please change this"], "!")

    fw.get_ai_comments = get_ai_comments_map

    # Ensure the module prompts are deterministic
    monkeypatch.setattr(watch, "watch_code_prompt", "CODE_PROMPT")
    monkeypatch.setattr(watch, "watch_ask_prompt", "ASK_PROMPT")

    # Force TreeContext to raise ValueError to exercise the fallback loop that formats lines as "  Line {ln}: {comment}\n"
    def raise_value_error(*a, **k):
        raise ValueError("bad context")

    monkeypatch.setattr(watch, "TreeContext", raise_value_error)

    # Execute
    res = watch.FileWatcher.process_changes(fw)

    # The result should start with the code prompt (because action was '!')
    assert res.startswith("CODE_PROMPT")

    # And should contain the relative filename header and the fallback line formatting
    assert "target.py:" in res
    assert "Line 1: please change this" in res

    # io.tool_output should have been called with the "Processing your request..." message
    assert "Processing your request..." in io.outputs

    # analytics should have recorded the execute event
    assert "ai-comments execute" in analytics.events
