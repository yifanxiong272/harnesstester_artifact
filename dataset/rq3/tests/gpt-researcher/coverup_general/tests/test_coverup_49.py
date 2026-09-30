# file: backend/server/logging_config.py:7-36
# asked: {"lines": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22, 23, 24, 25, 26, 28, 30, 31, 32, 34, 35, 36], "branches": []}
# gained: {"lines": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22, 23, 24, 25, 26, 28, 30, 31, 32, 34, 35, 36], "branches": []}

import json
import os
import importlib.util
from pathlib import Path

import pytest


def _import_logging_config_module():
    # Search for the logging_config.py file in the repository tree
    cwd = Path.cwd()
    candidates = list(cwd.rglob("logging_config.py"))
    if not candidates:
        raise FileNotFoundError("Could not find logging_config.py in repository tree")
    # Prefer a path that contains backend/server if present
    chosen = None
    for p in candidates:
        if "backend" in str(p.parts) and "server" in str(p.parts):
            chosen = p
            break
    if chosen is None:
        chosen = candidates[0]

    spec = importlib.util.spec_from_file_location("logging_config_for_tests", chosen)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_init_update_and_file_written(tmp_path):
    logging_config_module = _import_logging_config_module()
    JSONResearchHandler = logging_config_module.JSONResearchHandler

    # Arrange: create a temporary json file path
    json_file = tmp_path / "research.json"

    # Act: create handler and update content to trigger save
    handler = JSONResearchHandler(str(json_file))
    # initial state checks
    assert isinstance(handler.research_data, dict)
    assert "timestamp" in handler.research_data
    assert handler.research_data["events"] == []
    assert "content" in handler.research_data

    # update a known key and trigger save
    handler.update_content("query", "what is the capital of France?")
    handler.update_content("costs", 3.1415)

    # Assert: file was created and contains valid JSON matching handler.research_data
    assert json_file.exists(), "JSON file should have been created by update_content"
    loaded = json.loads(json_file.read_text())
    # timestamp will be a string; ensure keys and values updated are present
    assert "timestamp" in loaded
    assert loaded["content"]["query"] == "what is the capital of France?"
    assert loaded["content"]["costs"] == 3.1415
    # events should still be empty in this test
    assert loaded["events"] == []


def test_log_event_and_monkeypatched_json_dump(tmp_path, monkeypatch):
    logging_config_module = _import_logging_config_module()
    JSONResearchHandler = logging_config_module.JSONResearchHandler

    # Arrange: create a temporary json file path
    json_file = tmp_path / "events.json"
    handler = JSONResearchHandler(str(json_file))

    # We'll monkeypatch json.dump used inside the module to verify it's invoked
    calls = []

    def fake_dump(obj, f, indent=None):
        # Record that dump was called and write a distinct marker to the file
        calls.append(("called", indent, isinstance(obj, dict)))
        f.write("<<FAKE_JSON_DUMP>>")

    # Patch the json.dump used in the target module (not the global json)
    monkeypatch.setattr(logging_config_module.json, "dump", fake_dump)

    # Act: log an event which will call the patched _save_json -> fake_dump
    handler.log_event("test_event", {"value": 123})
    handler.log_event("another_event", {"nested": {"a": 1}})

    # Assert: our fake_dump was called for each save (two log_event calls)
    assert len(calls) == 2
    for call in calls:
        assert call[0] == "called"
        # indent was passed as 2 in implementation
        assert call[1] == 2
        assert call[2] is True  # obj passed was a dict

    # The file should exist and contain the marker written by fake_dump
    assert json_file.exists()
    content = json_file.read_text()
    assert "<<FAKE_JSON_DUMP>>" in content

    # Also verify the handler's in-memory events list grew accordingly
    assert len(handler.research_data["events"]) == 2
    types = [e["type"] for e in handler.research_data["events"]]
    assert types == ["test_event", "another_event"]

    # Clean up: remove file explicitly
    try:
        os.remove(str(json_file))
    except OSError:
        pass
