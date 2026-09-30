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
        """Ensure write_report handles missing available_images and sends research images before generating report."""
        # Prepare fake async helpers and capture data
        calls = []
        last_generate_kwargs = {}

        async def fake_stream_output(*args, **kwargs):
            # record the call arguments to inspect later
            calls.append(args)

        async def fake_generate_report(**kwargs):
            # capture kwargs passed to generate_report and return a sentinel report
            last_generate_kwargs.update(kwargs)
            return "FAKE_REPORT"

        # Build a minimal fake researcher with required attributes and a research image
        class FakeCfg:
            def __init__(self):
                self.agent_role = None

        class FakeResearcher:
            def __init__(self):
                self.query = "test query"
                self.cfg = FakeCfg()
                self.role = "test role"
                self.report_type = "full_report"
                self.report_source = "src"
                self.tone = "neutral"
                self.websocket = None
                self.headers = []
                self.verbose = True
                self.context = {"some": "context"}
                self.parent_query = "parent"
                self.kwargs = {}
                self.add_costs = lambda *a, **k: None
                self.prompt_family = "family"
                self.subtopics = []

            def get_research_images(self):
                return [{"id": "img1", "url": "http://example.com/img1.png"}]

        researcher = FakeResearcher()
        # Instantiate the ReportGenerator from the module under test
        rg = ReportGenerator(researcher)

        # Monkeypatch the module where ReportGenerator is defined
        import sys
        mod = sys.modules[rg.__class__.__module__]
        orig_stream_output = getattr(mod, "stream_output", None)
        orig_generate_report = getattr(mod, "generate_report", None)
        try:
            setattr(mod, "stream_output", fake_stream_output)
            setattr(mod, "generate_report", fake_generate_report)

            # Run the async write_report method
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    rg.write_report(existing_headers=["H1"], relevant_written_contents=["C1"], ext_context=None, custom_prompt="cp", available_images=None)
                )
            finally:
                loop.close()

            # Assertions:
            # 1) stream_output was called with selected_images (research images sent prior)
            assert any(len(call) > 1 and call[1] == "selected_images" for call in calls), f"Expected a selected_images stream_output call, got calls: {calls}"

            # 2) generate_report received available_images as an empty list (defaulting behavior)
            assert "available_images" in last_generate_kwargs, "generate_report did not receive available_images"
            assert last_generate_kwargs["available_images"] == [], f"Expected available_images == [], got {last_generate_kwargs['available_images']}"

            # 3) The returned report is what our fake_generate_report returned
            assert result == "FAKE_REPORT", f"Unexpected report returned: {result}"

        finally:
            # Restore originals
            if orig_stream_output is not None:
                setattr(mod, "stream_output", orig_stream_output)
            else:
                try:
                    delattr(mod, "stream_output")
                except Exception:
                    pass
            if orig_generate_report is not None:
                setattr(mod, "generate_report", orig_generate_report)
            else:
                try:
                    delattr(mod, "generate_report")
                except Exception:
                    pass
