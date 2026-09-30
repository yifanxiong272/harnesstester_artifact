import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.mle_summary')
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
        """Call save_grade_info on an empty temporary log folder while patching
        get_test_eval to avoid heavy initialization (e.g. MLE env). This ensures
        we exercise the beginning of save_grade_info quickly."""
        tempfile = __import__("tempfile")
        td = tempfile.TemporaryDirectory()
        try:
            log_path = Path(td.name) / "logs"
            log_path.mkdir(parents=True, exist_ok=True)

            # Patch get_test_eval in the save_grade_info globals to a lightweight stub
            original_get_test_eval = save_grade_info.__globals__.get("get_test_eval")

            def fake_get_test_eval():
                class FakeEval:
                    def eval(self, competition, workspace):
                        return "fake-score"
                return FakeEval()

            save_grade_info.__globals__["get_test_eval"] = fake_get_test_eval

            # Should not raise and should return quickly
            save_grade_info(log_path)

            # the folder should still exist
            self.assertTrue(log_path.exists() and log_path.is_dir())
        finally:
            # restore original function and cleanup
            if original_get_test_eval is None:
                save_grade_info.__globals__.pop("get_test_eval", None)
            else:
                save_grade_info.__globals__["get_test_eval"] = original_get_test_eval
            td.cleanup()
