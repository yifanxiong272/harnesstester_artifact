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
        """Ensure branch where report_params['agent_role_prompt'] is falsy sets it from cfg.agent_role or role."""
        import asyncio
        import sys
        import types

        # Minimal fake config and researcher to satisfy ReportGenerator expectations
        class Cfg:
            def __init__(self, agent_role=None):
                self.agent_role = agent_role

        class FakeResearcher:
            def __init__(self):
                self.query = "test query"
                self.cfg = Cfg(agent_role=None)  # force cfg.agent_role to be falsy
                self.role = "expected_role"
                self.report_type = "full_report"
                self.report_source = "unit_test"
                self.tone = "neutral"
                self.websocket = None
                self.headers = []
                self.verbose = False
                self.parent_query = None
                self.context = {"some": "context"}
                self.kwargs = {}
                self.prompt_family = "default"
                self.subtopics = []
            def get_research_images(self):
                return None
            def add_costs(self, *args, **kwargs):
                pass

        researcher = FakeResearcher()

        # Instantiate ReportGenerator
        rg = ReportGenerator(researcher)

        # Force the stored report_params agent_role_prompt to a falsy value to trigger the branch
        rg.research_params["agent_role_prompt"] = ""  # falsy

        # Prepare to patch the module-level generate_report to capture the passed params
        captured = {}
        async def fake_generate_report(**kwargs):
            captured.update(kwargs)
            return "GENERATED_REPORT"

        # Patch the module where ReportGenerator is defined
        mod = sys.modules[ReportGenerator.__module__]
        original_generate_report = getattr(mod, "generate_report", None)
        setattr(mod, "generate_report", fake_generate_report)

        try:
            # Call write_report (which should call our fake_generate_report)
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(rg.write_report())

            # Assertions
            self.assertEqual(result, "GENERATED_REPORT")
            # The branch should have set agent_role_prompt to researcher.cfg.agent_role or researcher.role
            self.assertIn("agent_role_prompt", captured)
            self.assertEqual(captured["agent_role_prompt"], researcher.cfg.agent_role or researcher.role)
        finally:
            # Restore original generate_report if present
            if original_generate_report is not None:
                setattr(mod, "generate_report", original_generate_report)
            else:
                delattr(mod, "generate_report")
