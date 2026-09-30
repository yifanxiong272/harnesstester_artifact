import types
import pytest

import aider.coders.base_coder as base_coder


class DummyIO:
    def __init__(self):
        self.tool_errors = []
        self.tool_outputs = []

    def tool_error(self, msg, strip=True):
        # mirror real signature used in code (strip optional)
        self.tool_errors.append((msg, strip))

    def tool_output(self, *args):
        # tool_output may be called with zero or one arg in the code
        if len(args) == 0:
            self.tool_outputs.append(None)
        elif len(args) == 1:
            self.tool_outputs.append(args[0])
        else:
            self.tool_outputs.append(args)


class DummySelf:
    def __init__(self):
        # defaults used/updated by apply_updates
        self.num_malformed_responses = 0
        self.reflected_message = None
        self.dry_run = True
        self.io = DummyIO()
        # placeholders for the edit pipeline methods
        self._edits_to_return = []
        self.applied_edits_arg = None

    def get_edits(self):
        return self._edits_to_return

    def apply_edits_dry_run(self, edits):
        # identity transformation unless overridden in test
        return edits

    def prepare_to_edit(self, edits):
        return edits

    def apply_edits(self, edits):
        # record that apply_edits was called with the argument
        self.applied_edits_arg = edits


def test_apply_updates_dry_run_round_094(monkeypatch):
    """
    Normal flow: when there is one edit and dry_run True, apply_updates returns the edited set
    and the IO outputs show a dry-run message for that path.
    """
    dummy = DummySelf()
    # one edit: tuple where first element is the path (per code: edit[0])
    dummy._edits_to_return = [("some/path.txt", "new content")]
    dummy.dry_run = True

    edited = base_coder.Coder.apply_updates(dummy)

    assert edited == {"some/path.txt"}
    # ensure apply_edits was invoked with the edits
    assert dummy.applied_edits_arg == [("some/path.txt", "new content")]
    # verify the dry-run output message is present
    assert any(
        isinstance(o, str) and "Did not apply edit to some/path.txt (--dry-run)" in o
        for o in dummy.io.tool_outputs
    )


def test_apply_updates_value_error_round_094(monkeypatch):
    """
    If get_edits raises ValueError, apply_updates should increment
    num_malformed_responses, call tool_error/tool_output sequence, and set reflected_message.
    """
    dummy = DummySelf()

    def raise_value_error():
        raise ValueError("LLM-bad-format")

    dummy.get_edits = raise_value_error

    # ensure urls.edit_errors exists and is a stable value the function will pass to tool_output
    monkeypatch.setattr(base_coder, "urls", types.SimpleNamespace(edit_errors="http://edit/errors"))

    edited = base_coder.Coder.apply_updates(dummy)

    # no edits applied
    assert edited == set()
    # malformed counter incremented
    assert dummy.num_malformed_responses == 1
    # reflected_message should contain the ValueError message string
    assert dummy.reflected_message == "LLM-bad-format"
    # tool_error should have been called with the fixed message about LLM format
    assert any("The LLM did not conform to the edit format." in te[0] for te in dummy.io.tool_errors)
    # tool_output should have been called for the edit_errors URL, an empty output, and the error string
    outputs = dummy.io.tool_outputs
    # Expect at least three entries: URL, None, and the string error
    assert "http://edit/errors" in outputs
    assert None in outputs
    assert "LLM-bad-format" in outputs


def test_apply_updates_any_git_error_round_094(monkeypatch):
    """
    If get_edits raises an exception matching ANY_GIT_ERROR, apply_updates should call tool_error
    with the stringified error and return the (empty) edited set.
    """
    dummy = DummySelf()

    class FakeGitError(Exception):
        pass

    def raise_git_error():
        raise FakeGitError("git-failed")

    dummy.get_edits = raise_git_error

    # Patch the module-level ANY_GIT_ERROR to include our FakeGitError so the except block matches
    monkeypatch.setattr(base_coder, "ANY_GIT_ERROR", (FakeGitError,))

    edited = base_coder.Coder.apply_updates(dummy)

    assert edited == set()
    # tool_error should have been called with the git error string
    assert any("git-failed" in te[0] for te in dummy.io.tool_errors)


def test_apply_updates_generic_exception_round_094(monkeypatch):
    """
    If an unexpected Exception is raised, apply_updates should report it via tool_error,
    set reflected_message, and return the empty edited set. Also suppress traceback.print_exc side-effects.
    """
    dummy = DummySelf()

    def raise_exc():
        raise Exception("unexpected-boom")

    dummy.get_edits = raise_exc

    # Patch traceback.print_exc in the module so the test does not emit to stderr
    monkeypatch.setattr(base_coder, "traceback", types.SimpleNamespace(print_exc=lambda: None))

    edited = base_coder.Coder.apply_updates(dummy)

    assert edited == set()
    # check that the first tool_error contains the 'Exception while updating files:' message
    assert any("Exception while updating files:" in te[0] for te in dummy.io.tool_errors)
    # check that reflected_message captured the exception text
    assert dummy.reflected_message == "unexpected-boom"
