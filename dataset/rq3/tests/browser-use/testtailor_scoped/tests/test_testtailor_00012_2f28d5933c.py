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
	def test_cloud_profile_id_sets_cloud_browser_params_and_use_cloud(self):
		"""Providing cloud_profile_id should populate cloud_browser_params and set use_cloud=True.

		Do not assume the exact attribute names on the CreateBrowserRequest Pydantic model;
	inspect via model_dump() or fallback to string representation.
	"""
		uuid_str = '11111111-1111-4111-8111-111111111111'

		# Import inside the test to avoid top-level imports
		from browser_use.browser import BrowserSession

		# Construct session with cloud_profile_id - this should trigger CreateBrowserRequest creation
		session = BrowserSession(cloud_profile_id=uuid_str)

		# BrowserProfile should indicate cloud usage
		self.assertTrue(session.browser_profile.use_cloud, 'use_cloud should be True when cloud_profile_id is provided')

		# cloud_browser_params should have been created
		cloud_params = session.browser_profile.cloud_browser_params
		self.assertIsNotNone(cloud_params, 'cloud_browser_params should be created when cloud_profile_id is provided')

		# Try to inspect the underlying data in a robust way
		found = False
		# Preferred: pydantic v2 exposes model_dump()
		if hasattr(cloud_params, 'model_dump'):
			try:
				data = cloud_params.model_dump(exclude_unset=True)
			except TypeError:
				# Older signature fallback
				data = cloud_params.model_dump()
			# Check values for the UUID string
			for v in (data.values() if isinstance(data, dict) else []):
				if uuid_str in str(v):
					found = True
					break

		# Fallback: string representation
		if not found:
			if uuid_str in str(cloud_params):
				found = True

		self.assertTrue(found, 'cloud_browser_params should contain the provided cloud_profile_id (checked via model_dump() or str)')
