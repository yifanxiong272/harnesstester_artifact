import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.open_pr')
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
        """Calling open_pr with an invalid github_url logs opening and raises ValueError."""
        logger = Mock()
        token = ""
        env = None  # env is not used because _get_gh_issue_data will raise early
        github_url = "not-a-valid-github-url"
        trajectory = []

        with self.assertRaises(ValueError) as cm:
            open_pr(logger=logger, token=token, env=env, github_url=github_url, trajectory=trajectory, _dry_run=True)

        # Verify the raised error message is the expected one from the handler
        self.assertIn("Data path must be a github issue URL if open_pr is set to True.", str(cm.exception))

        # logger.info should have been called before the error was raised
        logger.info.assert_called_with("Opening PR")
