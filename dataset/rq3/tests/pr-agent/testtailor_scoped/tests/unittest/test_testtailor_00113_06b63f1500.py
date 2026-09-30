import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.gerrit_provider')
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
        """complete the test case here"""
        url = "https://example.com/repo.git"
        refspec = "refs/heads/main"
        cwd = "/tmp/repo"

        # prepare a fake logger that records info calls
        fake_logger = unittest.mock.Mock()

        # determine the module where fetch is defined and patch its dependencies
        module = fetch.__module__
        with unittest.mock.patch(f"{module}.get_logger", return_value=fake_logger) as get_logger_patch, \
             unittest.mock.patch(f"{module}._call", return_value="fetched\n") as call_patch:
            # call the function under test
            fetch(url, refspec, cwd)

        # get_logger should have been called (twice: before and after the _call)
        self.assertGreaterEqual(get_logger_patch.call_count, 1)

        # _call should be invoked with the exact git fetch invocation and cwd kwarg
        call_patch.assert_called_once_with(
            'git', 'fetch', '--depth', '2', url, refspec, cwd=cwd
        )

        # logger.info should have been called first with the fetching message and later with stdout
        fake_logger.info.assert_any_call("Fetching %s %s", url, refspec)
        fake_logger.info.assert_any_call("fetched\n")
