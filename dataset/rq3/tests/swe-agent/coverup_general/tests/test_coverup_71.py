# file: sweagent/api/hooks.py:73-91
# asked: {"lines": [82, 83, 84, 85, 86, 87, 88, 89], "branches": []}
# gained: {"lines": [82, 83, 84, 85, 86, 87, 88, 89], "branches": []}

import pytest
from sweagent.api import hooks


def _make_instance(cls):
    """
    Try to construct an instance of cls normally; if that fails (requires args),
    allocate one without calling __init__ so we can attach a fake _emit.
    """
    try:
        return cls()
    except TypeError:
        return object.__new__(cls)


def test_up_env_calls_emit_with_defaults(monkeypatch):
    WebUpdate = hooks.WebUpdate
    inst = _make_instance(WebUpdate)

    called = {}

    def fake_emit(*args, **kwargs):
        # record positional args and kwargs
        called['args'] = args
        called['kwargs'] = kwargs
        return "EMITTED"

    # attach fake_emit to the instance
    monkeypatch.setattr(inst, "_emit", fake_emit, raising=False)

    # Call with only required args (type_ required)
    ret = inst.up_env("hello world", type_="info")

    # Verify return value (original method does not return anything, but our fake returns value;
    # up_env does not return that value, so ret should be None)
    assert ret is None

    # Verify _emit was called once
    assert 'args' in called, "_emit was not called"

    # Validate positional and payload
    args = called['args']
    assert len(args) >= 2
    assert args[0] == "update"

    payload = args[1]
    assert isinstance(payload, dict)
    assert payload["feed"] == "env"
    assert payload["message"] == "hello world"
    # default format
    assert payload["format"] == "markdown"
    # default thought_idx is None
    assert payload["thought_idx"] is None
    assert payload["type"] == "info"


def test_up_env_with_custom_format_and_thought_idx(monkeypatch):
    WebUpdate = hooks.WebUpdate
    inst = _make_instance(WebUpdate)

    captured = {}

    def fake_emit(event, payload):
        captured['event'] = event
        captured['payload'] = payload

    monkeypatch.setattr(inst, "_emit", fake_emit, raising=False)

    # Call with custom format and thought_idx
    ret = inst.up_env("status update", type_="warning", format="html", thought_idx=42)

    # up_env should not return anything
    assert ret is None

    # Ensure _emit was called and captured values are correct
    assert captured.get('event') == "update"
    payload = captured.get('payload')
    assert isinstance(payload, dict)
    assert payload == {
        "feed": "env",
        "message": "status update",
        "format": "html",
        "thought_idx": 42,
        "type": "warning",
    }
