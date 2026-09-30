import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.compare_runs')
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
    def test_case_01(self):
        """Verify get_resolved reads JSON from the given Path and returns the resolved IDs as a set."""
        p = Path("test_get_resolved_01.json")
        try:
            # write JSON content directly without relying on external imports
            p.write_text('{"resolved": ["id1", "id2", "id3"]}')
            result = get_resolved(p)
            self.assertEqual(result, {"id1", "id2", "id3"})
        finally:
            if p.exists():
                p.unlink()
