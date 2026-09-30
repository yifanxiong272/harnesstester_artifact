import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.services.db_session_injector')
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
        """Ensure _create_gcp_engine calls create_engine with the expected parameters."""
        # Create an injector configured for GCP so it uses _create_gcp_engine
        injector = DbSessionInjector(
            persistence_dir=Path('/tmp'),
            gcp_db_instance='my-instance',
            gcp_project='my-project',
            gcp_region='my-region',
        )

        # Replace create_engine in the function's globals so we intercept the call
        func_globals = injector._create_gcp_engine.__func__.__globals__
        original_create_engine = func_globals.get('create_engine', None)
        mock_create_engine = MagicMock(return_value='mocked_engine')
        func_globals['create_engine'] = mock_create_engine

        try:
            engine = injector._create_gcp_engine()

            # Returned engine should be whatever the mocked create_engine returned
            self.assertEqual(engine, 'mocked_engine')

            # create_engine should have been called once
            mock_create_engine.assert_called_once()
            called_args, called_kwargs = mock_create_engine.call_args

            # First positional argument is the URL string
            self.assertGreaterEqual(len(called_args), 1)
            self.assertEqual(called_args[0], 'postgresql+pg8000://')

            # Verify creator callable, pool sizes, overflow and pre-ping flag
            self.assertIn('creator', called_kwargs)
            called_creator = called_kwargs['creator']
            self.assertTrue(callable(called_creator))

            # Check that the creator is the injector's _create_gcp_db_connection bound method.
            # Compare underlying function and bound self to avoid identity pitfalls of bound-method objects.
            if hasattr(called_creator, '__func__') and hasattr(called_creator, '__self__'):
                self.assertIs(
                    called_creator.__func__,
                    injector._create_gcp_db_connection.__func__,
                )
                self.assertIs(called_creator.__self__, injector)
            else:
                # Fallback: ensure calling the creator returns a connection-like object by mocking connector usage
                # (This branch is defensive; normally the bound-method attributes exist.)
                self.assertTrue(callable(called_creator))

            self.assertEqual(called_kwargs.get('pool_size'), injector.pool_size)
            self.assertEqual(called_kwargs.get('max_overflow'), injector.max_overflow)
            self.assertTrue(called_kwargs.get('pool_pre_ping'))

        finally:
            # Restore original create_engine to avoid side effects
            if original_create_engine is None:
                try:
                    del func_globals['create_engine']
                except KeyError:
                    pass
            else:
                func_globals['create_engine'] = original_create_engine
