import types
from types import SimpleNamespace
import builtins
import os

import pytest

import openhands.runtime.utils.edit as edit

# Create deterministic dummy observation/objects and patch module-level symbols
class DummyErrorObservation:
    def __init__(self, content):
        self.content = content
        self.llm_metrics = None

class DummyFileWriteObservation:
    def __init__(self):
        # minimal attributes; tests use isinstance checks via patched symbol
        pass

class DummyFileReadObservation:
    def __init__(self, content):
        self.content = content

class DummyFileEditObservation:
    def __init__(self, content=None, path=None, prev_exist=None, old_content=None, new_content=None):
        self.content = content
        self.path = path
        self.prev_exist = prev_exist
        self.old_content = old_content
        self.new_content = new_content
        self.llm_metrics = None

# Patch type symbols in the module so isinstance checks work with our dummy classes
edit.ErrorObservation = DummyErrorObservation
edit.FileWriteObservation = DummyFileWriteObservation
edit.FileReadObservation = DummyFileReadObservation
edit.FileEditObservation = DummyFileEditObservation

# Patch get_diff to return a deterministic diff string
def fake_get_diff(a, b, p):
    return f"DIFF({a!r}->{b!r}@{p})"

edit.get_diff = fake_get_diff

# Helper Fake runtime that uses the mixin under test
class FakeRuntime(edit.FileEditRuntimeMixin):
    def __init__(self):
        # minimal config / attributes used by llm_based_edit
        self.config = SimpleNamespace(sandbox=SimpleNamespace(enable_auto_lint=True))
        self.MAX_LINES_TO_EDIT = 5
        # draft editor llm with metrics attr
        self.draft_editor_llm = SimpleNamespace(metrics={})
        # default behavior hooks that tests will override
        self._read_ret = None
        self._write_ret = None
        self._validate_ret = None
        self._lint_ret = None
        self._new_contents_ret = None
        self._write_calls = []

    # The mixin expects .read(action) and .write(action)
    def read(self, action):
        return self._read_ret

    def write(self, action):
        # record what is written for assertions
        # Use getattr to extract 'content' if present on the action object
        content = getattr(action, 'content', action)
        self._write_calls.append(content)
        return self._write_ret

    def _validate_range(self, start, end, total_lines):
        return self._validate_ret

    def _get_lint_error(self, suffix, old_content, new_content, filepath, diff):
        return self._lint_ret

    def correct_edit(self, file_content, error_obs, retry_num):
        # return a FileEditObservation-like object to indicate correction was performed
        return DummyFileEditObservation(content="CORRECTED", path="corrected", prev_exist=True, old_content="<old>", new_content=file_content)

    # Implement abstract method required by the interface
    def run_ipython(self, action):
        # minimal no-op implementation to satisfy abstract contract
        return None


def make_action(path="/tmp/x.py", content="new", start=1, end=1):
    return SimpleNamespace(path=path, content=content, start=start, end=end)


def test_llm_based_edit_create_file_then_write_success_round_003():
    """When read reports 'file not found', a write that returns a FileWriteObservation
    should produce a FileEditObservation with prev_exist=False and correct new_content.
    """
    rt = FakeRuntime()
    # read returns an ErrorObservation containing 'File not found' (case-insensitive)
    rt._read_ret = DummyErrorObservation("File not found: something")
    # write will succeed (FileWriteObservation)
    rt._write_ret = DummyFileWriteObservation()

    action = make_action(path="some_file.py", content="print(1)\n")

    res = rt.llm_based_edit(action)

    # Should be our DummyFileEditObservation created by the code path
    assert isinstance(res, DummyFileEditObservation)
    assert res.prev_exist is False
    assert res.old_content == ''
    assert res.new_content == action.content
    # content should come from the patched get_diff
    assert res.content == fake_get_diff('', action.content, action.path)


def test_llm_based_edit_create_file_write_error_round_003():
    """If write fails after a 'file not found' read, the original error observation is returned.
    """
    rt = FakeRuntime()
    err = DummyErrorObservation("File not found: no create")
    rt._read_ret = err
    # write returns an ErrorObservation -> should be returned immediately
    rt._write_ret = DummyErrorObservation("failed to write")

    action = make_action(path="other.py", content="x = 1\n")
    res = rt.llm_based_edit(action)

    # Should return the ErrorObservation from write
    assert isinstance(res, DummyErrorObservation)
    assert res.content == "failed to write"


def test_llm_based_edit_range_validation_error_round_003():
    """If _validate_range returns an ErrorObservation, llm_based_edit should return it.
    Covers the branch where read returns FileReadObservation and validation fails.
    """
    rt = FakeRuntime()
    # read returns existing content
    rt._read_ret = DummyFileReadObservation("a\nb\nc\n")
    # validation indicates an error
    rt._validate_ret = DummyErrorObservation("Invalid range")

    action = make_action(path="p.py", content="irrelevant", start=2, end=100)
    res = rt.llm_based_edit(action)

    assert isinstance(res, DummyErrorObservation)
    assert res.content == "Invalid range"


def test_llm_based_edit_append_with_auto_lint_error_triggers_correct_edit_round_003():
    """When appending to file (start == -1) and lint reports an error, the runtime should
    write the updated content and delegate to correct_edit.
    """
    rt = FakeRuntime()
    # existing file content
    rt._read_ret = DummyFileReadObservation("line1\nline2")
    # validation passes
    rt._validate_ret = None
    # when lint check runs, return an error observation
    lint_error = DummyErrorObservation("lint fail")
    rt._lint_ret = lint_error
    # write should return a FileWriteObservation when called for the write inside the lint branch
    rt._write_ret = DummyFileWriteObservation()

    action = make_action(path="file.py", content="added_line", start=-1, end=-1)

    res = rt.llm_based_edit(action)

    # correct_edit returns a DummyFileEditObservation with content == 'CORRECTED'
    assert isinstance(res, DummyFileEditObservation)
    assert res.content == "CORRECTED"
    # ensure that a write was attempted with the updated content (old + appended)
    assert rt._write_calls, "expected at least one write call"
    # The last write in _write_calls corresponds to the write performed before calling correct_edit
    expected_updated = "line1\nline2\nadded_line"
    assert rt._write_calls[-1] == expected_updated
