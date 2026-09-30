import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.gif')
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
        """Ensure history.screenshots(...) is consumed by create_history_gif and a GIF is produced."""
        # Minimal valid 1x1 PNG (base64) - not equal to any placeholder
        png_b64 = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='
        )

        # Create minimal dummy objects expected by create_history_gif
        class DummyState:
            def __init__(self, b64, url='https://example.com'):
                self._b64 = b64
                self.url = url
                self.screenshot_path = None
                self.interacted_element = None

            def get_screenshot(self):
                return self._b64

        class DummyCurrentState:
            def __init__(self, next_goal='Next goal'):
                self.next_goal = next_goal

        class DummyModelOutput:
            def __init__(self, next_goal='Next goal'):
                self.current_state = DummyCurrentState(next_goal)

        class DummyHistoryItem:
            def __init__(self, state, model_output=None):
                self.state = state
                self.model_output = model_output
                self.result = []
                self.metadata = None

        class DummyHistoryList:
            def __init__(self, items):
                self.history = items

            # Match the signature used by create_history_gif
            def screenshots(self, n_last=None, return_none_if_not_screenshot=True):
                items = self.history if n_last is None else self.history[-n_last:]
                out = []
                for it in items:
                    s = it.state.get_screenshot()
                    if s:
                        out.append(s)
                    else:
                        if return_none_if_not_screenshot:
                            out.append(None)
                return out

        # Build history with a single item that has a real screenshot
        state = DummyState(png_b64, url='https://example.com')
        item = DummyHistoryItem(state, model_output=DummyModelOutput(next_goal='Reach the target'))
        history = DummyHistoryList([item])

        # Call the function under test; choose a short duration to keep the file small
        output_path = 'test_agent_history.gif'
        # Ensure any previous file is removed
        os_mod = __import__('os')
        try:
            if os_mod.path.exists(output_path):
                os_mod.remove(output_path)
        except Exception:
            pass

        # Should not raise
        create_history_gif(
            task='Test task',
            history=history,
            output_path=output_path,
            duration=50,
            show_goals=True,
            show_task=True,
            show_logo=False,
        )

        # Verify the GIF file was created
        self.assertTrue(os_mod.path.exists(output_path), msg="Expected GIF output file to be created")

        # Clean up
        try:
            os_mod.remove(output_path)
        except Exception:
            pass
