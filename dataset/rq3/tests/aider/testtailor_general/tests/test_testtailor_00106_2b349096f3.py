import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.scrape')
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
        """Test has_playwright() when playwright is present and when it's absent."""
        import sys
        import types
        import builtins
        # Import the function under test
        from aider.scrape import has_playwright

        # Save originals to restore later
        orig_sync_api = sys.modules.get("playwright.sync_api")
        orig_playwright = sys.modules.get("playwright")
        orig_import = builtins.__import__

        try:
            # Create a fake playwright.sync_api module that provides sync_playwright
            mod = types.ModuleType("playwright.sync_api")

            def sync_playwright():
                class PlaywrightCM:
                    def __enter__(self_inner):
                        class Browser:
                            def launch(self, *a, **k):
                                # Simulate successful chromium launch
                                return object()
                        class P:
                            def __init__(self):
                                self.chromium = Browser()
                        return P()
                    def __exit__(self_inner, exc_type, exc, tb):
                        return False
                return PlaywrightCM()

            mod.sync_playwright = sync_playwright
            # Insert fake package/module entries
            sys.modules["playwright.sync_api"] = mod
            sys.modules["playwright"] = types.ModuleType("playwright")

            # Now has_playwright should return True (both pip import and chromium launch succeed)
            self.assertTrue(has_playwright())

            # Remove the fake modules to avoid accidental reuse
            sys.modules.pop("playwright.sync_api", None)
            sys.modules.pop("playwright", None)

            # Now force ImportError for any attempt to import playwright (simulate not installed)
            def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name.startswith("playwright"):
                    raise ImportError("no module named playwright")
                return orig_import(name, globals, locals, fromlist, level)

            builtins.__import__ = fake_import

            # Now has_playwright should return False
            self.assertFalse(has_playwright())

        finally:
            # Restore originals
            builtins.__import__ = orig_import
            if orig_sync_api is not None:
                sys.modules["playwright.sync_api"] = orig_sync_api
            else:
                sys.modules.pop("playwright.sync_api", None)
            if orig_playwright is not None:
                sys.modules["playwright"] = orig_playwright
            else:
                sys.modules.pop("playwright", None)
