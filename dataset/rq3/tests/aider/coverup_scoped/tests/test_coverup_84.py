# file: aider/repo.py:326-373
# asked: {"lines": [338, 359, 366, 367], "branches": [[330, 332], [337, 338], [342, 365], [358, 359], [365, 366]]}
# gained: {"lines": [338, 359, 366, 367], "branches": [[330, 332], [337, 338], [342, 365], [358, 359], [365, 366]]}

import types
from contextlib import contextmanager

import pytest

from aider.repo import GitRepo


@contextmanager
def _noop_spinner(text):
    yield


class _Model:
    def __init__(self, name, system_prompt_prefix=None, max_input_tokens=0, token_count_return=0, send_return=None):
        self.name = name
        self.system_prompt_prefix = system_prompt_prefix
        self.info = {"max_input_tokens": max_input_tokens} if max_input_tokens is not None else {}
        self._token_count_return = token_count_return
        self._send_return = send_return
        self.token_count_called_with = None
        self.simple_send_called_with = None

    def token_count(self, messages):
        # record messages passed for later inspection
        self.token_count_called_with = messages
        return self._token_count_return

    def simple_send_with_retries(self, messages):
        self.simple_send_called_with = messages
        return self._send_return


def test_get_commit_message_skips_model_exceeding_max_tokens_and_uses_prefix_and_strips_quotes(monkeypatch):
    # Arrange
    monkeypatch.setattr("aider.repo.WaitingSpinner", _noop_spinner)

    repo = GitRepo.__new__(GitRepo)

    # Provide a commit_prompt template so system_content formatting is exercised with language_instruction
    repo.commit_prompt = "COMMIT_PROMPT{language_instruction}"

    # Create two models:
    # model1 will be skipped because token_count > max_input_tokens
    model1 = _Model(name="m1", system_prompt_prefix=None, max_input_tokens=10, token_count_return=20, send_return=None)
    # model2 will be used and has a system_prompt_prefix to exercise that branch
    model2 = _Model(name="m2", system_prompt_prefix="PREFIX", max_input_tokens=0, token_count_return=5, send_return='  "My commit message"  ')

    repo.models = [model1, model2]

    # io is not used on success, but set to a dummy object to be safe
    repo.io = types.SimpleNamespace(tool_error=lambda msg: (_ for _ in ()).throw(AssertionError("tool_error should not be called")))

    diffs = "diff --git a/file b/file\n+added line"
    context = "Some context line"

    # Act
    result = repo.get_commit_message(diffs=diffs, context=context, user_language="Spanish")

    # Assert
    # The first model should have been queried (and skipped)
    assert model1.token_count_called_with is not None
    # The second model should have been used to generate and return a stripped message without surrounding quotes
    assert result == "My commit message"
    # Verify that the messages passed to the second model contain the current system content with the prefix
    system_msg = model2.simple_send_called_with[0]["content"]
    assert "PREFIX" in system_msg  # system_prompt_prefix was prefixed
    # Verify that the user content includes context and diffs in the expected order
    user_msg = model2.simple_send_called_with[1]["content"]
    assert user_msg.startswith(context + "\n")
    assert "# Diffs:\n" in user_msg
    # Ensure language instruction was applied to the system content via commit_prompt formatting
    assert "Is written in Spanish" in system_msg or "Spanish" in system_msg


def test_get_commit_message_reports_error_when_no_model_generates_message(monkeypatch):
    # Arrange
    monkeypatch.setattr("aider.repo.WaitingSpinner", _noop_spinner)

    repo = GitRepo.__new__(GitRepo)
    # Use prompts via commit_prompt to ensure formatting code paths remain valid
    repo.commit_prompt = "CP{language_instruction}"

    # Two models, both will be skipped/produce no message:
    m1 = _Model(name="m1", system_prompt_prefix=None, max_input_tokens=5, token_count_return=10, send_return=None)
    m2 = _Model(name="m2", system_prompt_prefix=None, max_input_tokens=5, token_count_return=10, send_return=None)

    repo.models = [m1, m2]

    # Provide an io that records tool_error calls
    calls = []
    def fake_tool_error(msg):
        calls.append(msg)

    repo.io = types.SimpleNamespace(tool_error=fake_tool_error)

    # Act
    result = repo.get_commit_message(diffs="x", context="", user_language=None)

    # Assert
    assert result is None  # function should return None on failure
    assert calls == ["Failed to generate commit message!"]  # tool_error should have been called with this exact message
