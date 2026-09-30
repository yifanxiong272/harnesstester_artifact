import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.llm')
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
        """Test that when WEB_HOST indicates staging, the staging llm proxy URL is returned."""
        import os
        from openhands.llm.llm import _get_openhands_llm_base_url

        # Ensure any explicit LITE_LLM_API_URL is not set so fallback logic is exercised
        os.environ.pop('LITE_LLM_API_URL', None)

        try:
            # Case A: WEB_HOST contains '.staging.' should pick the staging proxy
            os.environ['WEB_HOST'] = 'api.staging.example.com'
            url = _get_openhands_llm_base_url()
            self.assertEqual(url, 'https://llm-proxy.staging.all-hands.dev/')

            # Case B: WEB_HOST starts with 'staging' should also pick the staging proxy
            os.environ['WEB_HOST'] = 'staging-cluster'
            url2 = _get_openhands_llm_base_url()
            self.assertEqual(url2, 'https://llm-proxy.staging.all-hands.dev/')
        finally:
            # Clean up environment changes
            os.environ.pop('WEB_HOST', None)
