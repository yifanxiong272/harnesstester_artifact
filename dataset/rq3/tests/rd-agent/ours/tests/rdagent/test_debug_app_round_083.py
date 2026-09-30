import types
import builtins
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from rdagent.log.server import debug_app

# Deterministic helper message object used by the fake FileStorage.iter_msg
class DummyMessage:
    def __init__(self, tag, content, timestamp):
        self.tag = tag
        self.content = content
        self.timestamp = timestamp


# A simple controllable fake FileStorage. Tests set DummyFileStorage._messages
# to control what iter_msg yields.
class DummyFileStorage:
    _messages = []

    def __init__(self, path):
        # accept either Path or str - real code passes Path
        self.path = path

    def iter_msg(self):
        for m in list(DummyFileStorage._messages):
            yield m


# A simple fake WebStorage that delegates _obj_to_json behavior to a global
# function that tests will set. This mirrors the call signature used in
# upload_file.read_trace.
_obj_to_json_impl = None

class DummyWebStorage:
    def __init__(self, port, path):
        self.url = f"http://localhost:{port}"
        self.path = path

    def _obj_to_json(self, obj, tag, id, timestamp):
        # Delegate to test-provided implementation for deterministic control.
        assert _obj_to_json_impl is not None, "set _obj_to_json_impl in test"
        return _obj_to_json_impl(obj, tag, id, timestamp)


# DummyThread that runs target synchronously when start() is called. This
# avoids concurrency and makes the tests deterministic.
class DummyThread:
    def __init__(self, target=None, args=(), daemon=False):
        self._target = target
        self._args = args
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target(*self._args)


@pytest.fixture(autouse=True)
def isolate_and_patch(monkeypatch):
    """
    Patch out real FileStorage, WebStorage, threading.Thread, time.sleep, and
    randomname.get_name so tests are deterministic and perform no I/O.
    """
    # Patch the storage classes used by read_trace (they are imported inside read_trace).
    import rdagent.log.storage as storage_mod
    import rdagent.log.ui.storage as ui_storage_mod
    monkeypatch.setattr(storage_mod, "FileStorage", DummyFileStorage)
    monkeypatch.setattr(ui_storage_mod, "WebStorage", DummyWebStorage)

    # Patch threading.Thread in the debug_app module so created threads execute synchronously
    monkeypatch.setattr(debug_app.threading, "Thread", DummyThread)

    # Remove sleeping to keep tests fast/deterministic
    monkeypatch.setattr(debug_app, "time", types.SimpleNamespace(sleep=lambda *_: None))

    # Deterministic randomname
    import randomname
    monkeypatch.setattr(randomname, "get_name", lambda: "fixedname")

    # Ensure msgs_for_frontend is a clean dict each test
    debug_app.msgs_for_frontend = {}

    yield


def test_upload_file_data_science_round_083():
    """
    Exercise the 'Data Science' branch that constructs an o1-preview trace path,
    and exercise the code path where WebStorage._obj_to_json returns a list,
    causing the handler to append multiple entries for each yielded file.
    """
    global _obj_to_json_impl

    # Prepare two dummy messages with ordered timestamps
    now = datetime.now(timezone.utc)
    m1 = DummyMessage(tag="t.a", content={"k": 1}, timestamp=now - timedelta(seconds=2))
    m2 = DummyMessage(tag="t.b", content={"k": 2}, timestamp=now - timedelta(seconds=1))
    DummyFileStorage._messages = [m1, m2]

    # _obj_to_json returns a list for each message. Each element contains a 'msg' dict;
    # read_trace will append that inner dict to msgs_for_frontend[id].
    def impl(obj, tag, id, timestamp):
        return [
            {"msg": {"tag": f"{tag}.part1", "timestamp": timestamp, "content": {"src": "one"}}},
            {"msg": {"tag": f"{tag}.part2", "timestamp": timestamp, "content": {"src": "two"}}},
        ]

    _obj_to_json_impl = impl

    # Build a Flask test request context and call upload_file. Use competition with >=10 chars
    # to trigger competition[10:] slicing in the Data Science branch.
    app = debug_app.app
    form = {"scenario": "Data Science", "competition": "0123456789COMP", "loops": "1", "all_duration": "10"}
    with app.test_request_context(path="/upload", method="POST", data=form):
        resp, status = debug_app.upload_file()

    # Validate returned id and HTTP status
    assert status == 200
    assert resp.json["id"] == "Data Science/fixedname"

    # Check that msgs_for_frontend has an entry for that id and that it contains the
    # expected appended messages (two per dummy message) followed by an END marker.
    id_key = "Data Science/fixedname"
    assert id_key in debug_app.msgs_for_frontend
    entries = debug_app.msgs_for_frontend[id_key]

    # For two dummy messages and two list-elements each we expect 4 appended entries, then END
    assert len(entries) == 5
    # first four are the appended message dicts
    for i in range(4):
        assert isinstance(entries[i], dict)
        assert "tag" in entries[i]
        assert entries[i]["tag"].endswith(".part1") or entries[i]["tag"].endswith(".part2")

    # Last entry is the END marker
    last = entries[-1]
    assert last["tag"] == "END"
    assert "timestamp" in last
    assert last["content"] == {}


def test_upload_file_skip_and_single_message_round_083():
    """
    Exercise branches where WebStorage._obj_to_json returns falsy (skipped) and where
    it returns a single dict (single append). Ensure END is always appended.
    """
    global _obj_to_json_impl

    now = datetime.now(timezone.utc)

    # First: test the 'skipped' case where _obj_to_json returns None.
    DummyFileStorage._messages = [DummyMessage(tag="skip.tag", content={}, timestamp=now)]

    def impl_none(obj, tag, id, timestamp):
        return None

    _obj_to_json_impl = impl_none

    app = debug_app.app
    form = {"scenario": "NotDataScience", "competition": "unused", "loops": "1", "all_duration": "10"}
    with app.test_request_context(path="/upload", method="POST", data=form):
        resp, status = debug_app.upload_file()

    assert status == 200
    id_key = "NotDataScience/fixedname"
    assert id_key in debug_app.msgs_for_frontend
    entries = debug_app.msgs_for_frontend[id_key]
    # Only END should be present
    assert len(entries) == 1
    assert entries[0]["tag"] == "END"

    # Second: test single-dict return (not a list)
    DummyFileStorage._messages = [DummyMessage(tag="single.tag", content={"v": 1}, timestamp=now)]

    def impl_single(obj, tag, id, timestamp):
        return {"msg": {"tag": tag, "timestamp": timestamp, "content": {"v": 1}}}

    _obj_to_json_impl = impl_single

    form2 = {"scenario": "OtherScenario", "competition": "unused2", "loops": "1", "all_duration": "10"}
    with app.test_request_context(path="/upload", method="POST", data=form2):
        resp2, status2 = debug_app.upload_file()

    assert status2 == 200
    id2 = "OtherScenario/fixedname"
    assert id2 in debug_app.msgs_for_frontend
    entries2 = debug_app.msgs_for_frontend[id2]
    # One appended message then END
    assert len(entries2) == 2
    assert isinstance(entries2[0], dict)
    assert entries2[0]["tag"] == "single.tag"
    assert entries2[1]["tag"] == "END"
