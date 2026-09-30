import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.deep_research')
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
        """Ensure _load_repaired_json logs when json_repair.loads fails on the first
        candidate and then succeeds on a later extracted payload."""
        # Import the module under test without using an import statement at top-level.
        deep_research_module = __import__("gpt_researcher.skills.deep_research", fromlist=["*"])

        # response.strip() will be the first candidate (intentionally broken),
        # the JSON fence payload will be the second candidate (valid JSON).
        response = 'BROKEN_FIRST_CANDIDATE\n```json\n{"ok": true}\n```'

        def fake_loads(candidate):
            # Fail for the first candidate (the full response.strip()), succeed for the payload.
            if candidate == response.strip():
                raise ValueError("simulated parse error")
            return {"ok": True}

        # Patch json_repair.loads to raise on the first candidate then return a dict
        with unittest.mock.patch.object(deep_research_module.json_repair, "loads", side_effect=fake_loads):
            # Patch the module logger so we can assert debug was called
            with unittest.mock.patch.object(deep_research_module, "logger") as mock_logger:
                result = deep_research_module._load_repaired_json(response)

                # Should have returned the successfully parsed payload
                self.assertEqual(result, {"ok": True})

                # The logger.debug should have been called for the failing candidate
                mock_logger.debug.assert_called_with(
                    "json_repair failed on candidate (%d chars): %s",
                    len(response.strip()),
                    unittest.mock.ANY,
                )
