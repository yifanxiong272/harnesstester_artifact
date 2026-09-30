import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.sessions')
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
        """Ensure use_cloud branch passes cloud kwargs into CLIBrowserSession."""
        captured_instances = []

        class DummyCLISession:
            def __init__(self, **kwargs):
                # record kwargs for assertions and keep instance accessible
                self.kwargs = kwargs
                captured_instances.append(self)

        g = create_browser_session.__globals__
        old_cls = g.get('CLIBrowserSession', None)
        try:
            # Inject DummyCLISession into the function's globals so create_browser_session
            # will instantiate it instead of the real CLIBrowserSession.
            g['CLIBrowserSession'] = DummyCLISession

            # Obtain asyncio without top-level import (allowed inside function)
            asyncio = __import__('asyncio')

            # Run the async function to completion, handling possible closed loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    session = asyncio.run(
                        create_browser_session(
                            headed=True,
                            profile=None,
                            use_cloud=True,
                            cloud_profile_id='my-profile-id',
                            cloud_proxy_country_code='US',
                            cloud_timeout=123,
                        )
                    )
                else:
                    session = loop.run_until_complete(
                        create_browser_session(
                            headed=True,
                            profile=None,
                            use_cloud=True,
                            cloud_profile_id='my-profile-id',
                            cloud_proxy_country_code='US',
                            cloud_timeout=123,
                        )
                    )
            except RuntimeError:
                # Fallback if there's no running loop
                session = asyncio.run(
                    create_browser_session(
                        headed=True,
                        profile=None,
                        use_cloud=True,
                        cloud_profile_id='my-profile-id',
                        cloud_proxy_country_code='US',
                        cloud_timeout=123,
                    )
                )
        finally:
            # Restore original CLIBrowserSession to avoid side effects on other tests
            if old_cls is None:
                del g['CLIBrowserSession']
            else:
                g['CLIBrowserSession'] = old_cls

        # Validate returned object and that kwargs were forwarded correctly
        self.assertIs(session, captured_instances[0])
        self.assertTrue(session.kwargs.get('use_cloud'))
        self.assertEqual(session.kwargs.get('cloud_profile_id'), 'my-profile-id')
        self.assertEqual(session.kwargs.get('cloud_proxy_country_code'), 'US')
        self.assertEqual(session.kwargs.get('cloud_timeout'), 123)
