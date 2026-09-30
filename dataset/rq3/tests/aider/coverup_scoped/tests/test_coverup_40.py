# file: aider/io.py:806-925
# asked: {"lines": [843, 844, 846, 851, 852, 853, 854, 855, 862, 863, 864, 886, 887], "branches": [[841, 843], [843, 844], [843, 846], [850, 851], [862, 863], [862, 864]]}
# gained: {"lines": [843, 844, 846, 851, 852, 853, 854, 855, 862, 863, 864, 886, 887], "branches": [[841, 843], [843, 844], [843, 846], [850, 851], [862, 863], [862, 864]]}

import sys
import builtins
import types
import pytest

from aider.io import InputOutput


def test_confirm_ask_multiline_subject_and_inner_validation(monkeypatch):
    """
    Exercises:
    - default starting with 'n' branch (adds ' [No]: ')
    - subject with multiple lines -> padded subject branch (lines 851-855)
    - inner is_valid_response body by having the prompt mock retrieve and call it from the caller frame
      (lines 862-864)
    - normal prompt_session.prompt path returning 'y' to make confirm_ask return True
    """
    io = InputOutput(pretty=False, fancy_input=False)

    # Capture tool_output calls
    tool_output_calls = []

    def fake_tool_output(*messages, **kwargs):
        tool_output_calls.append((messages, kwargs))

    # Monkeypatch the instance method
    io.tool_output = fake_tool_output

    class PromptSessionMock:
        def prompt(self, question, style=None, complete_while_typing=None):
            # Access the caller's frame (confirm_ask) and get the local is_valid_response
            caller_frame = sys._getframe(1)
            is_valid = caller_frame.f_locals.get("is_valid_response")
            # Ensure we found the inner function and exercise both branches:
            #  - empty text -> should return True
            #  - non-empty text in valid_responses -> should return True
            assert is_valid is not None, "is_valid_response not found in caller locals"
            assert is_valid("") is True
            assert is_valid("yes") is True
            # Return a 'y' response to make confirm_ask accept
            return "y"

    io.prompt_session = PromptSessionMock()

    # Subject with multiple lines to trigger padding code path
    subject = "line1\nl2"
    result = io.confirm_ask("Do the thing?", default="n", subject=subject, explicit_yes_required=False, group=None, allow_never=False)

    # confirm_ask should return True because our prompt returned 'y'
    assert result is True

    # tool_output was called at least twice: once with no args, and once with padded_subject & bold=True
    # Find the call where bold=True
    bold_calls = [call for call in tool_output_calls if call[1].get("bold")]
    assert bold_calls, "Expected a tool_output call with bold=True for padded subject"

    padded_messages, kwargs = bold_calls[0]
    # padded_messages should contain one string: the padded subject
    assert len(padded_messages) == 1
    padded_subject = padded_messages[0]
    # Expect second line padded to length of the longest line ('line1' length 5)
    assert padded_subject == "line1\nl2   "


def test_confirm_ask_eof_and_default_other(monkeypatch):
    """
    Exercises:
    - default not starting with y or n -> else branch that uses f" [{default}]: " (line 846)
    - input() raising EOFError triggers the except branch (lines 886-887) where res = default
    - confirm_ask should then return False (default not affirmative)
    """
    io = InputOutput(pretty=False, fancy_input=False)

    # Monkeypatch builtins.input to raise EOFError to hit the except branch
    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)

    result = io.confirm_ask("Question about X?", default="Maybe", subject=None)
    assert result is False
