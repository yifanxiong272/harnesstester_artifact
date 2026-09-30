import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.session')
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
	def test_cloud_timeout_propagated(self):
		"""Ensure that providing cloud_timeout creates cloud_browser_params and the timeout value is present."""
		from browser_use.browser import BrowserSession

		session = BrowserSession(cloud_timeout=123)

		# cloud_browser_params should be created
		self.assertIsNotNone(session.browser_profile.cloud_browser_params)
		# use_cloud flag should be set when cloud params are provided
		self.assertTrue(session.browser_profile.use_cloud)

		# Safely serialize the cloud_browser_params to inspect contained values without assuming field names
		cloud_params = session.browser_profile.cloud_browser_params
		if hasattr(cloud_params, 'model_dump'):
			dumped = cloud_params.model_dump()
		elif hasattr(cloud_params, 'dict'):
			dumped = cloud_params.dict()
		else:
			dumped = getattr(cloud_params, '__dict__', dumped)

		# The exact field name on CreateBrowserRequest may vary; assert the provided timeout value is present somewhere in the serialized representation
		self.assertIn('123', repr(dumped), msg=f'Expected timeout value 123 in cloud params dump, got: {dumped}')

	@timeout_decorator.timeout(1)
	def test_legacy_timeout_alias_propagated(self):
		"""Ensure legacy timeout parameter (timeout) is treated like cloud_timeout and propagated."""
		from browser_use.browser import BrowserSession

		session = BrowserSession(timeout=77)

		self.assertIsNotNone(session.browser_profile.cloud_browser_params)
		self.assertTrue(session.browser_profile.use_cloud)

		cloud_params = session.browser_profile.cloud_browser_params
		if hasattr(cloud_params, 'model_dump'):
			dumped = cloud_params.model_dump()
		elif hasattr(cloud_params, 'dict'):
			dumped = cloud_params.dict()
		else:
			dumped = getattr(cloud_params, '__dict__', dumped)

		self.assertIn('77', repr(dumped), msg=f'Expected timeout value 77 in cloud params dump, got: {dumped}')
