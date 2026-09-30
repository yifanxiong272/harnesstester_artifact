import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser._cdp_timeout')
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
        """Ensure __init__ forwards args/kwargs to the parent __init__ and
        coerces the cdp_request_timeout_s into _cdp_request_timeout_s.
        """
        # Patch the parent's __init__ so we don't attempt any real setup.
        with patch('browser_use.browser._cdp_timeout.CDPClient.__init__', return_value=None) as mock_super_init:
            client = TimeoutWrappedCDPClient('positional_arg', foo='bar', cdp_request_timeout_s=0.123)

            # Parent __init__ was invoked exactly once.
            self.assertEqual(mock_super_init.call_count, 1)

            called_args, called_kwargs = mock_super_init.call_args
            # Depending on how the patched function was invoked the instance may or may not
            # appear as the first positional arg (patching a function replaces the descriptor).
            # Accept both possibilities: either (self, 'positional_arg') or ('positional_arg',).
            if called_args and called_args[0] is client:
                # Instance bound present; next positional arg should be our forwarded one.
                self.assertEqual(called_args[1], 'positional_arg')
            else:
                # No bound instance in the recorded args; first arg should be the forwarded one.
                self.assertEqual(called_args[0], 'positional_arg')

            # cdp_request_timeout_s must not be forwarded to the parent; other kwargs preserved.
            self.assertEqual(called_kwargs, {'foo': 'bar'})

            # The timeout argument is coerced and stored on the instance.
            self.assertAlmostEqual(client._cdp_request_timeout_s, 0.123)

        # Invalid values (e.g. nan) must fall back to the DEFAULT_CDP_REQUEST_TIMEOUT_S.
        with patch('browser_use.browser._cdp_timeout.CDPClient.__init__', return_value=None):
            client2 = TimeoutWrappedCDPClient(cdp_request_timeout_s=float('nan'))
            self.assertEqual(client2._cdp_request_timeout_s, DEFAULT_CDP_REQUEST_TIMEOUT_S)
