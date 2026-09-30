import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.stuck')
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
        """Detect repeating IPythonRunCellObservation unterminated string syntax error loop."""
        # Prepare state and stuck detector
        state = State(inputs={})
        state.iteration_flag.max_value = 50
        state.history = []

        # Prepare three identical IPython actions and matching observations that include
        # the specific unterminated string literal syntax error and the required Jupyter lines
        ipython_code = 'print("hello'  # code causing unterminated string literal
        ipython_obs_content = (
            'print("hello\n'
            '       ^\n'
            'SyntaxError: unterminated string literal (detected at line 1)\n'
            '[Jupyter current working directory:/tmp]\n'
            '[Jupyter Python interpreter:3.8]'
        )

        for _ in range(3):
            state.history.append(IPythonRunCellAction(code=ipython_code))
            state.history.append(
                IPythonRunCellObservation(content=ipython_obs_content, code=ipython_code)
            )

        sd = StuckDetector(state)

        # Patch the logger to assert the correct warning is emitted and verify stuck detection
        with patch('logging.Logger.warning') as mock_warning:
            self.assertTrue(sd.is_stuck(headless_mode=True))
            mock_warning.assert_called_once_with('Action, IPythonRunCellObservation loop detected')

        # Verify stuck_analysis was set appropriately
        self.assertIsNotNone(sd.stuck_analysis)
        self.assertEqual(sd.stuck_analysis.loop_type, 'repeating_action_error')
        self.assertEqual(sd.stuck_analysis.loop_repeat_times, 3)
