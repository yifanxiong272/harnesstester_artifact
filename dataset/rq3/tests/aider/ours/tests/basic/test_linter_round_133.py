import sys
import importlib
import types
import pytest

# Import the module under test
linter_mod = importlib.import_module('aider.linter')

class FakeLinterNoErrors:
    """Fake Linter that records root passed and returns no errors."""
    def __init__(self, root=None):
        # preserve the attribute so tests can validate construction
        self.root = root
    def lint(self, file_path):
        # Always return empty (no errors)
        return []

class FakeLinterConditional:
    """Fake Linter that returns errors for filepaths containing 'bad'."""
    def __init__(self, root=None):
        self.root = root
        self.seen = []
    def lint(self, file_path):
        self.seen.append(file_path)
        if 'bad' in file_path:
            return ['E_BAD', f'Bad file: {file_path}']
        return []


def test_main_no_args_round_133(monkeypatch, capsys):
    """When no args provided, main should print usage and exit with code 1."""
    # Ensure linter symbol is not invoked in this branch by providing a dummy
    monkeypatch.setattr(linter_mod, 'Linter', FakeLinterNoErrors)
    # Simulate running script with no file arguments
    monkeypatch.setattr(sys, 'argv', ['linter.py'])

    with pytest.raises(SystemExit) as excinfo:
        linter_mod.main()

    # main should exit with code 1 and print the usage message
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Usage: python linter.py <file1> <file2> ..." in captured.out


def test_main_with_args_no_errors_round_133(monkeypatch, capsys):
    """When args are provided and linter returns no errors, nothing should be printed."""
    # Patch the Linter used inside main to our fake that returns no errors
    monkeypatch.setattr(linter_mod, 'Linter', FakeLinterNoErrors)
    monkeypatch.setattr(sys, 'argv', ['linter.py', 'some_file.py'])

    # Running main should not raise and should produce no output
    linter_mod.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == ''


def test_main_with_args_with_errors_round_133(monkeypatch, capsys):
    """When linter returns errors for at least one file, main should print them."""
    fake = FakeLinterConditional()
    # Patch the class in the module to one that returns errors for paths with 'bad'
    def make_fake(root=None):
        # return the same fake instance so we can inspect it after run
        return fake

    monkeypatch.setattr(linter_mod, 'Linter', make_fake)
    # Provide two files: one good and one bad (triggers errors)
    monkeypatch.setattr(sys, 'argv', ['linter.py', 'good.py', 'this_is_bad.py'])

    # Run main; it should not exit but should print the errors for the bad file
    linter_mod.main()
    captured = capsys.readouterr()

    # The FakeLinterConditional returns a list for the bad file; printing that list
    # results in a string like "['E_BAD', 'Bad file: this_is_bad.py']"
    assert "E_BAD" in captured.out
    assert "this_is_bad.py" in captured.out
    # ensure the fake was constructed with a root (preserved contract)
    assert fake.root is not None
