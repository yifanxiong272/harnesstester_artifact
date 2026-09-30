import builtins
from types import SimpleNamespace
import pytest

import sweagent.agent.models as models
from sweagent.agent.models import HumanModel


def make_human_model_instance():
    # Create instance without running __init__ and attach required attributes
    h = HumanModel.__new__(HumanModel)
    # commands that start a multi-line block and their terminating keywords
    h.multi_line_command_endings = {"edit": "EOF"}
    # minimal stats object to observe instance_cost changes
    h.stats = SimpleNamespace(instance_cost=0.0)
    return h


def test_multi_line_command_ending_round_004(monkeypatch):
    """Simulate an initial 'edit' command that collects multiple lines until EOF."""
    h = make_human_model_instance()

    # Prepare inputs: initial action plus two further lines, final terminator EOF
    inputs = iter(["edit first line", "inserted line", "EOF"]) 
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))

    # Recorders for side-effects the method calls
    saved = []
    updated = []
    handled = []

    h._save_readline_history = lambda: saved.append(True)
    h._update_stats = lambda: updated.append(True)

    # Patch module-level raise handler to capture the action passed
    monkeypatch.setattr(models, "_handle_raise_commands", lambda action: handled.append(action))

    out = h._query(history=None, action_prompt="> ")

    # The returned message should be the joined buffer: initial + inserted + EOF
    assert out == {"message": "edit first line\ninserted line\nEOF"}
    # Ensure we saved/readline history once and updated stats once
    assert len(saved) == 1
    assert len(updated) == 1
    # The handler should have been called with the final assembled message
    assert handled == ["edit first line\ninserted line\nEOF"]


def test_start_multiline_command_return_recursive_round_004(monkeypatch):
    """Simulate the start_multiline_command flow that returns into a recursive _query call.

    Sequence: 'start_multiline_command' -> 'end_multiline_command' (causes return recursion) ->
    then nested call receives 'spend_money 7' which should update stats and produce an echo message.
    """
    h = make_human_model_instance()

    # Setup inputs for the outer call then the inner recursive call
    inputs = iter(["start_multiline_command", "end_multiline_command", "spend_money 7"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))

    saved = []
    updated = []
    handled = []

    h._save_readline_history = lambda: saved.append(True)
    h._update_stats = lambda: updated.append(True)

    # Patch the raise handler to avoid interference
    monkeypatch.setattr(models, "_handle_raise_commands", lambda action: handled.append(action))

    out = h._query(history=None, action_prompt="> ")

    # After the recursive handling of 'spend_money 7' we expect the stats to have increased
    assert pytest.approx(h.stats.instance_cost) == 7.0
    # The action should have been converted to the echo message
    assert out == {"message": "echo 'Spent 7.0 dollars'"}
    # _save_readline_history should have been called twice (outer and recursive inner call)
    assert len(saved) == 2
    # _update_stats should have been called once from the final execution
    assert len(updated) == 1
    # _handle_raise_commands must have been called with the final action string
    assert handled == ["echo 'Spent 7.0 dollars'"]


def test_unicode_unescape_round_004(monkeypatch):
    """Test that a single-line input with escape sequences is unescaped via unicode_escape.

    Input like 'say \\nworld' should become 'say \nworld' in the returned message.
    """
    h = make_human_model_instance()

    # Provide a single-line input that contains an escaped newline sequence
    inputs = iter(["say \\nworld"])  # literal backslash-n in the input
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))

    saved = []
    updated = []
    handled = []

    h._save_readline_history = lambda: saved.append(True)
    h._update_stats = lambda: updated.append(True)
    monkeypatch.setattr(models, "_handle_raise_commands", lambda action: handled.append(action))

    out = h._query(history=None, action_prompt="> ")

    # The unicode_escape decode should convert the '\\n' into an actual newline
    assert out == {"message": "say \nworld"}
    assert len(saved) == 1
    assert len(updated) == 1
    assert handled == ["say \nworld"]
