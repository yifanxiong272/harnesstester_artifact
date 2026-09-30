import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.runner.__init__')
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
        """Ensure CachedRunner.get_cache_key runs and returns a 32-char md5 string."""
        # simple task-like object with required method
        class SimpleTask:
            def __init__(self, name):
                self.name = name

            def get_task_information(self):
                return f"task:{self.name}"

        # simple based-experiment-like object with sub_tasks attribute
        class SimpleBasedExp:
            def __init__(self, sub_tasks):
                self.sub_tasks = sub_tasks

        # construct an Experiment with both based_experiments and sub_tasks
        exp = Experiment(
            sub_tasks=[SimpleTask("s1"), SimpleTask("s2")],
            based_experiments=[SimpleBasedExp([SimpleTask("b1")])],
        )

        # call the target method (pass None as self since the method does not use instance state)
        cache_key = CachedRunner.get_cache_key(None, exp)

        # basic sanity checks: string and md5 hex length
        self.assertIsInstance(cache_key, str)
        self.assertEqual(len(cache_key), 32)

        # calling again with same experiment yields same key
        cache_key2 = CachedRunner.get_cache_key(None, exp)
        self.assertEqual(cache_key, cache_key2)
