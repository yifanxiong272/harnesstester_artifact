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
        """Ensure get_supported_languages_md produces table rows and respects repo map existence."""
        # Create a temporary file name in the current directory to simulate an existing SCM tags file
        tmp_path = Path("tmp_scm_tags_test_file.scm")
        try:
            # Create or overwrite the file to ensure it exists
            tmp_path.write_text("dummy")

            # Prepare a fake PARSERS mapping (extension -> language)
            fake_parsers = {
                "ex1": "LangExists",
                "ex2": "LangMissing",
            }

            # Patch the PARSERS used by the function and patch get_scm_fname in the
            # module where get_supported_languages_md is defined to return the temp
            # file for LangExists and a non-existing path for LangMissing.
            with patch.dict("grep_ast.parsers.PARSERS", fake_parsers, clear=True):
                module_name = get_supported_languages_md.__module__

                def fake_get_scm_fname(lang):
                    if lang == "LangExists":
                        return tmp_path
                    return Path("/this/path/does/not/exist")

                with patch(f"{module_name}.get_scm_fname", side_effect=fake_get_scm_fname):
                    md = get_supported_languages_md()

            # Basic sanity: header present
            self.assertIn("| Language | File extension | Repo map | Linter |", md)

            # Both languages should appear in the table
            self.assertIn("LangExists", md)
            self.assertIn("LangMissing", md)

            # Locate the data rows (skip the header and separator)
            table_lines = [ln for ln in md.splitlines() if ln.startswith("| ")]

            # Find the specific rows for each language
            row_exists = next((r for r in table_lines if "LangExists" in r), None)
            row_missing = next((r for r in table_lines if "LangMissing" in r), None)

            self.assertIsNotNone(row_exists, "Row for LangExists should be present")
            self.assertIsNotNone(row_missing, "Row for LangMissing should be present")

            # Split rows into columns and check the repo_map column (3rd non-empty column)
            def repo_map_col(row):
                parts = [p.strip() for p in row.split("|")]
                # parts layout: ['', lang, ext, repo_map, linter, ''] => index 3 is repo_map
                if len(parts) >= 5:
                    return parts[3]
                return None

            repo_exists = repo_map_col(row_exists)
            repo_missing = repo_map_col(row_missing)

            # LangExists should have a checkmark in the repo_map column, LangMissing should not
            self.assertEqual(repo_exists, "✓")
            self.assertTrue(repo_missing == "" or repo_missing is None)

        finally:
            # Clean up the temporary file if it exists
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
