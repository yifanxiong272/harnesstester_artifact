import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_app')
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
        """When request.json() raises, get_body should log and raise HTTPException(400)."""
        class BadRequest:
            def __init__(self):
                self.headers = {}
            async def json(self):
                raise ValueError("invalid json payload")
            async def body(self):
                return b''

        req = BadRequest()

        with self.assertRaises(HTTPException) as cm:
            asyncio.run(get_body(req))

        exc = cm.exception
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(str(exc.detail), "Error parsing request body")
        # original exception should be chained
        self.assertIsInstance(exc.__cause__, ValueError)
        self.assertEqual(str(exc.__cause__), "invalid json payload")
