import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.middleware')
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
        """Ensure the branch that parses the origin and allows localhost/127.0.0.1
        (and the fallback 'allow any origin' when no origins are configured) is exercised.
        """
        mock_config = MagicMock()
        mock_config.permitted_cors_origins = []

        with patch('openhands.server.middleware.get_global_config', return_value=mock_config):
            # Create the middleware with a dummy app
            middleware = LocalhostCORSMiddleware(MagicMock())

            # Preconditions: no configured origins
            self.assertEqual(middleware.allow_origins, ())

            # Localhost origin should be allowed regardless of port (hits urlparse -> hostname)
            self.assertTrue(middleware.is_allowed_origin('http://localhost:8000'))
            self.assertTrue(middleware.is_allowed_origin('http://localhost:3000'))

            # 127.0.0.1 should also be allowed
            self.assertTrue(middleware.is_allowed_origin('http://127.0.0.1:8000'))

            # Non-localhost origin when no origins are configured should also be allowed
            # and should trigger a warning log (exercising the branch that logs and returns True)
            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                self.assertTrue(middleware.is_allowed_origin('https://example.org'))
                mock_get_logger.assert_called_once()
                mock_logger.warning.assert_called_once()
