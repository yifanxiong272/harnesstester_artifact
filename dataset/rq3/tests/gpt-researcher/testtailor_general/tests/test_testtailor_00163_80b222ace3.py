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
        """Ensure mcp_configs is forwarded into GPTResearcher params when provided."""
        import importlib

        # Try to import the module that defines BasicReport (path found in project)
        mod_names = (
            "backend.report_type.basic_report.basic_report",
            "backend.report_type.basic_report",
            "backend.report_type",
            "report_type",
        )
        module = None
        for name in mod_names:
            try:
                module = importlib.import_module(name)
                # Ensure it actually has BasicReport
                if hasattr(module, "BasicReport"):
                    break
            except Exception:
                module = None
        self.assertIsNotNone(module, "Could not import module containing BasicReport")
        self.assertTrue(hasattr(module, "BasicReport"), "Imported module does not have BasicReport")

        # Save original GPTResearcher (if any) and replace with a fake to avoid heavy init
        original_gpt_researcher = getattr(module, "GPTResearcher", None)
        recorded_kwargs = {}

        class FakeGPTResearcher:
            def __init__(self, **kwargs):
                # record the kwargs passed in so we can assert later
                recorded_kwargs.update(kwargs)

        setattr(module, "GPTResearcher", FakeGPTResearcher)

        try:
            # Instantiate BasicReport with a non-None mcp_configs to exercise the branch
            module.BasicReport(
                query="some query",
                query_domains=["example.com"],
                report_type="report",
                report_source="web",
                source_urls=[],
                document_urls=[],
                tone=None,
                config_path="cfg",
                websocket=object(),
                headers=None,
                mcp_configs={"enabled": True},
                mcp_strategy=None,
                max_search_results=None,
            )

            # Verify that mcp_configs was forwarded into the GPTResearcher constructor kwargs
            self.assertIn("mcp_configs", recorded_kwargs)
            self.assertEqual(recorded_kwargs["mcp_configs"], {"enabled": True})
        finally:
            # Restore original GPTResearcher to avoid side effects on other tests
            if original_gpt_researcher is None:
                try:
                    delattr(module, "GPTResearcher")
                except Exception:
                    # If deletion fails (unlikely), just pass
                    pass
            else:
                setattr(module, "GPTResearcher", original_gpt_researcher)
