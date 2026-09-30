import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.writer')
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
        """Ensure selected research images are sent to stream_output before report generation."""
        async def runner():
            asyncio = __import__("asyncio")
            json = __import__("json")

            research_images = [{"id": "img1", "url": "http://example.com/img1.png"}]

            class DummyCfg:
                agent_role = None

            class DummyResearcher:
                def __init__(self):
                    self.query = "test query"
                    self.cfg = DummyCfg()
                    self.role = "tester"
                    self.report_type = "full_report"
                    self.report_source = "source"
                    self.tone = "neutral"
                    self.websocket = object()
                    self.headers = []
                    self.context = "some context"
                    self.verbose = False  # keep verbose False to avoid extra stream_output calls
                    self.parent_query = "parent"
                    self.kwargs = {}
                    self.prompt_family = None
                    self.subtopics = []

                def get_research_images(self):
                    return research_images

                def add_costs(self, *args, **kwargs):
                    pass

            researcher = DummyResearcher()
            rg = ReportGenerator(researcher)

            # Patch stream_output and generate_report in the module where ReportGenerator is defined
            module_path = ReportGenerator.__module__
            with patch(f"{module_path}.stream_output", new_callable=AsyncMock) as mock_stream, \
                 patch(f"{module_path}.generate_report", new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = "GENERATED_REPORT"

                report = await rg.write_report()

                # verify generate_report result is returned
                self.assertEqual(report, "GENERATED_REPORT")

                # verify stream_output was awaited with the images payload
                mock_stream.assert_awaited_with(
                    "images",
                    "selected_images",
                    json.dumps(research_images),
                    researcher.websocket,
                    True,
                    research_images
                )

        __import__("asyncio").get_event_loop().run_until_complete(runner())
