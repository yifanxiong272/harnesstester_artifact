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
        """Ensure ContextCoder.__init__ returns early when self.repo_map is falsy."""
        # retrieve the ContextCoder parent class (expected to be Coder) and stub its __init__
        parent = ContextCoder.__mro__[1]
        orig_init = getattr(parent, "__init__", None)
        try:
            # Make parent's __init__ a no-op so we can control instance attributes without side effects
            parent.__init__ = lambda self, *a, **k: None

            # Create an instance without calling the real __init__ (to avoid unwanted behavior),
            # but ensure repo_map is present and falsy so the branch `if not self.repo_map: return` is taken.
            inst = object.__new__(ContextCoder)
            inst.repo_map = None

            # Call the ContextCoder.__init__ which should call the stubbed super().__init__
            # and then immediately return because repo_map is falsy.
            ContextCoder.__init__(inst)

            # After initialization returned early, repo_map must remain unchanged (still falsy/None)
            self.assertIsNone(inst.repo_map)
        finally:
            # restore original parent __init__ to avoid affecting other tests
            if orig_init is not None:
                parent.__init__ = orig_init
