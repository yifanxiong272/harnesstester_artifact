import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.azure_devops.service.branches')
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
        """Repository string with fewer than 3 parts raises ValueError."""
        # Use a plain object as self; the coroutine raises before using self
        dummy_self = object()
        bad_repo = "organization/project"  # only 2 parts -> should trigger ValueError

        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            with self.assertRaises(ValueError):
                loop.run_until_complete(
                    AzureDevOpsBranchesMixin.get_branches(dummy_self, bad_repo)
                )
        finally:
            loop.close()
