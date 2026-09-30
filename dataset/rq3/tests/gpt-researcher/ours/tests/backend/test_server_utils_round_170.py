import asyncio
import json
import pytest

from fastapi.responses import JSONResponse
import backend.server.server_utils as server_utils


@pytest.mark.asyncio
async def test_execute_multi_agents_no_ws_round_170():
    """When manager has no active connections, return a 400 JSONResponse with the expected message."""
    class Manager:
        active_connections = []

    manager = Manager()

    result = await server_utils.execute_multi_agents(manager)

    # Should be a JSONResponse with status 400 and the expected content
    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    # JSONResponse.body is bytes; decode and parse
    body_bytes = getattr(result, "body", None)
    assert body_bytes is not None, "JSONResponse should have a body attribute"
    parsed = json.loads(body_bytes.decode())
    assert parsed == {"message": "No active WebSocket connection"}


@pytest.mark.asyncio
async def test_execute_multi_agents_with_ws_round_170(monkeypatch):
    """When there is an active websocket, run_multi_agent_task is awaited and its result is returned under 'report'.

    This test patches run_multi_agent_task to avoid any external calls and also ensures stream_output exists.
    """
    # Prepare a fake websocket object (could be any sentinel)
    fake_ws = object()

    # Ensure stream_output symbol exists in the module so execute_multi_agents can reference it
    def fake_stream_output(*args, **kwargs):
        # No-op stream output for the test
        return None

    monkeypatch.setattr(server_utils, "stream_output", fake_stream_output, raising=False)

    # Capture the arguments passed to run_multi_agent_task and return a predictable report
    captured = {}

    async def fake_run_multi_agent_task(prompt, websocket_arg, stream_output_arg):
        captured['prompt'] = prompt
        captured['websocket'] = websocket_arg
        captured['stream_output'] = stream_output_arg
        # Return a sample report structure
        return {"summary": "fake-report"}

    monkeypatch.setattr(server_utils, "run_multi_agent_task", fake_run_multi_agent_task)

    class Manager:
        active_connections = []

    manager = Manager()
    manager.active_connections = [fake_ws]

    result = await server_utils.execute_multi_agents(manager)

    # The function should return a dict wrapping the report returned by the patched task
    assert result == {"report": {"summary": "fake-report"}}

    # Ensure run_multi_agent_task was called with the expected prompt and websocket
    assert captured.get('prompt') == "Is AI in a hype cycle?"
    assert captured.get('websocket') is fake_ws
    # The third arg should be the stream_output we injected
    assert captured.get('stream_output') is fake_stream_output
