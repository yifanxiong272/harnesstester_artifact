import types
import aider.linter as linter


def _make_res(text, lines):
    # simple result object with the attributes used by py_lint
    return types.SimpleNamespace(text=text, lines=set(lines))


def test_py_lint_all_none_round_080(monkeypatch):
    """If all sub-linters return falsy, py_lint should return None."""
    # patch the module-level functions and the instance method where py_lint resolves them
    monkeypatch.setattr(linter, 'basic_lint', lambda rel_fname, code: None)
    monkeypatch.setattr(linter, 'lint_python_compile', lambda fname, code: None)
    monkeypatch.setattr(linter.Linter, 'flake8_lint', lambda self, rel_fname: None)

    res = linter.Linter().py_lint('any.py', 'any.py', 'print(1)')
    assert res is None


def test_py_lint_compose_text_and_lines_round_080(monkeypatch):
    """Multiple non-empty results should concatenate texts with a newline and union lines."""
    # First linter returns None to cover the `if not res: continue` path
    monkeypatch.setattr(linter, 'basic_lint', lambda rel_fname, code: None)
    # compile returns a result with text and lines
    monkeypatch.setattr(
        linter,
        'lint_python_compile',
        lambda fname, code: _make_res('compile-msg', {10, 20})
    )
    # flake8 returns another result to trigger the branch that adds a newline between texts
    monkeypatch.setattr(
        linter.Linter,
        'flake8_lint',
        lambda self, rel_fname: _make_res('flake-msg', {20, 30})
    )

    res = linter.Linter().py_lint('any.py', 'any.py', 'print(1)')
    assert isinstance(res, linter.LintResult)
    # texts should be joined with a single newline in the original order
    assert res.text == 'compile-msg\nflake-msg'
    # lines should be the union of both sets
    assert res.lines == {10, 20, 30}


def test_py_lint_lines_no_text_round_080(monkeypatch):
    """A result with empty text but non-empty lines should still cause a LintResult return."""
    monkeypatch.setattr(
        linter,
        'basic_lint',
        lambda rel_fname, code: _make_res('', {5})
    )
    monkeypatch.setattr(linter, 'lint_python_compile', lambda fname, code: None)
    monkeypatch.setattr(linter.Linter, 'flake8_lint', lambda self, rel_fname: None)

    res = linter.Linter().py_lint('any.py', 'any.py', 'print(1)')
    assert isinstance(res, linter.LintResult)
    # text can be empty string but presence of lines triggers the LintResult
    assert res.text == ''
    assert res.lines == {5}
