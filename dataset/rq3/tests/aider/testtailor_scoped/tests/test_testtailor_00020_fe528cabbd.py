import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.context_coder')
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
        """Ensure ContextCoder.__init__ updates a provided repo_map as expected without passing
        repo_map as a kwarg to the parent Coder.__init__ (which doesn't accept it)."""
        # Create a simple repo_map-like object with the attributes the __init__ manipulates
        class DummyRepoMap:
            pass

        rm = DummyRepoMap()
        rm.refresh = "never"
        rm.max_map_tokens = 100
        rm.map_mul_no_files = 2.5

        # Temporarily patch the parent Coder.__init__ to a no-op so we can set repo_map
        parent = ContextCoder.__mro__[1]
        orig_init = getattr(parent, "__init__", None)

        def dummy_init(self, *args, **kwargs):
            # no-op initializer that won't overwrite repo_map
            return None

        try:
            parent.__init__ = dummy_init

            # Create an instance without calling __init__ so we can inject repo_map first
            coder = object.__new__(ContextCoder)
            coder.repo_map = rm

            # Now call ContextCoder.__init__, which will call our patched parent.__init__
            # and then run the repo_map modification code
            ContextCoder.__init__(coder)

            # The same repo_map object should have been modified in-place
            self.assertIs(coder.repo_map, rm)
            self.assertEqual(rm.refresh, "always")
            # max_map_tokens should be multiplied by the original map_mul_no_files (100 * 2.5 = 250.0)
            self.assertAlmostEqual(rm.max_map_tokens, 250.0)
            # map_mul_no_files should be reset to 1.0
            self.assertEqual(rm.map_mul_no_files, 1.0)
        finally:
            # Restore original initializer to avoid side effects on other tests
            if orig_init is not None:
                parent.__init__ = orig_init
