import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.proposal.factor_proposal')
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
        """Ensure QlibFactorHypothesisGen calls its superclass __init__ with the Scenario."""
        scen = Mock()
        # The immediate base class of QlibFactorHypothesisGen is at mro()[1]
        base_cls = QlibFactorHypothesisGen.__mro__[1]
        with patch.object(base_cls, "__init__", return_value=None) as mocked_base_init:
            inst = QlibFactorHypothesisGen(scen)
            # verify the super().__init__ was invoked with the scen argument
            mocked_base_init.assert_called_once_with(scen)
            # and an instance of the subclass was created
            self.assertIsInstance(inst, QlibFactorHypothesisGen)
