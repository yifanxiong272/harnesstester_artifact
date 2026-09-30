import json as std_json
import pytest

import openhands.io.json as oh_json
from openhands.core.exceptions import LLMResponseError


def test_loads_repair_success_round_069(monkeypatch):
    """When the top-level json.loads fails, the function should locate an embedded
    JSON object, repair it, and return the parsed object."""
    original = 'noise before {"a": 1} noise after'
    repaired = '{"a": 1}'

    # Patch json.loads used inside the module to fail on the original input
    # and succeed on the repaired string.
    def fake_loads(s, **kwargs):
        if s == original:
            raise std_json.JSONDecodeError('msg', s, 0)
        if s == repaired:
            return {"a": 1}
        raise AssertionError('unexpected loads input: ' + repr(s))

    monkeypatch.setattr(oh_json, "repair_json", lambda response: repaired)
    monkeypatch.setattr(oh_json, "json", type('J', (), {'loads': staticmethod(fake_loads), 'JSONDecodeError': std_json.JSONDecodeError}))

    result = oh_json.loads(original)
    assert result == {"a": 1}


def test_loads_repair_raises_value_error_round_069(monkeypatch):
    """If repair_json raises a ValueError (or repaired parse fails), the
    function should raise an LLMResponseError wrapping the failure."""
    original = 'prefix {"bad: 1} suffix'

    # First attempt (the top-level loads) fails with JSONDecodeError.
    def fake_loads_fail(s, **kwargs):
        raise std_json.JSONDecodeError('msg', s, 0)

    # Make repair_json raise a ValueError to simulate irreparable content.
    def fake_repair(response):
        raise ValueError('cannot repair')

    # Patch module-level symbols
    monkeypatch.setattr(oh_json, "json", type('J', (), {'loads': staticmethod(fake_loads_fail), 'JSONDecodeError': std_json.JSONDecodeError}))
    monkeypatch.setattr(oh_json, "repair_json", fake_repair)

    with pytest.raises(LLMResponseError) as excinfo:
        oh_json.loads(original)
    assert 'Invalid JSON in response' in str(excinfo.value)


def test_loads_no_json_object_round_069(monkeypatch):
    """If no matching JSON object braces are found, the function should raise
    an LLMResponseError indicating no valid JSON object was found."""
    original = 'this string has no braces that form an object'

    # Make top-level json.loads fail to force the manual scan path.
    def fake_loads_fail(s, **kwargs):
        raise std_json.JSONDecodeError('msg', s, 0)

    monkeypatch.setattr(oh_json, "json", type('J', (), {'loads': staticmethod(fake_loads_fail), 'JSONDecodeError': std_json.JSONDecodeError}))

    with pytest.raises(LLMResponseError) as excinfo:
        oh_json.loads(original)
    assert 'No valid JSON object found in response.' in str(excinfo.value)
