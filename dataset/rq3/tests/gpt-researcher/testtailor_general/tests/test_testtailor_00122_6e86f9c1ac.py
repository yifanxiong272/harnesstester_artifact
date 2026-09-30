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
        """Ensure MCP init log is emitted when mcp_enabled is True and mcp_configs is non-empty."""
        # Prepare module where run_agent is defined
        module = __import__(run_agent.__module__, fromlist=["*"])

        # Backup originals to restore later
        orig_CustomLogsHandler = getattr(module, "CustomLogsHandler", None)
        orig_run_multi_agent_task = getattr(module, "run_multi_agent_task", None)

        # Create a fake logs handler to capture send_json payload
        class FakeLogsHandler:
            instances = []

            def __init__(self, websocket, task):
                self.websocket = websocket
                self.task = task
                self.sent = None
                FakeLogsHandler.instances.append(self)

            async def send_json(self, data):
                # store the payload for assertions
                self.sent = data
                return None

        # Create a fake run_multi_agent_task to satisfy the multi_agents path
        async def fake_run_multi_agent_task(*args, **kwargs):
            return {"report": "fake_report"}

        # Patch the module objects
        setattr(module, "CustomLogsHandler", FakeLogsHandler)
        setattr(module, "run_multi_agent_task", fake_run_multi_agent_task)

        try:
            # Call run_agent with MCP enabled and non-empty mcp_configs to trigger the target code
            mcp_configs = [{"url": "http://localhost:1234"}]
            mcp_strategy = "fast"

            result = __import__("asyncio").get_event_loop().run_until_complete(
                run_agent(
                    task="test task",
                    report_type="multi_agents",
                    report_source="source",
                    source_urls=[],
                    document_urls=[],
                    tone=Tone.Objective,
                    websocket=None,
                    stream_output=None,
                    headers=None,
                    query_domains=[],
                    config_path="",
                    return_researcher=False,
                    mcp_enabled=True,
                    mcp_strategy=mcp_strategy,
                    mcp_configs=mcp_configs,
                    max_search_results=None,
                )
            )

            # Validate the returned report came from our fake run_multi_agent_task
            self.assertEqual(result, "fake_report")

            # Ensure our FakeLogsHandler was instantiated and captured the MCP init log
            self.assertTrue(FakeLogsHandler.instances)
            inst = FakeLogsHandler.instances[-1]
            expected_output = f"🔧 MCP enabled with strategy '{mcp_strategy}' and {len(mcp_configs)} server(s)"
            expected_payload = {
                "type": "logs",
                "content": "mcp_init",
                "output": expected_output,
            }
            self.assertEqual(inst.sent, expected_payload)

        finally:
            # Restore patched attributes
            if orig_CustomLogsHandler is not None:
                setattr(module, "CustomLogsHandler", orig_CustomLogsHandler)
            else:
                delattr(module, "CustomLogsHandler")
            if orig_run_multi_agent_task is not None:
                setattr(module, "run_multi_agent_task", orig_run_multi_agent_task)
            else:
                delattr(module, "run_multi_agent_task")
