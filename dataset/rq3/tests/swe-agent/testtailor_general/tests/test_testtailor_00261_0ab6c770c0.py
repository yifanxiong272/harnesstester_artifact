import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.server')
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
        """Ensure run_from_cli sets app.debug and calls socketio.run with expected kwargs"""
        # start with debug off to observe change
        app.debug = False

        with unittest.mock.patch.object(socketio, "run") as mock_run:
            # Call the function under test; it should set app.debug = True and call socketio.run
            run_from_cli()

            # app.debug must have been set to True
            self.assertTrue(app.debug)

            # socketio.run should have been called exactly once
            mock_run.assert_called_once()

            # Check that the call used the expected arguments and keyword arguments
            called_args, called_kwargs = mock_run.call_args
            # First positional arg should be the Flask app
            self.assertGreaterEqual(len(called_args), 1)
            self.assertIs(called_args[0], app)
            # Keyword args must include the expected server options
            self.assertEqual(called_kwargs.get("port"), 8000)
            self.assertTrue(called_kwargs.get("debug"))
            self.assertTrue(called_kwargs.get("allow_unsafe_werkzeug"))
