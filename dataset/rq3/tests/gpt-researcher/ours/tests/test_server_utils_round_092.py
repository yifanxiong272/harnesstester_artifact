import asyncio
import json
import os
import importlib
import pytest

import backend.server.server_utils as sut

@pytest.mark.asyncio
async def test_handle_start_command_missing_task_round_092(capsys, monkeypatch):
    """
    When extract_command_data returns missing task/report_type, the function should print
    the error message and return early without calling manager.start_streaming.
    """
    # Prepare data string such that sut.json.loads(data[6:]) will be valid JSON
    payload = json.dumps({"irrelevant": True})
    # handle_start_command slices at index 6, so ensure first 6 chars are a prefix and index 6 starts the JSON
    data = "123456" + payload

    # Patch extract_command_data to simulate missing task and report_type
    def fake_extract_command_data(json_data):
        # return tuple with task=None and report_type=None and fillers for other fields
        return (None, None, [], [], "", {}, None, [], False, None, None, None)

    monkeypatch.setattr(sut, "extract_command_data", fake_extract_command_data)

    # Create a manager whose start_streaming would fail the test if called
    class FailingManager:
        async def start_streaming(self, *args, **kwargs):
            raise AssertionError("start_streaming should not be called when task/report_type are missing")

    manager = FailingManager()

    # Call the function under test
    await sut.handle_start_command(None, data, manager)

    # Capture stdout and assert error message printed
    captured = capsys.readouterr()
    assert "Error: Missing task or report_type" in captured.out


@pytest.mark.asyncio
async def test_handle_start_command_happy_flow_round_092(monkeypatch):
    """
    Exercise the branch where task and report_type are provided. Validate that:
    - manager.start_streaming is called with expected parameters,
    - logs_handler.send_json is invoked to initialize logs,
    - generate_report_files and send_file_paths are awaited and send_file_paths receives
      a file_paths dict that includes the json path derived from logs_handler.log_file.
    """
    # Deterministic time for sanitize_filename
    monkeypatch.setattr(sut.time, "time", lambda: 1234567890)

    # Prepare data string (6-char prefix so data[6:] == payload)
    payload = json.dumps({"irrelevant": False})
    data = "ABCDEF" + payload

    # Prepare values to be returned by extract_command_data
    task = "my task"
    report_type = "full"
    source_urls = ["http://a"]
    document_urls = ["http://b"]
    tone = "neutral"
    headers = {"h": "v"}
    report_source = "web"
    query_domains = ["example.com"]
    mcp_enabled = False
    mcp_strategy = None
    mcp_configs = None
    max_search_results = 5

    def fake_extract_command_data(json_data):
        return (
            task,
            report_type,
            source_urls,
            document_urls,
            tone,
            headers,
            report_source,
            query_domains,
            mcp_enabled,
            mcp_strategy,
            mcp_configs,
            max_search_results,
        )

    monkeypatch.setattr(sut, "extract_command_data", fake_extract_command_data)

    # Capture created logs handler instances
    created_handlers = []

    class FakeLogsHandler:
        def __init__(self, websocket, task_arg):
            # store the created instance for assertions
            self.websocket = websocket
            self.task = task_arg
            # log file path used later by function
            self.log_file = os.path.join(os.getcwd(), "fake_logs.json")
            created_handlers.append(self)

        async def send_json(self, data):
            # Save the data that was sent for later assertions
            self.sent_data = data

    monkeypatch.setattr(sut, "CustomLogsHandler", FakeLogsHandler)

    # Manager that records its call
    class RecordingManager:
        def __init__(self):
            self.called = False
            self.args = None
            self.kwargs = None

        async def start_streaming(self, *args, **kwargs):
            self.called = True
            self.args = args
            self.kwargs = kwargs
            # return a non-string object to ensure code casts to str on its own
            return {"ok": True}

    manager = RecordingManager()

    # Patch generate_report_files to assert it receives a string report and return predictable files
    async def fake_generate_report_files(report, sanitized_filename):
        # report should have been cast to str in the function under test
        assert isinstance(report, str)
        # return some initial file paths (json will be overwritten by function under test)
        return {"pdf": "out.pdf", "word": "out.docx"}

    monkeypatch.setattr(sut, "generate_report_files", fake_generate_report_files)

    # Capture calls to send_file_paths
    send_calls = []

    async def fake_send_file_paths(websocket, file_paths):
        send_calls.append((websocket, file_paths))

    monkeypatch.setattr(sut, "send_file_paths", fake_send_file_paths)

    # Call the function under test
    websocket_obj = object()
    await sut.handle_start_command(websocket_obj, data, manager)

    # Assertions
    # manager.start_streaming should have been called once with parameters matching the extract_command_data values
    assert manager.called is True
    # The first two positional args should be task and report_type per function signature
    assert manager.args[0] == task
    assert manager.args[1] == report_type
    # The websocket passed to start_streaming should be the same websocket object
    assert manager.args[6] == websocket_obj

    # Check that a logs handler was created and its send_json initialized logs with the task
    assert len(created_handlers) == 1
    handler = created_handlers[0]
    assert hasattr(handler, "sent_data")
    assert handler.sent_data["query"] == task
    assert handler.sent_data["sources"] == []
    assert handler.sent_data["context"] == []

    # send_file_paths should have been called with the file_paths dictionary
    assert len(send_calls) == 1
    sent_websocket, sent_file_paths = send_calls[0]
    assert sent_websocket is websocket_obj

    # The function under test should add/override the "json" key with the relative path of the logs handler log_file
    expected_json_path = os.path.relpath(handler.log_file)
    assert sent_file_paths["json"] == expected_json_path
