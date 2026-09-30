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
        import sys
        import asyncio
        import io
        import contextlib
        import types

        # Resolve module where `main` is defined so we can patch its globals
        mod = sys.modules[main.__module__]

        # Fake researcher to exercise on_progress calls and report generation
        class FakeResearcher:
            def __init__(self, query, report_type):
                self.query = query
                self.report_type = report_type

            async def conduct_research(self, on_progress=None):
                # Simulate progress callbacks
                if on_progress:
                    on_progress(types.SimpleNamespace(
                        current_depth=1,
                        total_depth=2,
                        current_breadth=1,
                        total_breadth=3,
                        completed_queries=0,
                        total_queries=2,
                        current_query="init-query"
                    ))
                    on_progress(types.SimpleNamespace(
                        current_depth=2,
                        total_depth=2,
                        current_breadth=3,
                        total_breadth=3,
                        completed_queries=2,
                        total_queries=2,
                        current_query=""
                    ))
                return {"context": "dummy"}

            async def write_report(self):
                return "# Deep Report\n\nThis is a fake report."

        # Fake write_md_to_pdf to avoid filesystem / external dependency
        async def fake_write_md_to_pdf(text: str, filename: str = "") -> str:
            return "outputs/deep_research_report.pdf"

        # Patch the module-level names, saving originals to restore later
        orig_researcher = getattr(mod, "GPTResearcher", None)
        orig_write_md = getattr(mod, "write_md_to_pdf", None)
        setattr(mod, "GPTResearcher", FakeResearcher)
        setattr(mod, "write_md_to_pdf", fake_write_md_to_pdf)

        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                asyncio.run(main("example deep research task"))
            output = buf.getvalue()

            # Assertions to ensure the path through the target code executed
            self.assertIn("Starting deep research...", output)
            self.assertIn("Depth: 1/2", output)
            self.assertIn("Breadth: 1/3", output)
            self.assertIn("Queries: 0/2", output)
            self.assertIn("Current query: init-query", output)
            self.assertIn("Research completed. Generating report...", output)
            self.assertIn("Final Report:", output)
        finally:
            # Restore original attributes
            if orig_researcher is None:
                if hasattr(mod, "GPTResearcher"):
                    delattr(mod, "GPTResearcher")
            else:
                setattr(mod, "GPTResearcher", orig_researcher)

            if orig_write_md is None:
                if hasattr(mod, "write_md_to_pdf"):
                    delattr(mod, "write_md_to_pdf")
            else:
                setattr(mod, "write_md_to_pdf", orig_write_md)
