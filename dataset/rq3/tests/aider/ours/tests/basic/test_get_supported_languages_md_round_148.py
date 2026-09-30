import importlib
import sys
import types

import aider.repomap as repomap

import pytest


def _make_parsers_module(mapping):
    mod = types.ModuleType("grep_ast.parsers")
    mod.PARSERS = mapping
    return mod


def test_single_entry_repo_map_exists_round_148(monkeypatch):
    """
    Single-language PARSERS mapping. get_scm_fname returns a filename whose
    Path.exists is True for that name. Assert that the generated markdown
    contains the language row, the repo_map checkmark, and the linter checkmark.
    """
    # Provide a deterministic PARSERS mapping: ext -> lang
    parsers_mod = _make_parsers_module({"ext1": "Python"})
    monkeypatch.setitem(sys.modules, "grep_ast.parsers", parsers_mod)

    # Patch get_scm_fname to return a filename whose Path.name we can test
    monkeypatch.setattr(repomap, "get_scm_fname", lambda lang: f"{lang}.repo")

    # Make Path.exists return True only when the filename matches "Python.repo"
    def exists_for_python(self):
        return self.name == "Python.repo"

    monkeypatch.setattr(repomap.Path, "exists", exists_for_python, raising=True)

    # Call the function under test
    res = repomap.get_supported_languages_md()

    # Basic header sanity
    assert "| Language | File extension | Repo map | Linter |" in res

    # There should be a row for Python, and because exists_for_python is True it should show the checkmark
    check = "\u2713"
    lines = [ln for ln in res.splitlines() if ln.strip()]
    # Find the line that contains the language
    python_lines = [ln for ln in lines if "Python" in ln]
    assert python_lines, "expected a row containing 'Python'"
    # That row should include the repo map checkmark and the linter checkmark
    assert check in python_lines[0]
    assert python_lines[0].count(check) >= 1

    # The returned markdown should end with a blank line (function appends an extra '\n')
    assert res.endswith("\n\n")


def test_multiple_entries_order_and_missing_repo_map_round_148(monkeypatch):
    """
    Multiple entries in PARSERS. Check that the output rows are sorted by
    language name (the code builds tuples (lang, ext) and sorts them), and
    that repo_map is empty for languages whose file does not "exist".
    """
    # Choose languages that will sort: 'ALang' should come before 'ZLang'
    parsers_mod = _make_parsers_module({"aext": "ZLang", "zext": "ALang"})
    monkeypatch.setitem(sys.modules, "grep_ast.parsers", parsers_mod)

    # Map language -> filename
    monkeypatch.setattr(repomap, "get_scm_fname", lambda lang: f"/some/path/{lang}.repo")

    # exists returns True only for ALang.repo
    def exists_for_some(self):
        return self.name == "ALang.repo"

    monkeypatch.setattr(repomap.Path, "exists", exists_for_some, raising=True)

    res = repomap.get_supported_languages_md()

    # Confirm header present
    assert "| Language | File extension | Repo map | Linter |" in res

    # Extract non-empty lines that look like table rows (contain a pipe and a language)
    rows = [ln for ln in res.splitlines() if ln.strip().startswith("|") and not ln.strip().startswith("|:--")]

    # Find indices of ALang and ZLang rows and confirm ordering ALang before ZLang
    al_idx = next(i for i, r in enumerate(rows) if "ALang" in r)
    z_idx = next(i for i, r in enumerate(rows) if "ZLang" in r)
    assert al_idx < z_idx, "Expected ALang to appear before ZLang in sorted output"

    check = "\u2713"
    # ALang should have a repo_map checkmark (exists_for_some returns True for ALang.repo)
    assert check in rows[al_idx], "ALang row should include repo_map checkmark"

    # ZLang should NOT have the repo_map checkmark
    assert check not in rows[z_idx] or rows[z_idx].count(check) < 2, "ZLang row should not include repo_map checkmark"

    # Linter support is always shown as a checkmark; ensure each row has at least one (the linter)
    for r in rows:
        assert check in r, f"Expected linter checkmark in row: {r}"
