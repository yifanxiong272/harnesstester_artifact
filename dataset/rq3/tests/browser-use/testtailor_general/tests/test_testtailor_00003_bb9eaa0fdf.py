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
	def test_create_session_with_cloud_profile_id_builds_cloud_kwargs(self):
		"""Providing cloud_profile_id should create cloud_browser_params and enable use_cloud.

		The CreateBrowserRequest model may expose the provided id under different attribute
		names depending on its implementation. We therefore inspect the model dump / __dict__
		and look for the UUID string in any value to ensure the cloud_profile_id was passed
	 through into cloud_browser_params.
		"""
		# Use a stable UUID string accepted by the API/validators
		uuid_str = '123e4567-e89b-12d3-a456-426614174000'

		# Construct the BrowserSession with only cloud_profile_id to trigger cloud_kwargs branch
		from browser_use.browser import BrowserSession

		session = BrowserSession(cloud_profile_id=uuid_str)

		# The profile should be marked to use cloud
		self.assertTrue(session.browser_profile.use_cloud, 'BrowserProfile.use_cloud should be True when cloud_profile_id is provided')

		# cloud_browser_params should be populated
		cloud_params = session.browser_profile.cloud_browser_params
		self.assertIsNotNone(cloud_params, 'cloud_browser_params should be set when cloud_profile_id is provided')

		# Inspect the cloud_params for any field containing the provided UUID string
		dump = None
		if hasattr(cloud_params, 'model_dump'):
			try:
				dump = cloud_params.model_dump()
			except Exception:
				# some pydantic versions might not support model_dump at init time
				dump = getattr(cloud_params, '__dict__', None)
		else:
			dump = getattr(cloud_params, '__dict__', None)

		# Fallback to stringifying the object if we couldn't get a mapping
		found = False
		if isinstance(dump, dict):
			for v in dump.values():
				if v is None:
					continue
				# Handle UUID objects or nested structures
				try:
					if getattr(v, 'hex', None) or getattr(v, 'int', None):
						# likely a UUID-like object
						if str(v) == uuid_str:
							found = True
							break
				except Exception:
					pass
				# Strings or numbers
				if str(v) == uuid_str:
					found = True
					break
				# If it's a list/dict, search recursively (simple)
				if isinstance(v, (list, tuple, set)):
					for item in v:
						if item and str(item) == uuid_str:
							found = True
							break
					if found:
						break
				if isinstance(v, dict):
					for item in v.values():
						if item and str(item) == uuid_str:
							found = True
							break
					if found:
						break
		else:
			# Last resort: check string representation
			if uuid_str in str(cloud_params):
				found = True

		self.assertTrue(found, "Expected cloud_profile_id to be present in cloud_browser_params (found in model dump or __dict__)")
