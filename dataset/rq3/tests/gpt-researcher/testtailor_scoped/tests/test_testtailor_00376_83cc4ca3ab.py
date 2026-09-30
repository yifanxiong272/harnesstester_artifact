import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.basic_report.basic_report')
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
        """Test that BasicReport.run awaits conduct_research and write_report on gpt_researcher and returns the report."""
        asyncio = __import__("asyncio")

        async def run_test_coroutine():
            # Create a BasicReport instance without calling __init__
            br = object.__new__(BasicReport)

            # Mock researcher with async methods
            class MockResearcher:
                def __init__(self):
                    self.conduct_called = False
                    self.write_called = False

                async def conduct_research(self):
                    self.conduct_called = True
                    # yield control to the event loop
                    await asyncio.sleep(0)

                async def write_report(self):
                    self.write_called = True
                    await asyncio.sleep(0)
                    return {"status": "ok", "content": "test report"}

            mock = MockResearcher()
            br.gpt_researcher = mock

            # Call the async run method under test
            report = await br.run()
            return mock, report

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            mock_researcher, report = loop.run_until_complete(run_test_coroutine())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        self.assertTrue(mock_researcher.conduct_called, "conduct_research was not called")
        self.assertTrue(mock_researcher.write_called, "write_report was not called")
        self.assertEqual(report, {"status": "ok", "content": "test report"})
