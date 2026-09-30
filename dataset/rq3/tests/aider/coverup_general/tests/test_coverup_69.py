# file: aider/analytics.py:213-254
# asked: {"lines": [220, 221, 222, 229, 234, 235, 236, 237, 253, 254], "branches": [[219, 220], [228, 229], [233, 234], [239, 242], [242, 0]]}
# gained: {"lines": [220, 221, 222, 229, 234, 235, 236, 237, 253, 254], "branches": [[219, 220], [228, 229], [233, 234], [239, 242]]}

import builtins
import json
import time

import pytest
from mixpanel import MixpanelException

from aider.analytics import Analytics
from aider.models import model_info_manager


class _NameHolder:
    def __init__(self, name):
        self.name = name


class DummyMainModel:
    def __init__(self, name, weak_name, editor_name):
        self.name = name
        self.weak_model = _NameHolder(weak_name)
        self.editor_model = _NameHolder(editor_name)


class FakeMP:
    def track(self, user_id, event_name, properties):
        raise MixpanelException("simulated mp error")


class FakePH:
    def __init__(self):
        self.calls = []

    def capture(self, event_name, distinct_id=None, properties=None):
        self.calls.append({"event": event_name, "distinct_id": distinct_id, "properties": properties})


def test_event_with_main_model_mp_exception_ph_and_logfile(tmp_path, monkeypatch):
    # Prepare analytics instance
    a = Analytics()
    a.user_id = "user-1"
    a.mp = FakeMP()
    ph = FakePH()
    a.ph = ph
    logfile = tmp_path / "analytics.log"
    a.logfile = str(logfile)

    # Patch model_info_manager to return info only for 'goodmodel'
    def fake_get(name):
        if name == "goodmodel":
            return {"some": "info"}
        return None

    monkeypatch.setattr(model_info_manager, "get_model_from_cached_json_db", fake_get)

    # Prepare main model:
    # - main_model.name -> 'goodmodel' (manager returns info -> keep name)
    # - weak_model.name -> contains '/' so should become 'org/REDACTED'
    # - editor_model.name -> unknown no '/' -> becomes None -> stringified to 'None'
    main = DummyMainModel("goodmodel", "org/some", "unknown")

    # Call event with an integer and a non-integer property
    a.event("test_event", main_model=main, extra=5, other="value")

    # mp.track should have raised MixpanelException and analytics.mp set to None
    assert a.mp is None

    # ph.capture should have been called once
    assert len(ph.calls) == 1
    call = ph.calls[0]
    assert call["event"] == "test_event"
    assert call["distinct_id"] == "user-1"
    # Properties passed to ph.capture should preserve numeric types and stringify others
    props = call["properties"]
    assert props["extra"] == 5
    assert props["main_model"] == "goodmodel"
    assert props["weak_model"] == "org/REDACTED"
    # editor_model was redacted to None then stringified
    assert props["editor_model"] == "None"
    assert props["other"] == "value"

    # logfile should have one JSON line; verify contents
    with open(logfile, "r") as f:
        lines = f.read().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "test_event"
    # In the logfile JSON, numeric stays numeric and others are strings
    logged_props = entry["properties"]
    assert logged_props["extra"] == 5
    assert logged_props["main_model"] == "goodmodel"
    assert logged_props["weak_model"] == "org/REDACTED"
    assert logged_props["editor_model"] == "None"
    # Check time is an int and reasonably recent
    assert isinstance(entry["time"], int)
    assert abs(entry["time"] - int(time.time())) < 10


def test_event_logfile_oserror_is_ignored(monkeypatch, tmp_path):
    a = Analytics()
    a.user_id = "u2"
    a.mp = None
    a.ph = None
    logfile = tmp_path / "no_write.log"
    a.logfile = str(logfile)

    # Replace builtins.open to always raise OSError to exercise the except branch
    def fake_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(builtins, "open", fake_open)

    # Should not raise despite OSError when attempting to write logfile
    a.event("will_fail_write", main_model=None, some=1)

    # Because open raised, logfile should not exist
    assert not logfile.exists()
