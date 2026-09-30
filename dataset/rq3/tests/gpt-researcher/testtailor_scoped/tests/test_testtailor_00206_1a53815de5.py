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
        """Ensure that when pre-generated images are provided and researcher.verbose is True,
        the report generator logs the 'images_available' message and passes available_images
        through to generate_report.
        """
        import asyncio

        # Minimal researcher mock
        class Cfg:
            def __init__(self):
                self.agent_role = None

        class FakeResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = object()
                self.query = "test query"
                self.cfg = Cfg()
                self.role = "tester"
                self.report_type = "normal"
                self.report_source = "src"
                self.tone = "neutral"
                self.headers = []
                self.context = {"k": "v"}
                self.parent_query = "parent"
                self.kwargs = {}
                self.prompt_family = "pf"
                # simple synchronous method as used by write_report
                self.get_research_images = lambda: [{"id": "img1"}]
                self.add_costs = lambda *a, **k: None

        researcher = FakeResearcher()
        gen = ReportGenerator(researcher)

        # capture calls to stream_output and generate_report
        calls = []
        gen_kwargs = {}

        async def fake_stream_output(*args, **kwargs):
            # record positional args for assertions
            calls.append(args)

        async def fake_generate_report(**kwargs):
            gen_kwargs.update(kwargs)
            return "THE_REPORT"

        # Monkeypatch the module-level names used by ReportGenerator.write_report
        func_globals = ReportGenerator.write_report.__globals__
        original_stream = func_globals.get("stream_output")
        original_generate = func_globals.get("generate_report")
        try:
            func_globals["stream_output"] = fake_stream_output
            func_globals["generate_report"] = fake_generate_report

            # Call write_report with a non-empty available_images to trigger the target branch
            loop = asyncio.get_event_loop()
            report = loop.run_until_complete(gen.write_report(available_images=["imgA"]))

            # Assertions
            self.assertEqual(report, "THE_REPORT")

            # There should be at least one stream_output call with 'images_available' as second arg
            found = False
            for call in calls:
                # call is a tuple of positional args; second arg should be the message key
                if len(call) >= 2 and call[1] == "images_available":
                    # the message (third positional arg) should mention pre-generated images and the count 1
                    message = call[2] if len(call) >= 3 else ""
                    self.assertIn("pre-generated images available for embedding", message)
                    self.assertIn("1", message)  # len(available_images) == 1
                    # websocket should be passed as next positional argument
                    self.assertIn(researcher.websocket, call)
                    found = True
            self.assertTrue(found, "Expected a stream_output call with key 'images_available'")

            # generate_report should have received available_images unchanged
            self.assertIn("available_images", gen_kwargs)
            self.assertEqual(gen_kwargs["available_images"], ["imgA"])
        finally:
            # restore originals to avoid side effects
            if original_stream is not None:
                func_globals["stream_output"] = original_stream
            if original_generate is not None:
                func_globals["generate_report"] = original_generate
