import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.main')
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
        """Test that check_config_files_for_yes detects lines starting with 'yes:' and returns correct boolean."""
        base = os.path.join(os.getcwd(), "tmp_test_dir_" + str(id(self)))
        # Ensure a clean directory (avoid using shutil/tempfile to prevent missing imports)
        if os.path.exists(base):
            # remove any files/subdirs inside
            for name in os.listdir(base):
                path = os.path.join(base, name)
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    # remove nested directories recursively if any
                    for root, dirs, files in os.walk(path, topdown=False):
                        for file in files:
                            os.remove(os.path.join(root, file))
                        for d in dirs:
                            os.rmdir(os.path.join(root, d))
                    os.rmdir(path)
            os.rmdir(base)
        os.makedirs(base)
        try:
            # Non-existent file -> should return False
            nonexist = os.path.join(base, "nope.conf")
            self.assertFalse(check_config_files_for_yes([nonexist]))

            # Existing file without 'yes:' -> still False
            good = os.path.join(base, "good.conf")
            with open(good, "w") as f:
                f.write("no: something\nmaybe: 1\n")
            self.assertFalse(check_config_files_for_yes([good]))

            # Existing file with a line starting with 'yes:' (leading whitespace allowed) -> True
            bad = os.path.join(base, "bad.conf")
            with open(bad, "w") as f:
                f.write("   yes: should-be-replaced\nanother: value\n")
            self.assertTrue(check_config_files_for_yes([bad]))

            # Multiple files: one contains yes: -> True
            self.assertTrue(check_config_files_for_yes([good, bad, nonexist]))

            # Tab-indented 'yes:' should also be detected
            indented = os.path.join(base, "ind.conf")
            with open(indented, "w") as f:
                f.write("\t\tyes: another\n")
            self.assertTrue(check_config_files_for_yes([indented]))
        finally:
            # Cleanup created files and directory
            if os.path.exists(base):
                for name in os.listdir(base):
                    path = os.path.join(base, name)
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        for root, dirs, files in os.walk(path, topdown=False):
                            for file in files:
                                os.remove(os.path.join(root, file))
                            for d in dirs:
                                os.rmdir(os.path.join(root, d))
                        os.rmdir(path)
                os.rmdir(base)
