import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repomap')
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
        """Ensure get_scm_fname handles a KeyError from resources.files when USING_TSL_PACK is True
        and correctly falls back to the tree-sitter-languages path.
        """
        fn = get_scm_fname
        # Save originals to restore later
        orig_globals = fn.__globals__
        orig_resources = orig_globals.get("resources")
        orig_using = orig_globals.get("USING_TSL_PACK")

        # Sentinel object to be returned by the fallback joinpath
        FALLBACK_SENTINEL = object()

        class FakeFilesObject:
            def joinpath(self, *parts):
                # Return a sentinel indicating the fallback path was used
                return FALLBACK_SENTINEL

        class FakeResources:
            def __init__(self):
                self._calls = 0

            def files(self, package):
                # First call simulates a KeyError (as if the tsl-pack isn't available)
                # Subsequent calls return a FakeFilesObject (the fallback)
                self._calls += 1
                if self._calls == 1:
                    raise KeyError("simulate missing tsl-pack")
                return FakeFilesObject()

        fake_resources = FakeResources()

        try:
            # Inject the fake resources and enable USING_TSL_PACK
            orig_globals["resources"] = fake_resources
            orig_globals["USING_TSL_PACK"] = True

            # Call the function under test. The first resources.files call will raise KeyError,
            # triggering the except/pass branch; the fallback should then be used and returned.
            result = fn("python")

            # Verify that the fallback sentinel was returned
            self.assertIs(result, FALLBACK_SENTINEL)
        finally:
            # Restore originals to avoid side effects on other tests
            if orig_resources is None:
                orig_globals.pop("resources", None)
            else:
                orig_globals["resources"] = orig_resources
            if orig_using is None:
                orig_globals.pop("USING_TSL_PACK", None)
            else:
                orig_globals["USING_TSL_PACK"] = orig_using
