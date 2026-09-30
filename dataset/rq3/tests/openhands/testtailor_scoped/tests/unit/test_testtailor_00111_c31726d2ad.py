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
        """Ensure that when fetching PRs raises an exception, we log the PR error."""
        # Minimal subclass providing get_user
        class DummyGitHub(GitHubFeaturesMixin):
            async def get_user(self):
                return __import__('types').SimpleNamespace(login='alice')

        inst = DummyGitHub()
        inst.external_auth_id = 'user-123'

        # Prepare AsyncMock for execute_graphql_query
        mock_module = getattr(__import__('unittest'), 'mock')
        AsyncMock = mock_module.AsyncMock
        Mock = mock_module.Mock

        # First call (PR query) raises, second call (issues query) returns empty issues
        inst.execute_graphql_query = AsyncMock(
            side_effect=[
                Exception('boom'),
                {'data': {'user': {'issues': {'nodes': []}}}},
            ]
        )

        # Replace the module-level logger with a mock to capture logger.info calls
        mod = __import__(GitHubFeaturesMixin.__module__, fromlist=['*'])
        original_logger = getattr(mod, 'logger', None)
        mock_logger = Mock()
        setattr(mod, 'logger', mock_logger)

        try:
            # Run the async method using imported asyncio via __import__
            aio = __import__('asyncio')
            loop = aio.new_event_loop()
            try:
                aio.set_event_loop(loop)
                loop.run_until_complete(inst.get_suggested_tasks())
            finally:
                loop.close()

            # Verify logger.info was called with the expected message and extra payload
            mock_logger.info.assert_called_once_with(
                'Error fetching suggested task for PRs: boom',
                extra={'signal': 'github_suggested_tasks', 'user_id': 'user-123'},
            )
        finally:
            # Restore original logger to avoid side effects
            if original_logger is not None:
                setattr(mod, 'logger', original_logger)
