import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.server')
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
		"""Ensure that if a parent() call raises psutil.AccessDenied (or NoSuchProcess)
		when climbing the chain, the loop breaks cleanly after collecting the cmdline
		from the first accessible parent.
		"""
		# Access the module globals where get_parent_process_cmdline is defined
		mod_globals = get_parent_process_cmdline.__globals__

		# Preserve originals to restore after the test
		orig_psutil_Process = mod_globals['psutil'].Process
		orig_psutil_available = mod_globals.get('PSUTIL_AVAILABLE', False)

		try:
			# Ensure the function believes psutil is available
			mod_globals['PSUTIL_AVAILABLE'] = True

			# Create fake parent that provides a cmdline, but whose parent() raises AccessDenied
			class FakeParent:
				def cmdline(self):
					return ['parentcmd']

				def parent(self):
					# Raise the real psutil.AccessDenied coming from the module's psutil
					raise mod_globals['psutil'].AccessDenied()

			# Create fake current process whose parent() returns the FakeParent
			class FakeProcess:
				def parent(self):
					return FakeParent()

			# Patch psutil.Process used by the target function to return our fake process
			mod_globals['psutil'].Process = lambda: FakeProcess()

			# Call the function under test; it should collect the parent's cmdline and stop when parent().parent() raises
			result = get_parent_process_cmdline()

			# We expect the single collected cmdline joined into a string
			self.assertEqual(result, 'parentcmd')
		finally:
			# Restore originals
			mod_globals['psutil'].Process = orig_psutil_Process
			mod_globals['PSUTIL_AVAILABLE'] = orig_psutil_available
