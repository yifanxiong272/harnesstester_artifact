import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.sync.auth')
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
		"""Ensure get_or_create_device_id uses CONFIG.BROWSER_USE_CONFIG_DIR and persists/reads device id."""
		# Import needed stdlib modules dynamically to avoid relying on top-level imports
		tempfile = __import__('tempfile')
		pathlib = __import__('pathlib')
		Path = pathlib.Path
		mock = __import__('unittest.mock', fromlist=['patch'])

		# Preserve whether CONFIG originally had the attribute and its value
		orig_has = hasattr(CONFIG, 'BROWSER_USE_CONFIG_DIR')
		orig_value = getattr(CONFIG, 'BROWSER_USE_CONFIG_DIR', None)

		with tempfile.TemporaryDirectory() as tmpdir:
			temp_dir = Path(tmpdir) / '.config' / 'browseruse'
			temp_dir.mkdir(parents=True, exist_ok=True)

			try:
				# Point CONFIG to our temporary directory
				CONFIG.BROWSER_USE_CONFIG_DIR = temp_dir

				device_file = CONFIG.BROWSER_USE_CONFIG_DIR / 'device_id'
				# Ensure no device id exists initially
				if device_file.exists():
					device_file.unlink()

				# First call should create a new device id and write it to file
				id1 = get_or_create_device_id()
				self.assertIsInstance(id1, str)
				self.assertTrue(len(id1) > 0)
				self.assertTrue(device_file.exists())
				self.assertEqual(device_file.read_text().strip(), id1)

				# Second call should read the same device id
				id2 = get_or_create_device_id()
				self.assertEqual(id1, id2)

				# Simulate a read error so function creates a new id
				with mock.patch.object(pathlib.Path, 'read_text', side_effect=Exception("read error")):
					id3 = get_or_create_device_id()
					# Should return a new id (different from previous)
					self.assertIsInstance(id3, str)
					self.assertNotEqual(id3, id1)

				# After patch removed, file should contain the newly created id
				self.assertEqual(device_file.read_text().strip(), id3)
			finally:
				# Restore original CONFIG value or remove attribute if it didn't exist
				if orig_has:
					CONFIG.BROWSER_USE_CONFIG_DIR = orig_value
				else:
					try:
						delattr(CONFIG, 'BROWSER_USE_CONFIG_DIR')
					except Exception:
						# If deletion fails, ignore to avoid masking test results
						pass
