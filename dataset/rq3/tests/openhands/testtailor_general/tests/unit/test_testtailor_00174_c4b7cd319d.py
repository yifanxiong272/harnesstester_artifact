import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.microagent.microagent')
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
        """When BaseMicroagent.load raises a generic Exception, load_microagents_from_dir
        should catch it and re-raise a ValueError with a detailed message.
        """
        # Prepare a small temporary repo structure in the current working directory
        microagent_dir = Path('tmp_test_repo_microagents') / '.openhands' / 'microagents'
        repo_root = microagent_dir.parent.parent
        try:
            microagent_dir.mkdir(parents=True, exist_ok=True)
            special_file = repo_root / '.cursorrules'
            special_file.write_text('third party content')

            # Patch BaseMicroagent.load to raise a generic Exception to hit the target branch
            with patch.object(BaseMicroagent, 'load', side_effect=Exception('boom')):
                with self.assertRaises(ValueError) as cm:
                    load_microagents_from_dir(microagent_dir)

                err = str(cm.exception)
                # The error message should indicate the file and contain the original exception text
                self.assertIn('Error loading microagent from', err)
                self.assertIn('boom', err)
                # Ensure the special file path is mentioned in the error message
                self.assertIn('.cursorrules', err)
        finally:
            # Best-effort cleanup of created files/directories
            try:
                (repo_root / '.cursorrules').unlink()
            except Exception:
                pass
            try:
                microagent_dir.rmdir()
            except Exception:
                pass
            try:
                (repo_root / '.openhands').rmdir()
            except Exception:
                pass
            try:
                repo_root.rmdir()
            except Exception:
                pass
