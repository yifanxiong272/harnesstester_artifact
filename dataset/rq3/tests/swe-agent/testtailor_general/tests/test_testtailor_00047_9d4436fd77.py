import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.environment.hooks.status')
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
        calls = []

        def recorder(_id: str, message: str):
            calls.append((_id, message))

        hook = SetStatusEnvironmentHook("env-1", recorder)

        class DummyRepo:
            repo_name = "example-repo"

        repo = DummyRepo()
        hook.on_copy_repo_started(repo)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "env-1")
        self.assertEqual(calls[0][1], "Copying repo example-repo")
