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
        """Ensure CustomLogsHandler is instantiated with the provided websocket and task,
        and that the logs handler is passed into run_multi_agent_task."""
        task = "investigate the widget"
        fake_websocket = MagicMock(name="websocket-mock")

        # Determine the module where run_agent is defined so we can patch symbols there
        target_module = run_agent.__module__

        # Patch CustomLogsHandler and run_multi_agent_task in the run_agent's module
        async_mock_result = {"report": "multi-agent report"}
        with patch(f"{target_module}.CustomLogsHandler") as MockLogsHandler, patch(
            f"{target_module}.run_multi_agent_task", new=AsyncMock(return_value=async_mock_result)
        ) as mock_multi_agent:
            # Configure the CustomLogsHandler instance that will be returned
            mock_logs_handler_instance = MagicMock(name="logs-handler-instance")
            MockLogsHandler.return_value = mock_logs_handler_instance

            # Call the async function
            result = asyncio.run(
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
                    mcp_enabled=False,
                )
            )

            # Assert CustomLogsHandler was instantiated with the original websocket and task
            MockLogsHandler.assert_called_once_with(fake_websocket, task)

            # Assert run_multi_agent_task was awaited with the logs handler (not the raw websocket)
            mock_multi_agent.assert_awaited_once_with(
                query=task,
                websocket=mock_logs_handler_instance,
                stream_output=False,
                tone=Tone.Objective,
                headers=None,
            )

            # The function should return the "report" value from the multi-agent task result
            self.assertEqual(result, "multi-agent report")
