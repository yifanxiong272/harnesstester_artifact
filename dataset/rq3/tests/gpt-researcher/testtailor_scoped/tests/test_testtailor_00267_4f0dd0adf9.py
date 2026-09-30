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
        """complete the test case here"""
        # Prepare to patch the module-level classes used by run_agent
        module_globals = run_agent.__globals__

        # Save originals to restore later
        original_basic = module_globals.get("BasicReport", None)
        original_custom_logs = module_globals.get("CustomLogsHandler", None)

        # Dummy implementations to exercise the BasicReport path
        class DummyLogsHandler:
            def __init__(self, websocket, task):
                self.websocket = websocket
                self.task = task
                self.sent = []

            async def send_json(self, payload):
                # record payloads for potential inspection
                self.sent.append(payload)

        class DummyBasicReport:
            def __init__(self, *args, **kwargs):
                # mimic an attached researcher for possible return_researcher use
                self.gpt_researcher = "dummy_gpt_researcher"
                self.init_args = args
                self.init_kwargs = kwargs

            async def run(self):
                return "basic_report_result"

        try:
            # Patch into the run_agent module's globals
            module_globals["CustomLogsHandler"] = DummyLogsHandler
            module_globals["BasicReport"] = DummyBasicReport

            # Call the async run_agent function with a non-multi_agents, non-detailed_report type
            asyncio = __import__("asyncio")
            coro = run_agent(
                task="test task",
                report_type="research_report",  # not 'multi_agents' and not 'detailed_report'
                report_source=None,
                source_urls=[],
                document_urls=[],
                tone=None,
                websocket=None,
                # leave other params as defaults
            )
            result = asyncio.get_event_loop().run_until_complete(coro)

            # Verify we took the BasicReport path and got the expected dummy result
            self.assertEqual(result, "basic_report_result")

        finally:
            # Restore originals to avoid side effects on other tests
            if original_basic is None:
                module_globals.pop("BasicReport", None)
            else:
                module_globals["BasicReport"] = original_basic

            if original_custom_logs is None:
                module_globals.pop("CustomLogsHandler", None)
            else:
                module_globals["CustomLogsHandler"] = original_custom_logs
