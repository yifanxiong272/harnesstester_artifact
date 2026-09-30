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
        """Test the fallback try/except branch of get_scm_fname in the case where
        resources.files returns a path-like object and in the case where it raises KeyError.
        """
        # import the module under test dynamically (no top-level import statements)
        mod = __import__("aider.repomap", fromlist=["get_scm_fname"])

        # preserve original USING_TSL_PACK value
        orig_using = getattr(mod, "USING_TSL_PACK", None)
        try:
            # Ensure the code takes the fallback branch
            mod.USING_TSL_PACK = False

            # Fake resources.files that returns an object with joinpath
            class FakePath:
                def joinpath(self, *parts):
                    # mimic a path-like return value
                    return "/".join(parts)

            class FakeResources:
                def files(self, pkg):
                    return FakePath()

            # Patch the module's resources to our fake version
            with unittest.mock.patch.object(mod, "resources", FakeResources()):
                result = mod.get_scm_fname("py")
                # Expect the joinpath of ("queries", "tree-sitter-languages", "py-tags.scm")
                self.assertEqual(result, "queries/tree-sitter-languages/py-tags.scm")

            # Now simulate resources.files raising KeyError to hit the except branch
            class FakeResourcesRaise:
                def files(self, pkg):
                    raise KeyError("no resources")

            with unittest.mock.patch.object(mod, "resources", FakeResourcesRaise()):
                result_none = mod.get_scm_fname("py")
                self.assertIsNone(result_none)
        finally:
            # restore original USING_TSL_PACK state
            if orig_using is None:
                try:
                    delattr(mod, "USING_TSL_PACK")
                except Exception:
                    pass
            else:
                mod.USING_TSL_PACK = orig_using
