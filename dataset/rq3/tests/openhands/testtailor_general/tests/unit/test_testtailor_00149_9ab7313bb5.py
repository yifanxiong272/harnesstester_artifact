import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.github.service.features')
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
        """Trigger an exception during the PR GraphQL query so the PR error-logging branch is executed."""
        async def main():
            # Local imports (allowed inside the test body)
            import importlib
            import asyncio
            from unittest.mock import patch

            # Use the real mixin class from the codebase
            # Create a dummy instance that implements required async methods/attributes
            class Dummy(GitHubFeaturesMixin):
                def __init__(self):
                    # attribute used in logger extra data
                    self.external_auth_id = 'ext-123'

                async def get_user(self):
                    class U:
                        login = 'test-user'
                    return U()

                # simulate execute_graphql_query raising on first call (PR query),
                # then returning a benign issues response on the second call
                async def execute_graphql_query(self, query, variables):
                    if not hasattr(self, '_call_count'):
                        self._call_count = 1
                        raise Exception('boom-pr-query')
                    # return minimal shape expected for issues processing
                    return {'data': {'user': {'issues': {'nodes': []}}}}

            dummy = Dummy()

            # Patch the module-level logger used by the mixin so we can assert it was called
            mod = importlib.import_module(GitHubFeaturesMixin.__module__)
            with patch.object(mod.logger, 'info') as mock_info:
                # Run the method under test
                result = await dummy.get_suggested_tasks()

                # Assertions: logger.info should have been called for the PR exception
                mock_info.assert_called()
                args, kwargs = mock_info.call_args

                # First arg contains the formatted message
                self.assertIn('Error fetching suggested task for PRs', args[0])
                self.assertIn('boom-pr-query', args[0])

                # extra kwarg should include our signal and user id
                self.assertIn('extra', kwargs)
                self.assertEqual(kwargs['extra']['signal'], 'github_suggested_tasks')
                self.assertEqual(kwargs['extra']['user_id'], 'ext-123')

                # Method should still complete and return tasks (empty list in this setup)
                self.assertEqual(result, [])

        # Run the async test
        import asyncio
        asyncio.run(main())
