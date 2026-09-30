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
        """Verify that RETRIEVER_ENDPOINT is read from the environment and that absence raises."""
        # Save and clear any existing environment values we'll touch
        saved_endpoint = os.environ.pop('RETRIEVER_ENDPOINT', None)
        saved_arg = os.environ.pop('RETRIEVER_ARG_TEST', None)

        try:
            # When RETRIEVER_ENDPOINT is not set, constructor should raise ValueError
            with self.assertRaises(ValueError):
                CustomRetriever(query="should_fail")

            # Now set the environment variables and instantiate successfully
            os.environ['RETRIEVER_ENDPOINT'] = 'http://example.com'
            os.environ['RETRIEVER_ARG_TEST'] = 'value1'

            retriever = CustomRetriever(query="my query")

            # The endpoint should be read from the environment and stored on the instance
            self.assertEqual(retriever.endpoint, 'http://example.com')
            self.assertEqual(retriever.query, 'my query')

            # Parameters should include any environment vars prefixed with RETRIEVER_ARG_
            self.assertIn('test', retriever.params)
            self.assertEqual(retriever.params['test'], 'value1')
        finally:
            # Restore original environment state
            if saved_endpoint is None:
                os.environ.pop('RETRIEVER_ENDPOINT', None)
            else:
                os.environ['RETRIEVER_ENDPOINT'] = saved_endpoint

            if saved_arg is None:
                os.environ.pop('RETRIEVER_ARG_TEST', None)
            else:
                os.environ['RETRIEVER_ARG_TEST'] = saved_arg
