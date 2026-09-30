# file: rdagent/log/server/app.py:96-178
# asked: {"lines": [100, 101, 102, 103, 104, 107, 108, 109, 111, 112, 114, 115, 116, 117, 120, 121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 133, 135, 136, 137, 138, 139, 140, 141, 142, 143, 145, 146, 147, 148, 149, 150, 153, 154, 155, 156, 157, 159, 160, 161, 162, 163, 164, 165, 167, 168, 171, 172, 173, 174, 177], "branches": [[107, 108], [107, 111], [116, 117], [116, 120], [120, 121], [120, 135], [121, 120], [121, 122], [125, 126], [125, 128], [128, 129], [128, 133], [129, 130], [129, 131], [135, 136], [135, 137], [137, 138], [137, 139], [139, 140], [139, 141], [141, 142], [141, 147], [142, 143], [142, 145], [147, 148], [147, 149], [149, 150], [149, 153], [153, 154], [153, 156], [154, 155], [154, 156], [156, 157], [156, 159]]}
# gained: {"lines": [100, 101, 102, 103, 104, 107, 111, 112, 114, 115, 116, 117, 120, 121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 135, 137, 138, 139, 141, 142, 143, 146, 147, 149, 153, 154, 155, 156, 157, 159, 160, 161, 162, 163, 164, 165, 167, 168, 171, 172, 173, 174, 177], "branches": [[107, 111], [116, 117], [120, 121], [120, 135], [121, 122], [125, 126], [125, 128], [128, 129], [129, 130], [135, 137], [137, 138], [137, 139], [139, 141], [141, 142], [141, 147], [142, 143], [147, 149], [149, 153], [153, 154], [153, 156], [154, 155], [156, 157]]}

import io
import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture
def appmod(monkeypatch, tmp_path):
    # Import the module under test
    mod = importlib.import_module("rdagent.log.server.app")

    # Isolate and configure module-level state
    monkeypatch.setattr(mod, "log_folder_path", Path(tmp_path))
    monkeypatch.setattr(mod, "rdagent_processes", {})
    monkeypatch.setattr(mod, "server_port", 12345)
    # Ensure randomname.get_name predictable
    monkeypatch.setattr(mod.randomname, "get_name", lambda: "randname")

    return mod


def test_invalid_file_type_returns_400(appmod):
    client = appmod.app.test_client()

    data = {
        "scenario": "Some Scenario",
        "competition": "",
        "loops": "",
        "all_duration": "",
        # single non-pdf file
        "files": (io.BytesIO(b"not a pdf"), "bad.txt"),
    }
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    j = resp.get_json()
    assert j == {"error": "Invalid file type"}
    # ensure no process was started
    assert appmod.rdagent_processes == {}


def test_finance_reports_creates_process_and_stdout(appmod, monkeypatch, tmp_path):
    client = appmod.app.test_client()

    captured = {}

    # stub Popen to capture args/env and return a simple object
    def fake_popen(cmds, stdout, stderr, env):
        captured["cmds"] = cmds
        captured["env"] = env
        class Dummy:
            pass
        return Dummy()

    monkeypatch.setattr(appmod.subprocess, "Popen", fake_popen)

    # Provide a PDF file so saving proceeds
    file_content = b"%PDF-1.4 test"
    data = {
        "scenario": "Finance Data Building (Reports)",
        "competition": "",  # not used for this scenario
        "loops": "5",  # should be ignored for this scenario
        "all_duration": "2",
        "files": (io.BytesIO(file_content), "report.pdf"),
    }
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    j = resp.get_json()
    # trace_name is randomname.get_name() which we set to "randname"
    assert j["id"].startswith("Finance Data Building (Reports)/randname")

    # Ensure process was recorded
    # There should be exactly one key in rdagent_processes
    assert len(appmod.rdagent_processes) == 1
    log_trace_path_str = list(appmod.rdagent_processes.keys())[0]
    # Confirm that LOG_TRACE_PATH in env matches that key
    assert "LOG_TRACE_PATH" in captured["env"]
    assert captured["env"]["LOG_TRACE_PATH"] == log_trace_path_str

    # For Reports scenario, --report_folder should be present and --loop_n should NOT be present
    assert "--report_folder" in captured["cmds"]
    assert "--loop_n" not in captured["cmds"]
    # all_duration should have been added as --timeout 2h
    assert "--timeout" in captured["cmds"]
    idx = captured["cmds"].index("--timeout")
    assert captured["cmds"][idx + 1] == "2h"

    # stdout file should have been created
    # stdout path is log_folder_path / scenario / f"{trace_name}.stdout"
    parts = log_trace_path_str.split(os.path.sep)
    # last two parts are scenario and trace_name
    scenario = parts[-2]
    trace_name = parts[-1]
    stdout_path = Path(appmod.log_folder_path) / scenario / f"{trace_name}.stdout"
    assert stdout_path.exists()
    # Ensure uploaded PDF file was saved under uploads/<trace_name>/
    saved_pdf = Path(appmod.log_folder_path) / scenario / "uploads" / trace_name / "report.pdf"
    assert saved_pdf.exists()
    # Check file content matches what we uploaded
    assert saved_pdf.read_bytes() == file_content


def test_general_model_no_files_uses_form_link_as_rfp(appmod, monkeypatch):
    client = appmod.app.test_client()

    captured = {}

    def fake_popen(cmds, stdout, stderr, env):
        captured["cmds"] = cmds
        captured["env"] = env
        class Dummy:
            pass
        return Dummy()

    monkeypatch.setattr(appmod.subprocess, "Popen", fake_popen)

    # Do not send any actual files in request.files; provide form 'files' string instead
    data = {
        "scenario": "General Model Implementation",
        # form 'files' present; code will do request.form.get('files')[0]
        "files": "some/path/to/report.pdf",
        "loops": "3",
        "all_duration": "1",
    }
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["id"].startswith("General Model Implementation/randname")

    # Ensure cmd includes expected general_model and report_file_path with rfp being first char of the form string
    assert "general_model" in captured["cmds"]
    # find --report_file_path and its next value
    assert "--report_file_path" in captured["cmds"]
    idx = captured["cmds"].index("--report_file_path")
    # Per code, when files list is empty rfp = request.form.get("files")[0] -> first character
    expected_rfp = data["files"][0]
    assert captured["cmds"][idx + 1] == expected_rfp

    # loops should be appended (since scenario != Finance Data Building (Reports))
    assert "--loop_n" in captured["cmds"]
    ln_idx = captured["cmds"].index("--loop_n")
    assert captured["cmds"][ln_idx + 1] == "3"
    # timeout should be appended as well
    assert "--timeout" in captured["cmds"]
    to_idx = captured["cmds"].index("--timeout")
    assert captured["cmds"][to_idx + 1] == "1h"

    # ensure process recorded
    assert len(appmod.rdagent_processes) == 1
