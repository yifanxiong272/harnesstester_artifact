import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
        """When the analytics data file exists but contains invalid JSON,
        load_data should catch the JSONDecodeError and call disable(permanently=False).
        """
        from pathlib import Path
        import tempfile
        from unittest.mock import patch

        # create a temp analytics file with invalid JSON
        tmpdir = Path(tempfile.mkdtemp())
        tmp_file = tmpdir / "analytics.json"
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file.write_text("{ this is : not valid json ")

        # Patch get_data_file_path to point to our temp file so data_file.exists() is True
        with patch.object(Analytics, "get_data_file_path", return_value=tmp_file):
            # Patch disable to observe it's called with permanently=False
            with patch.object(Analytics, "disable") as mock_disable:
                # Instantiating Analytics will call get_or_create_uuid -> load_data,
                # which should attempt to read the invalid JSON and call disable(...)
                a = Analytics()
                # disable may be called more than once during init; ensure at least one call with permanently=False
                self.assertTrue(mock_disable.called)
                mock_disable.assert_any_call(permanently=False)
