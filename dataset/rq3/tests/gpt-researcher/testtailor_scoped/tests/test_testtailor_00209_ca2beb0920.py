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
        """Test that run_agent uses DetailedReport path and returns (report, researcher.gpt_researcher)."""
        task = "Investigate test query"
        report_type = ReportType.DetailedReport.value  # "detailed_report"
        tone = Tone.Objective

        # Patch DetailedReport and CustomLogsHandler in the module where run_agent is defined
        module_path = run_agent.__module__

        with unittest.mock.patch(f"{module_path}.CustomLogsHandler") as MockLogsHandler, \
             unittest.mock.patch(f"{module_path}.DetailedReport") as MockDetailed:

            # Ensure CustomLogsHandler instantiation returns a harmless object
            logs_handler_obj = object()
            MockLogsHandler.return_value = logs_handler_obj

            # Prepare a mock DetailedReport instance with async run and a gpt_researcher attr
            mock_instance = unittest.mock.AsyncMock()
            mock_instance.run = unittest.mock.AsyncMock(return_value="generated_report")
            mock_instance.gpt_researcher = "gpt_researcher_obj"
            MockDetailed.return_value = mock_instance

            # Run the async function
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                run_agent(
                    task=task,
                    report_type=report_type,
                    report_source=None,
                    source_urls=[],
                    document_urls=[],
                    tone=tone,
                    websocket=None,
                    headers=None,
                    query_domains=[],
                    config_path="",
                    return_researcher=True,
                    mcp_enabled=False,
                )
            )

            # Expect the tuple (report, researcher.gpt_researcher)
            self.assertEqual(result, ("generated_report", "gpt_researcher_obj"))
