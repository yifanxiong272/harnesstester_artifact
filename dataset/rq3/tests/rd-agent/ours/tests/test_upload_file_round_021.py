import importlib
import types
from pathlib import Path

import pytest


def _make_fake_request(form_values, files_list):
    class Files:
        def __init__(self, files):
            self._files = files

        def getlist(self, key):
            # upload endpoint uses getlist("files")
            return list(self._files)

    class Form:
        def __init__(self, d):
            self._d = d

        def get(self, k):
            # simple mapping consistent with server expectations
            return self._d.get(k)

    return types.SimpleNamespace(form=Form(form_values), files=Files(files_list))


def test_invalid_file_type_round_021(tmp_path, monkeypatch):
    """
    Verify early rejection when uploaded filename is not a PDF.

    Covers branches around file iteration and invalid file type (lines ~120-126).
    """
    m = importlib.import_module("rdagent.log.server.app")

    # isolate filesystem to tmp_path
    monkeypatch.setattr(m, "log_folder_path", Path(tmp_path))

    # deterministic random name
    monkeypatch.setattr(m.randomname, "get_name", lambda: "rand")

    # keep filename sanitization simple and deterministic
    monkeypatch.setattr(m, "secure_filename", lambda x: x)

    # jsonify -> identity so we can inspect returned dicts
    monkeypatch.setattr(m, "jsonify", lambda x: x)

    # ensure no real subprocess will run if reached
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **kw: None)

    # provide a fake request with a non-pdf file
    class FakeFile:
        def __init__(self, filename):
            self.filename = filename

        def save(self, target):
            # should not be called in this test; if it is, fail deterministically
            raise AssertionError("save() should not be called for invalid file types")

    fake_file = FakeFile("document.txt")
    fake_request = _make_fake_request(
        {"scenario": "Other", "competition": None, "loops": None, "all_duration": None},
        [fake_file],
    )
    monkeypatch.setattr(m, "request", fake_request)

    # ensure global process registry is empty before invocation
    if hasattr(m, "rdagent_processes"):
        m.rdagent_processes.clear()
    else:
        m.rdagent_processes = {}

    result = m.upload_file()

    # result should be (json_dict, 400)
    assert isinstance(result, tuple) and result[1] == 400
    assert result[0]["error"] == "Invalid file type"


def test_datascience_pdf_success_round_021(tmp_path, monkeypatch):
    """
    Simulate a successful Data Science upload with a PDF file.

    Covers many branches:
    - Data Science special handling (lines ~107-111)
    - file save happy-path (120-131)
    - command composition for Data Science and time-control flags (135-157)
    - subprocess invocation and rdagent_processes population (159-171)
    """
    m = importlib.import_module("rdagent.log.server.app")

    # Use tmp_path as the base log folder
    monkeypatch.setattr(m, "log_folder_path", Path(tmp_path))

    # deterministic name
    monkeypatch.setattr(m.randomname, "get_name", lambda: "rand")

    # deterministic filename sanitization
    monkeypatch.setattr(m, "secure_filename", lambda x: x)

    # jsonify -> identity to inspect returned payload
    monkeypatch.setattr(m, "jsonify", lambda x: x)

    # deterministic server port used in env
    monkeypatch.setattr(m, "server_port", 9999)

    # capture Popen call parameters without launching anything
    popen_calls = []

    def fake_popen(cmd, stdout, stderr, env):
        popen_calls.append({"cmd": cmd, "env": dict(env)})

        class DummyProc:
            pass

        return DummyProc()

    monkeypatch.setattr(m.subprocess, "Popen", fake_popen)

    # prepare a fake PDF file object whose save actually writes to the target path
    class FakePDF:
        def __init__(self, filename):
            self.filename = filename

        def save(self, target_path):
            # target_path will be a pathlib.Path object in this code. Create parent dirs and write.
            p = Path(target_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("pdf-content")

    fake_file = FakePDF("report.pdf")

    # competition string long enough so slicing at [10:] yields meaningful substring
    competition = "MLE-Bench:comp123"

    fake_request = _make_fake_request(
        {
            "scenario": "Data Science",
            "competition": competition,
            "loops": "5",
            "all_duration": "2",
        },
        [fake_file],
    )
    monkeypatch.setattr(m, "request", fake_request)

    # reset process registry
    m.rdagent_processes.clear()

    result = m.upload_file()

    # Expect success tuple (payload, 200)
    assert isinstance(result, tuple) and result[1] == 200
    payload = result[0]
    # trace name is competition[10:] + '-' + random name (rand)
    expected_trace_name = f"{competition[10:]}-rand"
    assert payload["id"] == f"Data Science/{expected_trace_name}"

    # log_trace_path key should be present in rdagent_processes
    expected_log_trace = (Path(tmp_path) / "Data Science" / expected_trace_name).absolute()
    assert str(expected_log_trace) in m.rdagent_processes

    # verify subprocess was invoked and env has expected keys
    assert popen_calls, "subprocess.Popen should have been called"
    call = popen_calls[0]
    assert call["cmd"][0] == "rdagent"
    # Data Science command should include --competition and the sliced competition
    assert "--competition" in call["cmd"] and competition[10:] in call["cmd"]
    assert call["env"]["LOG_TRACE_PATH"] == str(expected_log_trace)
    assert call["env"]["LOG_UI_SERVER_PORT"] == str(9999)

    # Ensure the uploaded pdf actually exists at the expected target
    expected_target = Path(tmp_path) / "Data Science" / "uploads" / expected_trace_name / "report.pdf"
    assert expected_target.exists()
