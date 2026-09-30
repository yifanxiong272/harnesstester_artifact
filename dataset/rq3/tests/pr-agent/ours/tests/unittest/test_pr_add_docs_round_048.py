import textwrap
import types
import pytest

from pr_agent.tools import pr_add_docs as pr_add_docs_mod
from pr_agent.tools.pr_add_docs import PRAddDocs


class _DummyFile:
    def __init__(self, filename, head_file):
        self.filename = filename
        self.head_file = head_file


class _FakeLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        # record messages for assertions
        self.infos.append(msg)


class _FakeSettings:
    def __init__(self, verbosity_level):
        self.config = types.SimpleNamespace(verbosity_level=verbosity_level)


class _FakeGitProvider:
    def __init__(self, diff_files=None, get_diff_raises=False):
        # diff_files: list or None
        self.diff_files = diff_files
        self._raise = get_diff_raises

    def get_diff_files(self):
        if self._raise:
            raise RuntimeError("get_diff_files failed")
        return self.diff_files


def _make_instance_with_provider(gp):
    # create PRAddDocs instance without calling its real constructor
    inst = object.__new__(PRAddDocs)
    inst.git_provider = gp
    return inst


def test_dedent_indent_after_round_048(monkeypatch):
    """
    Case: matching file found, doc_placement='after', add_original_line=False,
    delta_spaces > 0 so indent should be applied.
    """
    # head_file has two lines: index 0 (original_initial_line) and index 1 (line used for spaces)
    head = "def func():\n    inner_line = 1\n"
    f = _DummyFile("path/to/file.py", head)
    gp = _FakeGitProvider(diff_files=[f])
    inst = _make_instance_with_provider(gp)

    new_code = "inner_line = 2\n"

    # call
    out = PRAddDocs.dedent_code(inst, "path/to/file.py", 1, new_code, doc_placement='after', add_original_line=False)

    # expected: indent added (4 spaces) and trailing newline stripped by rstrip in method
    assert out == "    inner_line = 2"


def test_dedent_add_original_after_round_048(monkeypatch):
    """
    Case: matching file, doc_placement='after', add_original_line=True,
    verify original line is prefixed and indentation applied.
    """
    head = "def func():\n    inner_line = 1\n"
    f = _DummyFile("src/file.py", head)
    gp = _FakeGitProvider(diff_files=[f])
    inst = _make_instance_with_provider(gp)

    new_code = "inner_line = 2\n"

    out = PRAddDocs.dedent_code(inst, "src/file.py", 1, new_code, doc_placement='after', add_original_line=True)

    # original_initial_line + '\n' + indented snippet
    assert out == "def func():\n    inner_line = 2"


def test_dedent_before_add_original_round_048(monkeypatch):
    """
    Case: matching file, doc_placement='before', add_original_line=True,
    and suggested code has more leading spaces (so delta_spaces <= 0) -> no indent applied,
    and original line appended after the suggested snippet.
    """
    # original initial line will be index 0; use a suggestion with leading spaces
    head = "def func():\n    inner_line = 1\n"
    f = _DummyFile("lib/mod.py", head)
    gp = _FakeGitProvider(diff_files=[f])
    inst = _make_instance_with_provider(gp)

    # suggested code has 4 leading spaces already
    new_code = "    added_inner = 99\n"

    out = PRAddDocs.dedent_code(inst, "lib/mod.py", 1, new_code, doc_placement='before', add_original_line=True)

    # since doc_placement == 'before', expected: suggestion.rstrip() + '\n' + original_initial_line
    assert out == "    added_inner = 99\ndef func():"


def test_no_matching_file_returns_same_round_048(monkeypatch):
    """
    If no file in diff_files matches relevant_file, function should return the original new_code_snippet unchanged.
    """
    head = "some: content\nmore: content\n"
    f = _DummyFile("other/file.py", head)
    gp = _FakeGitProvider(diff_files=[f])
    inst = _make_instance_with_provider(gp)

    new_code = "x = 1\n"

    out = PRAddDocs.dedent_code(inst, "not_found.py", 1, new_code, doc_placement='after', add_original_line=False)

    assert out == new_code


def test_exception_logs_round_048(monkeypatch):
    """
    If an exception occurs during dedent_code, and verbosity_level >= 2,
    the logger.info should be called and the original snippet returned unchanged.
    """
    # create a git provider whose get_diff_files raises
    gp = _FakeGitProvider(diff_files=None, get_diff_raises=True)
    inst = _make_instance_with_provider(gp)

    # patch get_settings and get_logger in the module to control behavior
    dummy_logger = _FakeLogger()
    monkeypatch.setattr(pr_add_docs_mod, "get_logger", lambda: dummy_logger)
    monkeypatch.setattr(pr_add_docs_mod, "get_settings", lambda: _FakeSettings(verbosity_level=2))

    new_code = "should_stay_same\n"

    out = PRAddDocs.dedent_code(inst, "anyfile.py", 1, new_code, doc_placement='after', add_original_line=False)

    # returns unchanged snippet
    assert out == new_code

    # logger.info should have been called with a message mentioning the filename
    assert any("anyfile.py" in m for m in dummy_logger.infos), "logger.info was not called with filename"
