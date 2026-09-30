# file: sweagent/agent/models.py:364-404
# asked: {"lines": [370, 371, 372, 375, 376, 377, 378, 379, 380, 381, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 397, 398, 399, 400, 401, 402, 403, 404], "branches": [[375, 376], [375, 385], [378, 379], [381, 378], [381, 383], [385, 386], [385, 397], [387, 388], [389, 390], [389, 391], [391, 392], [391, 393], [398, 399], [398, 402]]}
# gained: {"lines": [370, 371, 372, 375, 376, 377, 378, 379, 380, 381, 383, 384, 385, 386, 387, 388, 389, 390, 397, 398, 399, 400, 401, 402, 403, 404], "branches": [[375, 376], [375, 385], [378, 379], [381, 378], [381, 383], [385, 386], [385, 397], [387, 388], [389, 390], [398, 399], [398, 402]]}

import builtins
import types
import pytest

import sweagent.agent.models as models
from sweagent.agent.models import HumanModel

class DummyStats:
    def __init__(self):
        self.instance_cost = 0.0

def make_human_instance():
    # Create instance without calling __init__ to avoid file IO and other setup
    inst = object.__new__(HumanModel)
    inst.stats = DummyStats()
    inst.multi_line_command_endings = {}
    # Replace methods that would touch filesystem or external state
    inst._save_readline_history = lambda: None
    inst._update_stats = lambda: None
    return inst

def test_spend_money_updates_stats_and_returns_message(monkeypatch):
    inst = make_human_instance()

    # Capture calls to _handle_raise_commands
    called = {}
    def fake_handle(action):
        called['action'] = action
    monkeypatch.setattr(models, "_handle_raise_commands", fake_handle)

    # Provide input: a spend_money command
    inputs = iter(["spend_money 12.5"])
    monkeypatch.setattr(builtins, "input", lambda prompt="> ": next(inputs))

    res = HumanModel._query(inst, history=None, action_prompt="> ")
    # After spend_money, stats should be increased and message should be the echo command
    assert pytest.approx(inst.stats.instance_cost, rel=1e-6) == 12.5
    assert res == {"message": "echo 'Spent 12.5 dollars'"}
    assert called.get('action') == "echo 'Spent 12.5 dollars'"

def test_multi_line_command_endings_reads_until_end(monkeypatch):
    inst = make_human_instance()
    # set a multi-line command mapping
    inst.multi_line_command_endings = {"edit": "END"}

    # Capture calls to _handle_raise_commands and to _update_stats
    handled = {}
    def fake_handle(action):
        handled['action'] = action
    monkeypatch.setattr(models, "_handle_raise_commands", fake_handle)

    updated = {'called': False}
    inst._update_stats = lambda: updated.__setitem__('called', True)
    # Simulate inputs: initial 'edit', then two lines, then the END marker
    inputs = iter(["edit", "line1", "line2", "END"])
    monkeypatch.setattr(builtins, "input", lambda prompt="> ": next(inputs))

    res = HumanModel._query(inst, history=None, action_prompt="> ")
    # The action returned should be the joined buffer of the multi-line input
    assert res == {"message": "edit\nline1\nline2\nEND"}
    assert handled['action'] == "edit\nline1\nline2\nEND"
    assert updated['called'] is True

def test_unicode_escape_and_start_multiline_command_recursion(monkeypatch):
    inst = make_human_instance()

    # We'll test two behaviors in sequence by driving inputs:
    # First call: provide a unicode-escaped string -> should be decoded.
    # Second call: simulate start_multiline_command which immediately receives end_multiline_command,
    # causing recursive call to _query; ensure recursion consumes next input and returns it.
    sequence = [
        r"hello\nworld",  # first call: unicode escape path
        "start_multiline_command",  # second call: triggers special branch
        "end_multiline_command",    # causes immediate recursive call
        "final input"               # consumed by recursive call and returned
    ]
    inputs = iter(sequence)
    monkeypatch.setattr(builtins, "input", lambda prompt="> ": next(inputs))

    # Replace handle and update to track their calls
    handled = {}
    def fake_handle(action):
        # record last action processed
        handled.setdefault('actions', []).append(action)
    monkeypatch.setattr(models, "_handle_raise_commands", fake_handle)
    updated = {'count': 0}
    inst._update_stats = lambda: updated.__setitem__('count', updated['count'] + 1)

    # First invocation: unicode escape decoding
    res1 = HumanModel._query(inst, history=None, action_prompt="> ")
    assert res1 == {"message": "hello\nworld"}
    # Second invocation: start_multiline_command then immediate end causes recursion and returns "final input"
    res2 = HumanModel._query(inst, history=None, action_prompt="> ")
    assert res2 == {"message": "final input"}
    # Ensure _handle_raise_commands was called for both resulting actions
    assert handled.get('actions') and "hello\nworld" in handled['actions']
    assert "final input" in handled['actions']
    # _update_stats should have been called twice (once per top-level/recursive query)
    assert updated['count'] >= 2
