import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.proposal.model_proposal')
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
        """Ensure QlibModelHypothesisGen calls its superclass __init__ with the scen argument."""
        scen = Mock()
        parent_cls = QlibModelHypothesisGen.__mro__[1]
        with patch.object(parent_cls, "__init__", return_value=None) as mock_parent_init:
            inst = QlibModelHypothesisGen(scen)
            self.assertTrue(mock_parent_init.called)
            # Ensure the scen we passed ended up in the positional args of the parent __init__ call
            called_args = mock_parent_init.call_args[0]
            self.assertTrue(len(called_args) >= 1)
            self.assertIn(scen, called_args)
