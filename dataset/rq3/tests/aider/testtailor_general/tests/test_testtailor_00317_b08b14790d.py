import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repomap')
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
        """Ensure get_supported_languages_md iterates PARSERS and formats rows,
        showing repo map mark only when the SCM file exists."""
        # Prepare a fake PARSERS mapping: extension -> language
        fake_parsers = {"py": "Python", "js": "JavaScript"}

        # Fake get_scm_fname to return different fake paths for languages
        def fake_get_scm_fname(lang):
            # return a string path so Path(fn).exists() will receive it via Path(...)
            return f"/fake/{lang}.scm"

        # Fake Path.exists to return True only for JavaScript's fake path
        def fake_path_exists(self):
            s = str(self)
            return s.endswith("JavaScript.scm")

        # Patch the PARSERS, the get_scm_fname used by the module, and Path.exists
        with patch("grep_ast.parsers.PARSERS", new=fake_parsers), patch(
            f"{get_supported_languages_md.__module__}.get_scm_fname", side_effect=fake_get_scm_fname
        ), patch("pathlib.Path.exists", new=fake_path_exists):
            md = get_supported_languages_md()

        # Basic table structure
        self.assertIn("| Language | File extension | Repo map | Linter |", md)

        # Both languages and their extensions should be present
        self.assertIn("JavaScript", md)
        self.assertIn("Python", md)
        self.assertIn("js", md)
        self.assertIn("py", md)

        # There should be a repo_map check for JavaScript (existing file) and none for Python
        # Each row always has a linter '✓' so total checkmarks = repo_map(1) + linters(2) = 3
        self.assertEqual(md.count("✓"), 3)

        # Verify per-line counts:
        lines = md.splitlines()
        js_line = next((l for l in lines if "JavaScript" in l), "")
        py_line = next((l for l in lines if "Python" in l), "")
        # JavaScript row should contain two checkmarks (repo_map + linter)
        self.assertEqual(js_line.count("✓"), 2)
        # Python row should contain only one checkmark (linter)
        self.assertEqual(py_line.count("✓"), 1)
