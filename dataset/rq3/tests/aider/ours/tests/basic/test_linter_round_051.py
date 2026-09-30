import types
import pytest

import aider.linter as linter_mod


class DummyResult:
    def __init__(self, text, lines):
        self.text = text
        self.lines = lines


def make_linter():
    # Construct with typical args (encoding, root). The real __init__ in the module
    # expects encoding and root parameters per source outline.
    return linter_mod.Linter("utf-8", ".")


def test_read_error_round_051(monkeypatch, capsys):
    """Path.read_text raises OSError -> prints message and returns None"""
    monkeypatch.setattr(linter_mod.Path, "read_text", lambda self, encoding, errors: (_ for _ in ()).throw(OSError("nope")))

    L = make_linter()
    res = L.lint("somefile.py")

    captured = capsys.readouterr()
    assert "Unable to read somefile.py" in captured.out
    assert res is None


def test_cmd_strip_and_run_cmd_round_051(monkeypatch):
    """Provided cmd is stripped; Linter.run_cmd is called with stripped value and
    returned LintResult and tree_context are composed into final string.
    """
    # return some code content
    monkeypatch.setattr(linter_mod.Path, "read_text", lambda self, encoding, errors: "print(\"hi\")\n")

    # Ensure filename_to_lang not used in this branch
    monkeypatch.setattr(linter_mod, "filename_to_lang", lambda fname: "should-not-be-used")

    # Provide a fake run_cmd that asserts it gets a stripped command and returns DummyResult
    def fake_run_cmd(self, cmd, rel_fname, code):
        assert cmd == "echo hi"
        return DummyResult("ERR_TEXT", [1])

    monkeypatch.setattr(linter_mod.Linter, "run_cmd", fake_run_cmd, raising=True)

    # tree_context should be called with rel_fname, code and lines and provide a known suffix
    monkeypatch.setattr(linter_mod, "tree_context", lambda rel, code, lines: "CTX")

    L = make_linter()
    out = L.lint("file.py", cmd="  echo hi  ")

    assert out is not None
    assert out.startswith("# Fix any errors below")
    assert "ERR_TEXT" in out
    assert out.endswith("\nCTX")


def test_callable_cmd_round_051(monkeypatch):
    """When resolved cmd is a callable from languages mapping, it is invoked and
    its result is used to build the final output.
    """
    monkeypatch.setattr(linter_mod.Path, "read_text", lambda self, encoding, errors: "x = 1\n")

    # Make filename_to_lang return a language so languages lookup is used
    monkeypatch.setattr(linter_mod, "filename_to_lang", lambda fname: "py")

    # Prepare a callable that will be placed in L.languages
    def callable_linter(fname, rel_fname, code):
        # validate args are passed through
        assert fname.endswith("a.py") or fname.endswith("file.py")
        return DummyResult("CALLABLE_ERR", [2, 3])

    monkeypatch.setattr(linter_mod, "tree_context", lambda rel, code, lines: "CTX_CALLABLE")

    L = make_linter()
    # ensure all_lint_cmd falsey and languages mapping contains callable
    L.all_lint_cmd = None
    L.languages = {"py": callable_linter}

    out = L.lint("a.py", cmd=None)
    assert out is not None
    assert "CALLABLE_ERR" in out
    assert out.endswith("\nCTX_CALLABLE")


def test_language_none_and_basic_lint_none_round_051(monkeypatch):
    """If filename_to_lang returns None -> early return. Also when basic_lint
    returns None (no issues) -> function returns None.
    """
    # Case A: filename_to_lang returns None
    monkeypatch.setattr(linter_mod.Path, "read_text", lambda self, encoding, errors: "code\n")
    monkeypatch.setattr(linter_mod, "filename_to_lang", lambda fname: None)

    L = make_linter()
    res = L.lint("unknown.ext", cmd=None)
    assert res is None

    # Case B: filename_to_lang returns a language, but languages mapping has no cmd
    # and basic_lint returns None -> early return
    monkeypatch.setattr(linter_mod, "filename_to_lang", lambda fname: "py")
    monkeypatch.setattr(linter_mod, "basic_lint", lambda rel, code: None)

    L2 = make_linter()
    L2.all_lint_cmd = None
    L2.languages = {}  # languages.get('py') -> None

    out2 = L2.lint("f.py", cmd=None)
    assert out2 is None
