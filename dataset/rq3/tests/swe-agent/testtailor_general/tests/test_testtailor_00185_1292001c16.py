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
        """Stats_single prints correct totals for submitted_ids and resolved (alias) field."""
        fname = f"tmp_test_stats_{id(self)}.json"
        path = Path(fname)
        try:
            data = {"submitted_ids": ["a", "b"], "resolved": ["a"]}
            path.write_text(json.dumps(data))

            with unittest.mock.patch("builtins.print") as mock_print:
                stats_single(path)

            # Two print calls: evaluated and resolved
            self.assertEqual(mock_print.call_count, 2)
            self.assertEqual(mock_print.call_args_list[0][0][0], "Total evaluated: 2")
            self.assertEqual(mock_print.call_args_list[1][0][0], "Total resolved: 1")
        finally:
            try:
                path.unlink()
            except Exception:
                pass
