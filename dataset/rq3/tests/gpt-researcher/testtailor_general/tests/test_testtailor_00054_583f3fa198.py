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
        """Ensure parent directory is created when writing a report."""
        tempfile = __import__('tempfile')
        pathlib = __import__('pathlib')
        Path = pathlib.Path
        json = __import__('json')
        asyncio = __import__('asyncio')

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "some" / "nested" / "dir" / "reports.json"
            # parent should not exist yet
            self.assertFalse(path.parent.exists())
            store = ReportStore(path)
            report_id = "r1"
            report = {"a": 1}
            # perform the upsert which should trigger _ensure_parent_dir()
            asyncio.run(store.upsert_report(report_id, report))
            # parent directory must now exist and file must be written
            self.assertTrue(path.parent.exists())
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(report_id, data)
            self.assertEqual(data[report_id], report)
