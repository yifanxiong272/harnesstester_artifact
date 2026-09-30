import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.language_handler')
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
        """Ensure filter_bad_extensions uses extra bad extensions when enabled."""
        # Build a minimal settings object with default + extra bad extensions and the flag enabled.
        settings = type("S", (), {})()
        settings.bad_extensions = type("BE", (), {})()
        settings.bad_extensions.default = ["bad"]
        settings.bad_extensions.extra = ["extra"]
        settings.config = type("C", (), {})()
        settings.config.use_extra_bad_extensions = True

        # Create some file-like objects with filename attributes.
        File = type("F", (), {})
        files = []
        f1 = File(); f1.filename = "a.bad"     # should be filtered out (default bad)
        f2 = File(); f2.filename = "b.extra"   # should be filtered out (extra bad)
        f3 = File(); f3.filename = None        # should be filtered out (None)
        f4 = File(); f4.filename = "c.ok"      # should be kept
        files.extend([f1, f2, f3, f4])

        # Monkeypatch the get_settings function in the module that defines filter_bad_extensions.
        mod_name = filter_bad_extensions.__module__
        mod = __import__(mod_name, fromlist=["get_settings"])
        orig_get_settings = getattr(mod, "get_settings", None)
        try:
            setattr(mod, "get_settings", lambda use_context=False: settings)
            result = filter_bad_extensions(files)
        finally:
            # Restore original
            if orig_get_settings is None:
                try:
                    delattr(mod, "get_settings")
                except Exception:
                    pass
            else:
                setattr(mod, "get_settings", orig_get_settings)

        # Only the 'c.ok' file should remain.
        self.assertEqual([f.filename for f in result], ["c.ok"])
