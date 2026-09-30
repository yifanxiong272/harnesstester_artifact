import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.bundle')
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
        """Creating a Bundle with a hidden tool that doesn't exist in config should raise."""
        # Ensure we can create a temporary directory without top-level imports by using __import__
        tempfile = __import__("tempfile")
        with tempfile.TemporaryDirectory() as tmpname:
            bundle_path = Path(tmpname)
            config = {"tools": {"existing_tool": {}}}
            (bundle_path / "config.yaml").write_text(yaml.safe_dump(config))

            # hidden_tools contains a name not present in config -> should trigger the ValueError branch
            with self.assertRaisesRegex(ValueError, r"Hidden tools .* do not exist in available tools"):
                Bundle(path=bundle_path, hidden_tools=["nonexistent_tool"])
