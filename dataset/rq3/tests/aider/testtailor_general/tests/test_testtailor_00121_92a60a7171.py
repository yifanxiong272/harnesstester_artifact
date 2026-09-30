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
        """ContextCoder.__init__ should update repo_map attributes when repo_map is present.
        Monkeypatch the parent Coder.__init__ to avoid needing real constructor args.
        """
        # prepare a minimal repo_map-like object
        RepoMap = type("RepoMap", (), {})  # simple dynamic class
        repo = RepoMap()
        repo.refresh = None
        repo.max_map_tokens = 100
        repo.map_mul_no_files = 2.5

        # create a ContextCoder instance without calling real Coder.__init__
        coder = object.__new__(ContextCoder)
        coder.repo_map = repo

        # monkeypatch the parent Coder.__init__ so super().__init__ is a no-op
        parent = ContextCoder.__mro__[1]
        orig_parent_init = parent.__init__
        parent.__init__ = lambda self, *a, **k: None
        try:
            # call ContextCoder.__init__ which will call the monkeypatched super().__init__
            ContextCoder.__init__(coder)
        finally:
            # restore original parent __init__ no matter what
            parent.__init__ = orig_parent_init

        # after initialization the target lines should have executed
        self.assertEqual(coder.repo_map.refresh, "always")
        self.assertAlmostEqual(coder.repo_map.max_map_tokens, 100 * 2.5)
        self.assertEqual(coder.repo_map.map_mul_no_files, 1.0)
