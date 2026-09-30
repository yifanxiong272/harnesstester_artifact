import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.deep_research.main')
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
        from types import SimpleNamespace
        import asyncio
        import sys
        import io
        import inspect
        import importlib
        import urllib.parse

        # Prepare fake outputs
        fake_report = "# Deep Research Report\n\nContent"

        # Fake async behaviors for the researcher instance
        async def fake_conduct_research(self, on_progress=None):
            # Simulate multiple progress callbacks, one with current_query set and one without
            p1 = SimpleNamespace(
                current_depth=1,
                total_depth=3,
                current_breadth=2,
                total_breadth=4,
                completed_queries=1,
                total_queries=5,
                current_query="What is X?",
            )
            if on_progress:
                on_progress(p1)

            p2 = SimpleNamespace(
                current_depth=3,
                total_depth=3,
                current_breadth=4,
                total_breadth=4,
                completed_queries=5,
                total_queries=5,
                current_query=None,
            )
            if on_progress:
                on_progress(p2)

            # return some dummy context as the real function would
            return {"dummy": "context"}

        async def fake_write_report(self):
            return fake_report

        async def fake_write_md_to_pdf(text: str, filename: str = "") -> str:
            return urllib.parse.quote(f"outputs/{filename[:60]}.pdf")

        # A minimal mock researcher class
        class MockResearcher:
            def __init__(self, query=None, report_type=None):
                self.query = query
                self.report_type = report_type

            conduct_research = fake_conduct_research
            write_report = fake_write_report

        # Find the module that defines the async `main` function
        target_module = None
        # First try the most likely module name
        candidates = ["backend.researcher", "researcher", "backend.research"]
        for name in candidates:
            try:
                mod = importlib.import_module(name)
            except Exception:
                mod = None
            if mod and hasattr(mod, "main") and inspect.iscoroutinefunction(getattr(mod, "main")):
                target_module = mod
                break

        # If not found, scan loaded modules
        if target_module is None:
            for mod in list(sys.modules.values()):
                if not mod:
                    continue
                if hasattr(mod, "main") and inspect.iscoroutinefunction(getattr(mod, "main")):
                    target_module = mod
                    break

        self.assertIsNotNone(target_module, "Could not find a module with an async main function to test")

        # Backup originals (if any) and inject our fakes
        orig_gpt = getattr(target_module, "GPTResearcher", None)
        orig_write_pdf = getattr(target_module, "write_md_to_pdf", None)
        try:
            setattr(target_module, "GPTResearcher", MockResearcher)
            setattr(target_module, "write_md_to_pdf", fake_write_md_to_pdf)

            # Import main from that module (already have module reference)
            main = getattr(target_module, "main")

            # Capture stdout
            buf = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(main("Investigate deep topic"))
                finally:
                    loop.close()
            finally:
                sys.stdout = old_stdout

            output = buf.getvalue()

        finally:
            # Restore originals
            if orig_gpt is None and hasattr(target_module, "GPTResearcher"):
                delattr(target_module, "GPTResearcher")
            else:
                setattr(target_module, "GPTResearcher", orig_gpt)
            if orig_write_pdf is None and hasattr(target_module, "write_md_to_pdf"):
                delattr(target_module, "write_md_to_pdf")
            else:
                setattr(target_module, "write_md_to_pdf", orig_write_pdf)

        # Assert that key printed lines from on_progress and final report were produced
        self.assertIn("Starting deep research...", output)
        self.assertIn("Depth: 1/3", output)
        self.assertIn("Breadth: 2/4", output)
        self.assertIn("Queries: 1/5", output)
        self.assertIn("Current query: What is X?", output)
        self.assertIn("Depth: 3/3", output)
        self.assertIn("Final Report:", output)
        self.assertIn(fake_report, output)
