import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.bitbucket_service')
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
        """Ensure get_bitbucket_service_impl lazily loads via get_impl and caches the result."""
        # Import module without using an import statement (to satisfy the constraints)
        bb_mod = __import__('openhands.integrations.bitbucket.bitbucket_service', fromlist=['*'])

        # Ensure the cached implementation is reset to trigger the lazy-loading path
        bb_mod._bitbucket_service_impl = None

        # Create a dummy implementation class that subclasses the expected base
        dummy_impl = type('DummyBitbucketImpl', (bb_mod.BitBucketService,), {})

        # Replace get_impl with a fake that counts calls and records args
        original_get_impl = getattr(bb_mod, 'get_impl', None)
        calls = {'count': 0, 'last_args': None, 'last_kwargs': None}

        def fake_get_impl(*args, **kwargs):
            calls['count'] += 1
            calls['last_args'] = args
            calls['last_kwargs'] = kwargs
            return dummy_impl

        bb_mod.get_impl = fake_get_impl
        try:
            # First call should invoke fake_get_impl and return the dummy implementation
            impl1 = bb_mod.get_bitbucket_service_impl()
            self.assertIs(impl1, dummy_impl)
            self.assertEqual(calls['count'], 1)
            # Validate the expected arguments were passed to get_impl
            self.assertIs(calls['last_args'][0], bb_mod.BitBucketService)
            self.assertEqual(calls['last_args'][1], bb_mod.bitbucket_service_cls)

            # Second call should return cached value and NOT call get_impl again
            impl2 = bb_mod.get_bitbucket_service_impl()
            self.assertIs(impl2, dummy_impl)
            self.assertEqual(calls['count'], 1)  # still one call (cached)
        finally:
            # Restore original get_impl to avoid side effects for other tests
            if original_get_impl is not None:
                bb_mod.get_impl = original_get_impl
            else:
                delattr(bb_mod, 'get_impl')
