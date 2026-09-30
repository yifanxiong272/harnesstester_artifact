import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.run_cmd')
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
        """Test get_windows_parent_process_name finds a PowerShell parent and returns None when none match."""
        # First scenario: a parent chain that includes PowerShell
        with patch("psutil.Process") as mock_process:
            current = MagicMock()
            parent1 = MagicMock()
            parent2 = MagicMock()

            # current -> parent1 -> parent2 -> None
            current.parent.return_value = parent1
            parent1.parent.return_value = parent2
            parent2.parent.return_value = None

            parent1.name.return_value = "SomeParent.exe"
            parent2.name.return_value = "PowerShell.exe"

            mock_process.return_value = current

            result = get_windows_parent_process_name()
            self.assertEqual(result, "powershell.exe")

        # Second scenario: a parent chain with no matching names -> should return None
        with patch("psutil.Process") as mock_process:
            current2 = MagicMock()
            a = MagicMock()
            b = MagicMock()

            current2.parent.return_value = a
            a.parent.return_value = b
            b.parent.return_value = None

            a.name.return_value = "one.exe"
            b.name.return_value = "two.exe"

            mock_process.return_value = current2

            result2 = get_windows_parent_process_name()
            self.assertIsNone(result2)
