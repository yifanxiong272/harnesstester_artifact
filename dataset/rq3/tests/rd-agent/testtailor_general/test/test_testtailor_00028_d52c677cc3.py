import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.server.app')
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
        """Ensure favicon() calls send_from_directory with app.static_folder and correct mimetype."""
        # Ensure favicon is available
        try:
            func = favicon
        except NameError:
            self.fail("favicon is not available in the test environment")

        g = func.__globals__

        # ensure expected globals exist
        if "app" not in g:
            self.fail("module where favicon is defined has no 'app'")

        # prepare to replace send_from_directory in the function's globals
        original_send = g.get("send_from_directory", None)
        original_static = getattr(g["app"], "static_folder", None)

        try:
            # create a temporary directory and a dummy favicon file using __import__ to avoid top-level imports
            tempfile_mod = __import__("tempfile")
            os_mod = __import__("os")
            with tempfile_mod.TemporaryDirectory() as tmpdir:
                favicon_file = os_mod.path.join(tmpdir, "favicon.ico")
                with open(favicon_file, "wb") as f:
                    f.write(b"ICO")

                # point app.static_folder to our temp dir
                g["app"].static_folder = tmpdir

                # sentinel to capture call
                called = {"args": None, "kwargs": None}

                def sentinel(*args, **kwargs):
                    called["args"] = args
                    called["kwargs"] = kwargs
                    return "SENTINEL"

                # inject sentinel
                g["send_from_directory"] = sentinel

                # call the function under test
                result = func()

                # assertions
                self.assertEqual(result, "SENTINEL")
                self.assertIsNotNone(called["args"], "send_from_directory was not called")
                self.assertGreaterEqual(len(called["args"]), 2)
                self.assertEqual(called["args"][0], tmpdir)
                self.assertEqual(called["args"][1], "favicon.ico")
                self.assertIn("mimetype", called["kwargs"])
                self.assertEqual(called["kwargs"]["mimetype"], "image/vnd.microsoft.icon")
        finally:
            # restore originals
            if original_send is not None:
                g["send_from_directory"] = original_send
            else:
                g.pop("send_from_directory", None)
            if original_static is not None:
                g["app"].static_folder = original_static
            else:
                # if there was no original, try to delete attribute if present
                try:
                    delattr(g["app"], "static_folder")
                except Exception:
                    # ignore if deletion not possible
                    pass
