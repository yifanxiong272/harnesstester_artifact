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
    def test_case_XX(self):
        """Create two JSON result files and run compare_many to exercise evaluated_ids/resolved_ids."""
        dir = Path(f"tmp_compare_many_{id(self)}")
        try:
            dir.mkdir(exist_ok=True)
            p1 = dir / "r1.json"
            p2 = dir / "r2.json"

            # First file: two submitted ids, only one resolved (uses "resolved" key)
            p1.write_text(json.dumps({
                "submitted_ids": ["id1", "id2"],
                "resolved": ["id1"]
            }))

            # Second file: only one submitted id, resolved via "resolved_ids" key
            p2.write_text(json.dumps({
                "submitted_ids": ["id1"],
                "resolved_ids": ["id1"]
            }))

            # Call the function under test; it should run without raising.
            result = compare_many([p1, p2])
            self.assertIsNone(result)
        finally:
            # clean up files and directory
            for p in (p1, p2):
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass
            try:
                if dir.exists():
                    dir.rmdir()
            except Exception:
                pass
