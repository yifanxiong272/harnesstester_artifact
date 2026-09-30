# file: aider/repomap.py:832-849
# asked: {"lines": [833, 835, 839, 841, 842, 843, 844, 845, 847, 849], "branches": [[841, 842], [841, 847]]}
# gained: {"lines": [833, 835, 839, 841, 842, 843, 844, 845, 847, 849], "branches": [[841, 842], [841, 847]]}

import sys
import types
from pathlib import Path

import pytest

from aider import repomap


def _make_grep_parsers_module(parsers_dict):
    mod = types.ModuleType("grep_ast.parsers")
    mod.PARSERS = parsers_dict
    return mod


def _lines_from_md(md):
    # return the content lines excluding leading/trailing blank lines
    return [ln for ln in md.splitlines() if ln.strip() != ""]


def _parse_table_line(line):
    # return the 4 columns as stripped strings for a table row like:
    # | Language | File extension | Repo map | Linter |
    parts = [p.strip() for p in line.split("|")[1:-1]]
    return parts  # [language, extension, repo_map, linter]


def test_get_supported_languages_md_no_repo_files(monkeypatch):
    # Set up a fake grep_ast.parsers module with two entries
    parsers = {".py": "Python", ".js": "JavaScript"}
    parsers_mod = _make_grep_parsers_module(parsers)
    # Install into sys.modules so the dynamic import inside the function finds it
    monkeypatch.setitem(sys.modules, "grep_ast", types.ModuleType("grep_ast"))
    monkeypatch.setitem(sys.modules, "grep_ast.parsers", parsers_mod)

    # Patch get_scm_fname to return non-existent paths so repo_map column is empty
    def fake_get_scm_fname(lang):
        return f"/nonexistent/path/{lang}.repomap"

    monkeypatch.setattr(repomap, "get_scm_fname", fake_get_scm_fname)

    md = repomap.get_supported_languages_md()
    assert md.startswith("\n| Language | File extension | Repo map | Linter |")
    lines = _lines_from_md(md)

    # header + separator + 2 language rows => at least 4 lines
    assert len(lines) >= 4

    # The languages should be sorted alphabetically by language name
    # i.e., JavaScript comes before Python
    language_rows = [ln for ln in lines if ln.startswith("| " ) and not ln.startswith("| Language")]
    assert any("JavaScript" in row for row in language_rows)
    assert any("Python" in row for row in language_rows)
    # Order check: JavaScript row should appear before Python row
    js_index = next(i for i, r in enumerate(language_rows) if "JavaScript" in r)
    py_index = next(i for i, r in enumerate(language_rows) if "Python" in r)
    assert js_index < py_index

    # Parse rows and verify repo_map column is empty and linter is present
    for row in language_rows:
        lang, ext, repo_map, linter = _parse_table_line(row)
        assert linter == "✓"
        # repo_map should be empty (no file exists)
        assert repo_map == ""


def test_get_supported_languages_md_with_some_repo_files(monkeypatch, tmp_path):
    # Create files for one language (Python) and leave JavaScript without a file
    parsers = {".py": "Python", ".js": "JavaScript"}
    parsers_mod = _make_grep_parsers_module(parsers)
    monkeypatch.setitem(sys.modules, "grep_ast", types.ModuleType("grep_ast"))
    monkeypatch.setitem(sys.modules, "grep_ast.parsers", parsers_mod)

    # create a repo-map file for Python
    python_map = tmp_path / "Python.map"
    python_map.write_text("dummy")

    # get_scm_fname should return the existing file for Python and a non-existent one for JavaScript
    def fake_get_scm_fname(lang):
        if lang == "Python":
            return str(python_map)
        return str(tmp_path / f"{lang}.missing")

    monkeypatch.setattr(repomap, "get_scm_fname", fake_get_scm_fname)

    md = repomap.get_supported_languages_md()
    lines = _lines_from_md(md)

    # Extract language rows (skip header/separator)
    language_rows = [ln for ln in lines if ln.startswith("| ") and not ln.startswith("| Language")]

    # Build a mapping from language to its columns and assert repo_map/linter values
    mapping = {}
    for row in language_rows:
        lang, ext, repo_map_col, linter = _parse_table_line(row)
        mapping[lang] = {"ext": ext, "repo_map": repo_map_col, "linter": linter}

    # linter always supported
    assert mapping["Python"]["linter"] == "✓"
    assert mapping["JavaScript"]["linter"] == "✓"

    # Python should have a repo_map check mark because we created the file
    assert mapping["Python"]["repo_map"] == "✓"
    # JavaScript should have no repo_map check mark
    assert mapping["JavaScript"]["repo_map"] == ""

    # Extensions should match the provided parsers mapping (note mapping flips ext<->lang in code)
    assert mapping["Python"]["ext"] == ".py"
    assert mapping["JavaScript"]["ext"] == ".js"
