import types
import pytest
from aider.coders import base_coder


class FakeConsole:
    """Replace rich Console used by the module; record last show_cursor arg."""
    last_arg = None

    def __init__(self, *_, **__):
        pass

    def show_cursor(self, value):
        FakeConsole.last_arg = value


class FakeIO:
    def __init__(self):
        self.messages = []

    def tool_warning(self, msg):
        # record warnings for assertions
        self.messages.append(msg)


def _bind_keyboard_interrupt_to(obj):
    """Attach the Coder.keyboard_interrupt function as a bound method on obj."""
    obj.keyboard_interrupt = types.MethodType(base_coder.Coder.keyboard_interrupt, obj)
    return obj


def test_keyboard_interrupt_single_round_150(monkeypatch):
    # Arrange: no previous interrupt, controlled time
    monkeypatch.setattr(base_coder, "Console", FakeConsole)
    monkeypatch.setattr(base_coder.time, "time", lambda: 1000.0)

    inst = type("X", (), {})()
    inst.last_keyboard_interrupt = None
    inst.io = FakeIO()

    called_events = []

    def event(name, **kwargs):
        called_events.append((name, kwargs))

    inst.event = event

    # Act
    _bind_keyboard_interrupt_to(inst)
    inst.keyboard_interrupt()

    # Assert: show_cursor was called with True, tool_warning prompted to press again,
    # and last_keyboard_interrupt updated to the mocked time
    assert FakeConsole.last_arg is True
    assert inst.io.messages == ["\n\n^C again to exit"]
    assert inst.last_keyboard_interrupt == 1000.0
    # event should not have been called in this branch
    assert called_events == []


def test_keyboard_interrupt_double_exit_round_150(monkeypatch):
    # Arrange: previous interrupt recently happened; time difference < thresh triggers exit
    monkeypatch.setattr(base_coder, "Console", FakeConsole)
    monkeypatch.setattr(base_coder.time, "time", lambda: 1000.0)

    inst = type("Y", (), {})()
    inst.last_keyboard_interrupt = 999.5  # now - last = 0.5 < thresh(2)
    inst.io = FakeIO()

    called_events = []

    def event(name, **kwargs):
        called_events.append((name, kwargs))

    inst.event = event

    # Act & Assert: SystemExit is expected; prior to exit, tool_warning and event should run
    _bind_keyboard_interrupt_to(inst)
    with pytest.raises(SystemExit):
        inst.keyboard_interrupt()

    assert FakeConsole.last_arg is True
    assert inst.io.messages == ["\n\n^C KeyboardInterrupt"]
    assert called_events == [("exit", {"reason": "Control-C"})]
    # last_keyboard_interrupt should remain unchanged in the exit branch
    assert inst.last_keyboard_interrupt == 999.5
