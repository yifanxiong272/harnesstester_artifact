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
        """Ensure report_github_issue builds system_info and encodes it into the issue URL."""
        # Prepare deterministic values for pieces used when building system_info
        ver = "9.9.9-test"
        pyver = "3.99.0"
        platform_str = "TestOS/1.0"
        py_info = "PYINFO"
        os_info = "OSINFO"
        git_info = "GITINFO"

        fn = report_github_issue
        g = fn.__globals__

        # Save originals to restore later
        names = ["__version__", "get_python_info", "get_os_info", "get_git_info", "platform", "sys", "webbrowser"]
        originals = {n: g.get(n, None) for n in names}

        try:
            # Inject controlled globals so the output is predictable
            g["__version__"] = ver
            g["get_python_info"] = lambda: py_info
            g["get_os_info"] = lambda: os_info
            g["get_git_info"] = lambda: git_info

            class FakePlatform:
                @staticmethod
                def platform():
                    return platform_str

            g["platform"] = FakePlatform()

            class FakeSys:
                version = pyver + " extra-info"

            g["sys"] = FakeSys()

            # Replace webbrowser with a mock to capture the URL instead of opening a real browser
            mock_browser = unittest.mock.MagicMock()
            mock_browser.open = unittest.mock.MagicMock(return_value=True)
            g["webbrowser"] = mock_browser

            # Call function with confirm=False to skip interactive prompt
            user_issue = "This is the user provided issue body."
            title = "My Test Title"
            fn(user_issue, title=title, confirm=False)

            # Ensure webbrowser.open was called exactly once and inspect the URL argument
            mock_browser.open.assert_called_once()
            opened_url = mock_browser.open.call_args[0][0]

            # Parse the URL and its query parameters
            parsed = urllib.parse.urlparse(opened_url)
            qs = urllib.parse.parse_qs(parsed.query)
            assert "body" in qs and "title" in qs, "URL must contain body and title query parameters"

            body_text = qs["body"][0]
            title_text = qs["title"][0]

            # Reconstruct the expected system_info prefix
            expected_system = (
                f"Aider version: {ver}\n"
                f"Python version: {pyver}\n"
                f"Platform: {platform_str}\n"
                f"{py_info}\n"
                f"{os_info}\n"
                f"{git_info}\n"
                f"\n"
            )

            # Assertions: the body should start with the system info and end with the user issue
            self.assertTrue(
                body_text.startswith(expected_system),
                "The issue body should start with the composed system information",
            )
            self.assertTrue(
                body_text.endswith(user_issue),
                "The issue body should end with the user-provided issue text",
            )
            self.assertEqual(title_text, title)
        finally:
            # Restore originals
            for name, val in originals.items():
                if val is None:
                    g.pop(name, None)
                else:
                    g[name] = val
