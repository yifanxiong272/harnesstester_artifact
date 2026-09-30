import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.custom.custom')
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
        """Verify CustomRetriever reads RETRIEVER_ENDPOINT env var and raises when missing."""
        # Save original environment and restore at the end
        original_env = os.environ.copy()
        try:
            # Ensure RETRIEVER_ENDPOINT is not set -> constructor should raise ValueError
            os.environ.pop('RETRIEVER_ENDPOINT', None)
            os.environ.pop('RETRIEVER_ARG_SAMPLE', None)
            with self.assertRaises(ValueError):
                CustomRetriever(query="irrelevant")

            # Now set RETRIEVER_ENDPOINT and a RETRIEVER_ARG_... var and construct successfully
            os.environ['RETRIEVER_ENDPOINT'] = 'http://retriever.test/endpoint'
            os.environ['RETRIEVER_ARG_SAMPLE'] = 'param_value'

            retriever = CustomRetriever(query="my query")
            # endpoint should be read from environment and assigned
            self.assertEqual(retriever.endpoint, 'http://retriever.test/endpoint')
            # query should be assigned from constructor arg
            self.assertEqual(retriever.query, 'my query')
            # params should include the populated RETRIEVER_ARG_ value (key lowercased and prefix removed)
            self.assertIn('sample', retriever.params)
            self.assertEqual(retriever.params['sample'], 'param_value')
        finally:
            # Restore original environment to avoid side effects on other tests
            os.environ.clear()
            os.environ.update(original_env)
