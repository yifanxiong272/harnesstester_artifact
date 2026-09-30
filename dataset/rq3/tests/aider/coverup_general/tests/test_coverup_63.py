# file: aider/coders/base_coder.py:2296-2336
# asked: {"lines": [2305, 2306, 2308, 2310, 2311, 2312, 2313, 2315, 2316, 2318, 2319, 2320, 2321, 2322, 2323, 2325, 2327, 2328], "branches": []}
# gained: {"lines": [2305, 2306, 2308, 2310, 2311, 2312, 2313, 2315, 2316, 2318, 2319, 2320, 2321, 2322, 2323, 2325, 2327, 2328], "branches": []}

import pytest

from aider import urls
import aider.urls
import aider.repo
from aider.coders import base_coder as base_coder_module


class DummyIO:
    def __init__(self):
        self.tool_errors = []
        self.tool_outputs = []

    def tool_error(self, msg, strip=True):
        self.tool_errors.append((msg, strip))

    def tool_output(self, *args):
        self.tool_outputs.append(args)


class BaseTestCoder(base_coder_module.Coder):
    def __init__(self):
        # do not call super(); just set required attributes used by apply_updates
        self.io = DummyIO()
        self.num_malformed_responses = 0
        self.dry_run = False
        self.reflected_message = None

    def get_edits(self):
        return []

    def apply_edits_dry_run(self, edits):
        return edits

    def prepare_to_edit(self, edits):
        return edits

    def apply_edits(self, edits):
        return None


def test_value_error_path_returns_edited_and_reports():
    class VECoder(BaseTestCoder):
        def get_edits(self):
            return [('file1.txt', 'change1'), ('file2.txt', 'change2')]

        def apply_edits(self, edits):
            raise ValueError("LLM returned malformed JSON")

    coder = VECoder()
    assert coder.num_malformed_responses == 0

    result = coder.apply_updates()

    assert result == {'file1.txt', 'file2.txt'}
    assert coder.num_malformed_responses == 1
    assert coder.reflected_message == "LLM returned malformed JSON"

    assert any("LLM did not conform" in call[0] for call in coder.io.tool_errors)
    outputs = coder.io.tool_outputs
    assert len(outputs) >= 3
    assert outputs[0] == (aider.urls.edit_errors,)
    assert outputs[1] == ()
    assert outputs[2] == ("LLM returned malformed JSON",)


def test_any_git_error_path_calls_tool_error_and_returns_edited(monkeypatch):
    class GitLikeError(Exception):
        pass

    # Patch the ANY_GIT_ERROR symbol used inside the base_coder module (it was imported there)
    monkeypatch.setattr(base_coder_module, "ANY_GIT_ERROR", GitLikeError, raising=True)

    class GitCoder(BaseTestCoder):
        def get_edits(self):
            return [('gfile.py', 'chg')]

        def apply_edits(self, edits):
            raise GitLikeError("git failed to write")

    coder = GitCoder()

    res = coder.apply_updates()

    assert res == {'gfile.py'}
    assert coder.io.tool_errors, "Expected tool_error to be called"
    last_err_msg, strip = coder.io.tool_errors[-1]
    assert "git failed to write" in last_err_msg
    # In the ANY_GIT_ERROR branch, reflected_message should not be set by the except block in base_coder,
    # so ensure it remains None.
    assert coder.reflected_message is None


def test_generic_exception_path_reports_exception_and_sets_reflected(monkeypatch):
    print_exc_called = {"called": False}

    def fake_print_exc():
        print_exc_called["called"] = True

    # Patch the traceback.print_exc used inside the base_coder module
    monkeypatch.setattr(base_coder_module.traceback, "print_exc", fake_print_exc, raising=True)

    class ExCoder(BaseTestCoder):
        def get_edits(self):
            return [('pathA', 'x')]

        def apply_edits(self, edits):
            raise Exception("unexpected boom")

    coder = ExCoder()

    res = coder.apply_updates()

    assert res == {'pathA'}
    assert len(coder.io.tool_errors) >= 2
    header_msg, header_strip = coder.io.tool_errors[0]
    assert "Exception while updating files" in header_msg
    msg, strip_flag = coder.io.tool_errors[1]
    assert "unexpected boom" in msg
    assert strip_flag is False
    assert print_exc_called["called"] is True
    assert coder.reflected_message == "unexpected boom"
