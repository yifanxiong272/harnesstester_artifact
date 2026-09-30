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
        """When writing .gitignore fails with OSError, check_gitignore should report the error
        and print manual instructions including the patterns to add."""
        # Create a simple directory we can use as a git_root without relying on
        # external temp helpers that might not be imported in the test harness.
        git_root = Path("tmp_test_gitignore_err_dir")
        try:
            git_root.mkdir(exist_ok=True)

            # Fake repo: ensure repo.ignored returns False so patterns are added
            fake_repo = MagicMock()
            fake_repo.ignored = lambda pattern: False

            # Prepare IO object and override behavior to force the write error path
            io = InputOutput(pretty=False, yes=True)
            io.confirm_ask = lambda prompt: True  # accept adding patterns

            # Make write_text raise OSError to trigger the except block
            def raise_oserror(path, content):
                raise OSError("permission denied")

            io.write_text = raise_oserror
            io.tool_error = MagicMock()
            io.tool_output = MagicMock()

            # Patch git.Repo to return our fake repo so check_gitignore proceeds
            with patch("git.Repo", return_value=fake_repo):
                check_gitignore(git_root, io)

            # Assertions: tool_error called with message mentioning .gitignore and the OSError text
            self.assertTrue(io.tool_error.called, "tool_error was not called")
            err_msg = io.tool_error.call_args[0][0]
            self.assertIn("Error when trying to write to", err_msg)
            self.assertIn(".gitignore", err_msg)
            self.assertIn("permission denied", err_msg)

            # tool_output should include the manual instruction and the pattern entry
            outputs = [call.args[0] for call in io.tool_output.call_args_list]
            self.assertTrue(
                any(
                    "Try running with appropriate permissions or manually add these patterns"
                    in o
                    for o in outputs
                ),
                "Did not find manual instruction message in tool_output calls",
            )
            # pattern .aider* should be printed
            self.assertTrue(
                any("  .aider*" in o for o in outputs),
                "Did not find the .aider* pattern printed in tool_output calls",
            )
        finally:
            # cleanup
            try:
                if git_root.exists():
                    for p in git_root.iterdir():
                        if p.is_file():
                            p.unlink()
                        elif p.is_dir():
                            # try rmdir for empty dirs
                            try:
                                p.rmdir()
                            except Exception:
                                pass
                    git_root.rmdir()
            except Exception:
                pass
