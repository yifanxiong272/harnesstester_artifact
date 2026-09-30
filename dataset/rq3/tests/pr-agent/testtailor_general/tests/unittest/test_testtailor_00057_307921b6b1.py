import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.log.__init__')
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
        import pr_agent
        import pkgutil
        import importlib

        # Try to locate the json_format function anywhere in the pr_agent package
        json_fn = None

        # Check direct attributes on package
        for name in dir(pr_agent):
            try:
                obj = getattr(pr_agent, name)
            except Exception:
                continue
            if callable(obj) and getattr(obj, "__name__", "") == "json_format":
                json_fn = obj
                break

        # If not found, walk submodules
        if json_fn is None:
            for finder, modname, ispkg in pkgutil.walk_packages(pr_agent.__path__, pr_agent.__name__ + "."):
                try:
                    mod = importlib.import_module(modname)
                except Exception:
                    continue
                for name in dir(mod):
                    try:
                        obj = getattr(mod, name)
                    except Exception:
                        continue
                    if callable(obj) and getattr(obj, "__name__", "") == "json_format":
                        json_fn = obj
                        break
                if json_fn:
                    break

        self.assertIsNotNone(json_fn, "Could not find json_format in pr_agent package")

        # Normal case: message present
        record = {"message": "hello world", "level": "INFO"}
        result = json_fn(record)
        self.assertEqual(result, "hello world")

        # Error case: missing message -> KeyError raised from record["message"]
        with self.assertRaises(KeyError):
            json_fn({"no_message": True})
