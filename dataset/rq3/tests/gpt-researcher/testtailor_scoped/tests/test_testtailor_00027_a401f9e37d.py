import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.websocket_manager')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure CustomLogsHandler is instantiated and used for MCP init when running a multi-agent task."""
        # Save originals to restore later
        orig_custom_logs_handler = run_agent.__globals__.get("CustomLogsHandler")
        orig_run_multi = run_agent.__globals__.get("run_multi_agent_task")

        captured_handler = {"instance": None}

        # Fake logs handler to capture initialization and send_json calls
        class FakeLogsHandler:
            def __init__(self, websocket, task):
                self.websocket = websocket
                self.task = task
                self.sent = []

            async def send_json(self, payload):
                self.sent.append(payload)

        async def fake_run_multi_agent_task(query, websocket, stream_output, tone, headers):
            # The websocket arg here should be the FakeLogsHandler instance created in run_agent
            captured_handler["instance"] = websocket
            # Return structure expected by run_agent
            return {"report": "multi-agent report result"}

        # Patch the globals used by run_agent
        run_agent.__globals__["CustomLogsHandler"] = FakeLogsHandler
        run_agent.__globals__["run_multi_agent_task"] = fake_run_multi_agent_task

        try:
            # Prepare inputs
            task = "investigate X"
            fake_websocket = object()  # arbitrary object passed into CustomLogsHandler
            # Call the coroutine
            result = __import__("asyncio").run(
                run_agent(
                    task=task,
                    report_type="multi_agents",
                    report_source=None,
                    source_urls=[],
                    document_urls=[],
                    tone=Tone.Objective,
                    websocket=fake_websocket,
                    stream_output=False,
                    headers=None,
                    query_domains=[],
                    config_path="",
                    return_researcher=False,
                    mcp_enabled=True,
                    mcp_strategy="fast",
                    mcp_configs=["server-a", "server-b"],
                    max_search_results=None,
                )
            )

            # Assert return value is taken from fake_run_multi_agent_task
            self.assertEqual(result, "multi-agent report result")

            # Assert a FakeLogsHandler was created and passed into the multi-agent runner
            handler = captured_handler["instance"]
            self.assertIsNotNone(handler)
            self.assertIsInstance(handler, FakeLogsHandler)
            # Check the FakeLogsHandler was initialized with the websocket sentinel and the task
            self.assertIs(handler.websocket, fake_websocket)
            self.assertEqual(handler.task, task)

            # Because mcp_enabled was True and mcp_configs contained servers,
            # run_agent should have invoked send_json once with the mcp_init payload
            self.assertEqual(len(handler.sent), 1)
            mcp_msg = handler.sent[0]
            self.assertEqual(mcp_msg.get("type"), "logs")
            self.assertEqual(mcp_msg.get("content"), "mcp_init")
            self.assertIn("MCP enabled", mcp_msg.get("output", "") or "🔧")
            # Ensure the output mentions the strategy and number of servers
            self.assertIn("fast", mcp_msg["output"])
            self.assertIn(str(len(["server-a", "server-b"])), mcp_msg["output"])

        finally:
            # Restore originals
            if orig_custom_logs_handler is not None:
                run_agent.__globals__["CustomLogsHandler"] = orig_custom_logs_handler
            else:
                run_agent.__globals__.pop("CustomLogsHandler", None)
            if orig_run_multi is not None:
                run_agent.__globals__["run_multi_agent_task"] = orig_run_multi
            else:
                run_agent.__globals__.pop("run_multi_agent_task", None)
