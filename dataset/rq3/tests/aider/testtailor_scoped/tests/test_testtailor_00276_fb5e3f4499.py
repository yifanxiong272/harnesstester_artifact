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
        """When .gitignore exists but io.read_text returns None, check_gitignore should return
        early and not attempt to write to the file."""
        tmp = Path.cwd() / "tmp_test_case_XX"
        # ensure a fresh directory for the test
        if tmp.exists():
            try:
                for p in tmp.iterdir():
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        # best effort removal; tests shouldn't leave complex trees here
                        for sub in p.iterdir():
                            if sub.is_file():
                                sub.unlink()
                        p.rmdir()
                tmp.rmdir()
            except Exception:
                # ignore cleanup errors; try to continue with test
                pass
        tmp.mkdir()

        try:
            gitignore = tmp / ".gitignore"
            # Create a .gitignore so gitignore_file.exists() is True
            gitignore.write_text("ignored.txt\n")

            # Create a fake io that simulates read_text returning None
            io = MagicMock()
            io.read_text.return_value = None
            io.tool_output = MagicMock()
            io.tool_error = MagicMock()
            io.write_text = MagicMock()
            io.confirm_ask = MagicMock(return_value=True)

            # Patch the git.Repo used inside check_gitignore to avoid requiring a real repo
            with patch("aider.main.git.Repo") as MockRepo:
                # Ensure repo.ignored(...) returns False so patterns_to_add is non-empty
                MockRepo.return_value.ignored.return_value = False

                # Call the function under test
                check_gitignore(tmp, io)

            # read_text should have been called with the gitignore path
            io.read_text.assert_called_once_with(gitignore)
            # Because read_text returned None, the function should return early and not write
            io.write_text.assert_not_called()
            # The .gitignore file should remain unchanged
            self.assertEqual(gitignore.read_text(), "ignored.txt\n")
        finally:
            # cleanup
            try:
                if gitignore.exists():
                    gitignore.unlink()
                if tmp.exists():
                    tmp.rmdir()
            except Exception:
                pass
