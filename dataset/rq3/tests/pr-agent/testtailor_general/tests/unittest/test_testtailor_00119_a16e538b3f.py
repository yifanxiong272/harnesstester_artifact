import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.server')
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
        """Verify start() calls setup_logger with JSON format, logs the startup message,
        and invokes uvicorn.run() with the build_app() result and environment HOST/PORT.
        This avoids patching a non-existent attribute on the server module by injecting a
        fake 'uvicorn' module into sys.modules before importing/calling start().
        """
        import importlib
        import os
        import sys
        import types
        from unittest.mock import patch, MagicMock
        from pr_agent.log import LoggingFormat

        # Prepare a fake uvicorn module with a MagicMock 'run' function.
        dummy_uvicorn = types.ModuleType("uvicorn")
        dummy_uvicorn.run = MagicMock()

        prev_uvicorn = sys.modules.get("uvicorn")
        sys.modules["uvicorn"] = dummy_uvicorn
        try:
            # Patch the functions in the server module that start() will call.
            with patch("pr_agent.mosaico.server.setup_logger") as mock_setup_logger, \
                 patch("pr_agent.mosaico.server.build_app") as mock_build_app, \
                 patch("pr_agent.mosaico.server.get_logger") as mock_get_logger:

                # Configure build_app() to return a sentinel app object and get_logger() to return a fake logger.
                dummy_app = object()
                mock_build_app.return_value = dummy_app
                fake_logger = MagicMock()
                mock_get_logger.return_value = fake_logger

                # Set environment values for HOST and PORT and import/call start().
                with patch.dict(os.environ, {"HOST": "1.2.3.4", "PORT": "4321"}):
                    server = importlib.import_module("pr_agent.mosaico.server")
                    # Call the start function under test.
                    server.start()

                # Assertions: setup_logger called with JSON format
                mock_setup_logger.assert_called_once()
                called_kwargs = mock_setup_logger.call_args.kwargs
                self.assertIn("fmt", called_kwargs)
                self.assertEqual(called_kwargs["fmt"], LoggingFormat.JSON)

                # uvicorn.run called with the app returned by build_app and the expected host/port
                dummy_uvicorn.run.assert_called_once_with(dummy_app, host="1.2.3.4", port=4321)

                # The logger.info startup message was emitted and contains host:port
                fake_logger.info.assert_called_once()
                msg = fake_logger.info.call_args[0][0]
                self.assertIn("Starting PR-Agent MOSAICO solution agent", msg)
                self.assertIn("1.2.3.4:4321", msg)
        finally:
            # Restore previous uvicorn module if any.
            if prev_uvicorn is not None:
                sys.modules["uvicorn"] = prev_uvicorn
            else:
                del sys.modules["uvicorn"]
