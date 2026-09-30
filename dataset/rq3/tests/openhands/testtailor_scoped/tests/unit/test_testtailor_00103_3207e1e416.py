import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.issue_definitions')
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
    def test_set_strategy_updates_internal_strategy(self):
        """set_strategy should replace the internal _strategy reference with the provided one."""
        # Create two distinct mock strategy objects
        original_strategy = MagicMock(name='original_strategy')
        new_strategy = MagicMock(name='new_strategy')

        # Instantiate ServiceContext with the original strategy and no LLM config
        ctx = ServiceContext(original_strategy, None)

        # Sanity check initial strategy is set
        self.assertIs(ctx._strategy, original_strategy)

        # Call set_strategy to replace it
        ctx.set_strategy(new_strategy)

        # Verify the internal _strategy was updated to the new object
        self.assertIs(ctx._strategy, new_strategy)
