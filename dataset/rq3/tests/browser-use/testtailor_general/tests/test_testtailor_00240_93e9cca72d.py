import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.cloud.cloud')
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
        """When the cloud API returns HTTP 403, create_browser should raise CloudBrowserAuthError."""
        # Ensure API key is present so auth fallback logic doesn't interfere
        os.environ['BROWSER_USE_API_KEY'] = 'test-key'
        try:
            client = CloudBrowserClient(api_base_url='https://api.browser-use.com')

            class DummyResponse:
                def __init__(self):
                    self.status_code = 403
                    self.is_success = False

                def json(self):
                    return {"detail": "forbidden"}

            async def fake_post(*args, **kwargs):
                return DummyResponse()

            # Patch the AsyncClient.post method with our fake
            client.client.post = fake_post

            request = CreateBrowserRequest()  # use defaults; model_dump will produce {}

            # Import asyncio at runtime to avoid top-level import in the generated snippet
            asyncio = __import__('asyncio')

            # Create or reuse an event loop robustly
            created_new_loop = False
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                created_new_loop = True

            try:
                with self.assertRaises(CloudBrowserAuthError) as cm:
                    loop.run_until_complete(client.create_browser(request))
            finally:
                if created_new_loop:
                    try:
                        loop.close()
                        asyncio.set_event_loop(None)
                    except Exception:
                        # Best-effort cleanup; tests shouldn't fail due to loop cleanup
                        pass

            self.assertIn('Access forbidden', str(cm.exception))
        finally:
            # Clean up environment modification
            os.environ.pop('BROWSER_USE_API_KEY', None)
