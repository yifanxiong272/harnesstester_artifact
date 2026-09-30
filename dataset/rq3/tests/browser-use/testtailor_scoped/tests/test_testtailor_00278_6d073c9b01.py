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
	def test_case_XX(self):
		"""Ensure cloud_browser backward-compatibility alias maps to use_cloud in BrowserProfile"""
		# cloud_browser=True should set use_cloud=True on the resolved BrowserProfile
		session_true = BrowserSession(cloud_browser=True)
		self.assertTrue(
			session_true.browser_profile.use_cloud,
			"Expected browser_profile.use_cloud to be True when initialized with cloud_browser=True",
		)

		# cloud_browser=False should set use_cloud=False on the resolved BrowserProfile
		session_false = BrowserSession(cloud_browser=False)
		self.assertFalse(
			session_false.browser_profile.use_cloud,
			"Expected browser_profile.use_cloud to be False when initialized with cloud_browser=False",
		)
