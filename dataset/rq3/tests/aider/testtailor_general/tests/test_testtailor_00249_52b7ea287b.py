import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.report')
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
        """Exercise report_github_issue when confirm=True and user accepts the prompt."""
        # Locate the report_github_issue function inside the aider package
        import importlib
        import pkgutil
        import io
        import sys
        import builtins

        aider_pkg = importlib.import_module("aider")
        func = None

        # First try direct attribute
        if hasattr(aider_pkg, "report_github_issue"):
            func = getattr(aider_pkg, "report_github_issue")
            module = aider_pkg
        else:
            # Search submodules for the function
            for finder, name, ispkg in pkgutil.iter_modules(aider_pkg.__path__):
                mod = importlib.import_module(f"aider.{name}")
                if hasattr(mod, "report_github_issue"):
                    func = getattr(mod, "report_github_issue")
                    module = mod
                    break

        self.assertIsNotNone(func, "Could not find report_github_issue in the aider package")

        # Patch input to simulate user pressing Enter (i.e., accept)
        from unittest.mock import patch, MagicMock

        fake_input = ""
        fake_web_open = MagicMock(return_value=True)

        # Capture stdout
        stdout = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout

        try:
            with patch.object(builtins, "input", return_value=fake_input), patch(
                "webbrowser.open", fake_web_open
            ):
                # Call the function with confirm=True to hit the target branch
                func("This is a test issue body", title="UnitTestTitle", confirm=True)
        finally:
            sys.stdout = old_stdout

        output = stdout.getvalue()

        # Assertions about printed output
        self.assertIn("# UnitTestTitle", output)
        self.assertIn("This is a test issue body", output)
        self.assertIn("Please consider reporting this bug to help improve aider!", output)
        self.assertIn("Attempting to open the issue URL in your default web browser...", output)
        self.assertIn("Browser window should be opened.", output)
        self.assertIn("You can also use this URL to file the GitHub Issue:", output)

        # Ensure webbrowser.open was invoked with a URL that contains the title and body params
        self.assertTrue(fake_web_open.called, "webbrowser.open should have been called")
        called_url = fake_web_open.call_args[0][0]
        self.assertIn("title=UnitTestTitle", called_url)
        self.assertIn("body=", called_url)
        # Ensure the original issue body text appears (URL-encoded) in the URL
        self.assertIn("This+is+a+test+issue+body", called_url)
