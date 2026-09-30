import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.app')
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
        """Ensure frontend and static mounts are created when frontend directory exists."""
        # Local imports to avoid relying on top-level imports in the test harness
        import os
        import sys
        import shutil
        import tempfile
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        tmpdir = tempfile.mkdtemp()
        original_file = None
        mod = None
        try:
            # Create frontend and static directories with test files
            frontend_dir = os.path.join(tmpdir, "frontend")
            static_dir = os.path.join(frontend_dir, "static")
            os.makedirs(static_dir, exist_ok=True)

            index_path = os.path.join(frontend_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("frontend-index")

            static_file_path = os.path.join(static_dir, "test.txt")
            with open(static_file_path, "w", encoding="utf-8") as f:
                f.write("static-file")

            # Create a fake module file three levels under tmpdir so that
            # dirname(dirname(dirname(__file__))) == tmpdir
            fake_mod_dir = os.path.join(tmpdir, "a", "b")
            os.makedirs(fake_mod_dir, exist_ok=True)
            fake_mod_file = os.path.join(fake_mod_dir, "mod.py")
            with open(fake_mod_file, "w", encoding="utf-8") as f:
                f.write("# fake module file for tests")

            # Monkeypatch the module where lifespan is defined to point __file__ to our fake path
            mod = sys.modules.get(lifespan.__module__)
            if mod is None:
                self.fail(f"Module for lifespan not found: {lifespan.__module__}")
            original_file = getattr(mod, "__file__", None)
            mod.__file__ = fake_mod_file

            # Create a fresh FastAPI instance so we don't depend on any existing global app mounts
            local_app = FastAPI(lifespan=lifespan)

            # Use TestClient to trigger the lifespan context (startup)
            with TestClient(local_app) as client:
                # The frontend mount should serve index.html at /site/index.html
                resp_site = client.get("/site/index.html")
                self.assertEqual(resp_site.status_code, 200)
                self.assertIn("frontend-index", resp_site.text)

                # The static mount should serve files under /static/
                resp_static = client.get("/static/test.txt")
                self.assertEqual(resp_static.status_code, 200)
                self.assertIn("static-file", resp_static.text)
        finally:
            # Restore original module __file__ and clean up
            try:
                if mod is not None:
                    if original_file is None:
                        if hasattr(mod, "__file__"):
                            delattr(mod, "__file__")
                    else:
                        mod.__file__ = original_file
            except Exception:
                pass
            shutil.rmtree(tmpdir, ignore_errors=True)
