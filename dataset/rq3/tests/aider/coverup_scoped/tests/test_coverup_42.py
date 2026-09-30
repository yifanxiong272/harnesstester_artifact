# file: aider/coders/base_coder.py:2296-2336
# asked: {"lines": [2305, 2306, 2308, 2310, 2311, 2312, 2313, 2315, 2316, 2318, 2319, 2320, 2321, 2322, 2323, 2325, 2327, 2328], "branches": []}
# gained: {"lines": [2305, 2306, 2308, 2310, 2311, 2312, 2313, 2315, 2316, 2318, 2319, 2320, 2321, 2322, 2323, 2325, 2327, 2328], "branches": []}

import traceback
from types import SimpleNamespace

import pytest

from aider.coders.base_coder import Coder
from aider import urls
import aider.repo as repo
import aider.coders.base_coder as base_coder


class DummyIO:
    def __init__(self):
        self.tool_error_calls = []
        self.tool_output_calls = []

    def tool_error(self, msg, strip=True):
        self.tool_error_calls.append((msg, strip))

    def tool_output(self, msg=None):
        # normalize None to explicit None in list
        self.tool_output_calls.append(msg)


def run_apply_updates_with_overrides(get_edits, apply_edits_dry_run, prepare_to_edit, apply_edits,
                                     io=None, num_malformed_responses=0, dry_run=False, reflected_message=None):
    """
    Helper: create a simple object with the attributes expected by Coder.apply_updates
    and call the method. Returns the object and the returned value from apply_updates.
    """
    obj = SimpleNamespace()
    obj.get_edits = get_edits
    obj.apply_edits_dry_run = apply_edits_dry_run
    obj.prepare_to_edit = prepare_to_edit
    obj.apply_edits = apply_edits
    obj.io = io or DummyIO()
    obj.num_malformed_responses = num_malformed_responses
    obj.dry_run = dry_run
    obj.reflected_message = reflected_message
    # Call the unbound method with our object as self
    result = Coder.apply_updates(obj)
    return obj, result


def test_apply_updates_value_error(monkeypatch):
    # Prepare functions that succeed until apply_edits which raises ValueError
    edits = [("a.txt", "content")]

    def get_edits():
        return edits

    def apply_edits_dry_run(edits_in):
        return edits_in

    def prepare_to_edit(edits_in):
        return edits_in

    # accept the edits parameter because apply_updates will pass it
    def apply_edits(edits_in):
        raise ValueError("malformed edit response")

    io = DummyIO()
    obj, returned = run_apply_updates_with_overrides(
        get_edits,
        apply_edits_dry_run,
        prepare_to_edit,
        apply_edits,
        io=io,
        num_malformed_responses=0,
        dry_run=False,
        reflected_message=None,
    )

    # The edited set should have been computed before the ValueError and returned
    assert returned == {"a.txt"}
    # num_malformed_responses must have been incremented
    assert obj.num_malformed_responses == 1
    # The IO must have recorded the error message and the edit_errors url and the original error message
    assert io.tool_error_calls, "Expected tool_error to be called"
    assert io.tool_error_calls[0][0] == "The LLM did not conform to the edit format."
    # tool_output_calls: first is urls.edit_errors, then an empty output (None), then the stringified inner error
    assert io.tool_output_calls[0] == urls.edit_errors
    assert io.tool_output_calls[1] is None
    assert io.tool_output_calls[2] == "malformed edit response"
    # reflected_message should be set to the inner error string
    assert obj.reflected_message == "malformed edit response"


def test_apply_updates_any_git_error(monkeypatch):
    # Create a custom exception class to represent a git-like error
    class MyGitError(Exception):
        pass

    # Patch the ANY_GIT_ERROR in the base_coder module (where it's imported) to a tuple including our exception class
    monkeypatch.setattr(base_coder, "ANY_GIT_ERROR", (MyGitError,))

    edits = [("b.txt", "other")]

    def get_edits():
        return edits

    def apply_edits_dry_run(edits_in):
        return edits_in

    def prepare_to_edit(edits_in):
        return edits_in

    # accept the edits parameter because apply_updates will pass it
    def apply_edits(edits_in):
        raise MyGitError("git failed")

    io = DummyIO()
    obj, returned = run_apply_updates_with_overrides(
        get_edits,
        apply_edits_dry_run,
        prepare_to_edit,
        apply_edits,
        io=io,
        num_malformed_responses=0,
        dry_run=False,
        reflected_message=None,
    )

    # Should return the set of edited files computed before the git error
    assert returned == {"b.txt"}
    # IO should have been told about the git error (single tool_error call with the string)
    assert io.tool_error_calls == [("git failed", True)]
    # num_malformed_responses should remain unchanged
    assert obj.num_malformed_responses == 0
    # reflected_message should not be set by this branch
    assert obj.reflected_message is None


def test_apply_updates_generic_exception(monkeypatch):
    edits = [("c.txt", "z")]

    def get_edits():
        return edits

    def apply_edits_dry_run(edits_in):
        return edits_in

    def prepare_to_edit(edits_in):
        return edits_in

    # accept the edits parameter because apply_updates will pass it
    def apply_edits(edits_in):
        raise RuntimeError("unexpected boom")

    # Capture calls to traceback.print_exc so we can assert it was invoked without printing to stderr
    printed = []

    def fake_print_exc():
        printed.append(True)

    monkeypatch.setattr(traceback, "print_exc", fake_print_exc)

    io = DummyIO()
    obj, returned = run_apply_updates_with_overrides(
        get_edits,
        apply_edits_dry_run,
        prepare_to_edit,
        apply_edits,
        io=io,
        num_malformed_responses=0,
        dry_run=False,
        reflected_message=None,
    )

    # Should return edited set
    assert returned == {"c.txt"}
    # First tool_error call should be the generic message, second should contain the error with strip=False
    assert len(io.tool_error_calls) >= 2
    assert io.tool_error_calls[0][0] == "Exception while updating files:"
    # second call should be the error string and have strip=False
    assert io.tool_error_calls[1] == ("unexpected boom", False)
    # traceback.print_exc must have been called
    assert printed == [True]
    # reflected_message should be set to the exception string
    assert obj.reflected_message == "unexpected boom"
