import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.gitea_app')
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
        """Ensure that when request.json() raises, get_body logs error and raises HTTPException 400."""
        async def bad_json():
            raise Exception("invalid json")

        request = MagicMock()
        request.json = bad_json
        request.headers = {}

        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            with self.assertRaises(HTTPException) as cm:
                loop.run_until_complete(get_body(request))
        finally:
            asyncio.set_event_loop(None)
            loop.close()

        exc = cm.exception
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.detail, "Error parsing request body")
