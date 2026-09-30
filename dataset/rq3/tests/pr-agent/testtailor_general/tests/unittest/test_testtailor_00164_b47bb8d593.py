import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_action_runner')
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
        """When GITHUB_EVENT_NAME is set but GITHUB_EVENT_PATH is missing, run_action should print an error and return."""
        # Preserve existing env vars to restore later
        prev_event_name = os.environ.get('GITHUB_EVENT_NAME')
        prev_event_path = os.environ.get('GITHUB_EVENT_PATH')
        prev_token = os.environ.get('GITHUB_TOKEN')

        # Preserve original print to restore later
        bb = __builtins__
        if isinstance(bb, dict):
            orig_print = bb.get('print')
        else:
            orig_print = bb.print

        captured = []
        def fake_print(*args, **kwargs):
            # capture printed output as a single string per call
            captured.append(" ".join(str(a) for a in args))

        try:
            # Set up environment: present GITHUB_EVENT_NAME, but remove GITHUB_EVENT_PATH
            os.environ['GITHUB_EVENT_NAME'] = 'pull_request'
            os.environ.pop('GITHUB_EVENT_PATH', None)

            # Replace built-in print with our capturing function
            if isinstance(bb, dict):
                bb['print'] = fake_print
            else:
                bb.print = fake_print

            # Run the async action
            asyncio.run(run_action())

            # Assert that the expected message was printed
            self.assertTrue(any("GITHUB_EVENT_PATH not set" in s for s in captured),
                            f"Expected message not found in captured output: {captured}")
        finally:
            # Restore environment
            if prev_event_name is not None:
                os.environ['GITHUB_EVENT_NAME'] = prev_event_name
            else:
                os.environ.pop('GITHUB_EVENT_NAME', None)
            if prev_event_path is not None:
                os.environ['GITHUB_EVENT_PATH'] = prev_event_path
            else:
                os.environ.pop('GITHUB_EVENT_PATH', None)
            if prev_token is not None:
                os.environ['GITHUB_TOKEN'] = prev_token
            else:
                os.environ.pop('GITHUB_TOKEN', None)

            # Restore original print
            if isinstance(bb, dict):
                if orig_print is not None:
                    bb['print'] = orig_print
                else:
                    bb.pop('print', None)
            else:
                bb.print = orig_print
