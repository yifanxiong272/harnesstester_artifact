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
        """Ensure the branch where USING_TSL_PACK is True but resources.files raises KeyError is exercised."""
        # Locate the module that defines get_scm_fname
        mod = __import__(get_scm_fname.__module__, fromlist=["*"])

        # Preserve original flag and restore later
        orig_using = getattr(mod, "USING_TSL_PACK", None)
        try:
            setattr(mod, "USING_TSL_PACK", True)

            call = {"n": 0}

            def fake_files(pkg):
                # First call simulates missing tsl-pack by raising KeyError
                call["n"] += 1
                if call["n"] == 1:
                    raise KeyError("simulate missing tsl-pack")
                # Second call returns an object with joinpath(...) as expected by fallback
                class Dummy:
                    def joinpath(self, *args):
                        return "fallback_joinpath"
                return Dummy()

            # Patch resources.files so the first call raises KeyError and the second returns Dummy
            with unittest.mock.patch.object(mod.resources, "files", side_effect=fake_files):
                result = get_scm_fname("python")

            # The fallback path should have been taken and returned our Dummy.joinpath value
            self.assertEqual(result, "fallback_joinpath")
        finally:
            # Restore original USING_TSL_PACK
            if orig_using is None:
                try:
                    delattr(mod, "USING_TSL_PACK")
                except Exception:
                    pass
            else:
                setattr(mod, "USING_TSL_PACK", orig_using)
