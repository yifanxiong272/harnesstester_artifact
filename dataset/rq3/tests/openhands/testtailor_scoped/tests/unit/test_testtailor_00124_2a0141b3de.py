import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.condenser.condenser')
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
        """Ensure get_condensation_metadata returns the condenser metadata stored in state.extra_data when the key is present."""
        # Create a fresh State and inject condenser metadata under the expected key
        state = State()
        condenser_meta = [
            {"forgotten": [1, 2, 3], "summary": "summary of events", "summary_offset": 2}
        ]
        state.extra_data[CONDENSER_METADATA_KEY] = condenser_meta

        # Call the function under test
        result = get_condensation_metadata(state)

        # It should return the exact list we stored (not a copy)
        self.assertIs(result, condenser_meta)
        self.assertEqual(result, condenser_meta)
