import os
import subprocess
from pathlib import Path
import importlib
import pytest

# Import the module under test
app_module = importlib.import_module("rdagent.log.server.app")

# Helpers used in tests
class DummyFile:
    def __init__(self, filename, content=b"pdf-data"):
        self.filename = filename

    def save(self, path):
        # Ensure parent exists and write deterministic content
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"saved:" + (self.filename.encode() if isinstance(self.filename, str) else b"file"))


class DummyFilesObj:
    def __init__(self, files_list):
        # files_list is a list of DummyFile
        self._files = files_list

    def getlist(self, key):
        # matches: request.files.getlist("files")
        return list(self._files)


class DummyRequest:
    def __init__(self, form_dict, files_list):
        self._form = dict(form_dict)
        self.files = DummyFilesObj(files_list)

    # mimic Flask request.form.get
    @property
    def form(self):
        class G:
            def __init__(self, d):
                self._d = d

            def get(self, k):
                return self._d.get(k)

        return G(self._form)


class FakePopen:
    def __init__(self, *args, **kwargs):
        # capture invocation details
        self.args = args
        self.kwargs = kwargs
        # expose pid-like attribute for realism
        self.pid = 12345

    def poll(self):
        return None


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    """
    Prepare isolated environment for each test: patch subprocess.Popen, randomname.get_name,
    secure_filename, jsonify to deterministic behaviors, and set module globals like
    log_folder_path, rdagent_processes, server_port to ephemeral values under tmp_path.
    """
    # Ensure deterministic random name
    monkeypatch.setattr(app_module.randomname, "get_name", lambda: "rndname")

    # Ensure secure_filename is identity for deterministic behavior
    # secure_filename is imported into the module namespace; override it there
    monkeypatch.setattr(app_module, "secure_filename", lambda s: s)

    # Avoid using Flask's jsonify which needs app context; return the dict directly
    monkeypatch.setattr(app_module, "jsonify", lambda x: x)

    # Patch Popen to prevent real subprocess spawning
    monkeypatch.setattr(app_module.subprocess, "Popen", FakePopen)

    # Provide isolated storage path and globals
    monkeypatch.setattr(app_module, "log_folder_path", tmp_path)
    monkeypatch.setattr(app_module, "rdagent_processes", {})
    monkeypatch.setattr(app_module, "server_port", 42424)

    yield


def _call_upload_with_request(monkeypatch, request_obj):
    # Attach the dummy request to module
    monkeypatch.setattr(app_module, "request", request_obj)
    # Call upload_file and return its result
    return app_module.upload_file()


def test_data_science_round_021(monkeypatch, tmp_path):
    """Test uploading a valid PDF under 'Data Science' scenario; exercises Data Science branch,
    file-saving path, Popen invocation, and time-control parameters (--loop_n and --timeout).
    """
    scenario = "Data Science"
    # Make competition string that matches expected prefix in code
    competition = "MLE-Bench:comp"  # slicing in code will use [10:]

    # One valid PDF file
    f = DummyFile("report.pdf")

    form = {
        "scenario": scenario,
        "competition": competition,
        "loops": "3",
        "all_duration": "2",
        # ensure request.form.get("files") is present for other branches if needed
        "files": None,
    }

    req = DummyRequest(form, [f])

    # Call and capture response
    resp, status = _call_upload_with_request(monkeypatch, req)

    # Assertions: response id should start with scenario/
    assert status == 200
    assert isinstance(resp, dict)
    assert resp["id"].startswith(f"{scenario}/")

    # The process should have been registered using absolute log_trace_path key
    expected_comp = competition[10:]
    expected_trace_name = f"{expected_comp}-rndname"
    expected_log_trace_path = (tmp_path / scenario / expected_trace_name).absolute()
    key = str(expected_log_trace_path)
    assert key in app_module.rdagent_processes

    # Check Popen received the expected command beginning
    popen_obj = app_module.rdagent_processes[key]
    assert isinstance(popen_obj, FakePopen)
    full_cmd = popen_obj.args[0]
    assert isinstance(full_cmd, list)
    assert full_cmd[0] == "rdagent"
    assert "data_science" in full_cmd
    # loop_n should be included
    assert "--loop_n" in full_cmd
    # timeout should be included and end with 'h'
    assert any(str(a).endswith("h") for a in full_cmd)

    # Environment variables injected as kwargs['env']
    env = popen_obj.kwargs.get("env", {})
    assert env.get("LOG_UI_SERVER_PORT") == str(app_module.server_port)
    assert env.get("LOG_TRACE_PATH") == str(expected_log_trace_path)


def test_invalid_file_type_round_021(monkeypatch, tmp_path):
    """Uploading a non-pdf should return a 400 and not spawn a process.
    This exercises the invalid-file-type early return branch.
    """
    scenario = "General Model Implementation"
    # file with invalid extension
    bad = DummyFile("bad.txt")

    form = {
        "scenario": scenario,
        "competition": None,
        "loops": None,
        "all_duration": None,
        # In this case, provide the uploaded file in request.files
        "files": None,
    }

    req = DummyRequest(form, [bad])
    resp, status = _call_upload_with_request(monkeypatch, req)

    # It should return the JSON-like dict and status 400
    assert status == 400
    assert isinstance(resp, dict)
    assert resp.get("error") == "Invalid file type"

    # Ensure no subprocess was started
    assert app_module.rdagent_processes == {}


def test_finance_reports_round_021(monkeypatch, tmp_path):
    """Test 'Finance Data Building (Reports)' scenario: ensures the --report_folder command is used,
    and that loop_n is NOT appended (special-case), but all_duration still appends --timeout.
    Also exercises path building with no uploaded files (files list empty).
    """
    scenario = "Finance Data Building (Reports)"

    form = {
        "scenario": scenario,
        "competition": None,
        "loops": "5",  # should be ignored for this scenario
        "all_duration": "1",
        # no uploaded files
        "files": None,
    }

    req = DummyRequest(form, [])

    resp, status = _call_upload_with_request(monkeypatch, req)

    assert status == 200
    assert isinstance(resp, dict)
    assert resp["id"].startswith(f"{scenario}/")

    # Check that a process was recorded
    expected_trace_name = "rndname"
    expected_log_trace_path = (tmp_path / scenario / expected_trace_name).absolute()
    key = str(expected_log_trace_path)
    assert key in app_module.rdagent_processes

    popen_obj = app_module.rdagent_processes[key]
    assert isinstance(popen_obj, FakePopen)
    cmd = popen_obj.args[0]
    # Should contain the report-specific command
    assert "fin_factor_report" in cmd
    # Should contain --report_folder with the trace_files_path value
    assert "--report_folder" in cmd
    # loop_n shouldn't be added for this scenario
    assert "--loop_n" not in cmd
    # all_duration should have added timeout with 'h'
    assert any(str(a).endswith("h") for a in cmd)
