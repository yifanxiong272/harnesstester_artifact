import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.report_store')
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
        """Ensure reading an existing JSON file triggers json.loads(...) path."""
        # Use a file in the current working directory to avoid relying on tempfile import
        path = Path.cwd() / "reports_test.json"
        try:
            if path.exists():
                path.unlink()
            # Prepare a valid JSON file that maps report ids to report dicts
            original = {"report-1": {"value": 42, "name": "test"}}
            path.write_text(json.dumps(original), encoding="utf-8")

            store = ReportStore(path)

            # Call get_report which will call _read_all_unlocked and exercise json.loads(...)
            result = asyncio.run(store.get_report("report-1"))
            self.assertEqual(result, original["report-1"])

            # Also verify list_reports reads the file and returns the stored report
            all_reports = asyncio.run(store.list_reports())
            self.assertEqual(all_reports, [original["report-1"]])
        finally:
            # Clean up the file created for the test
            if path.exists():
                path.unlink()
