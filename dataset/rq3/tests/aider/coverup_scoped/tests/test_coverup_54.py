# file: aider/linter.py:288-300
# asked: {"lines": [292, 293, 294, 296, 297, 298, 299, 300], "branches": [[292, 293], [292, 296], [297, 0], [297, 298], [299, 297], [299, 300]]}
# gained: {"lines": [292, 293, 294, 296, 297, 298, 299, 300], "branches": [[292, 293], [292, 296], [297, 0], [297, 298], [299, 297], [299, 300]]}

import pytest
from types import SimpleNamespace

import aider.linter as linter_mod


def test_main_without_args_prints_usage_and_exits(monkeypatch, capsys):
    # Arrange: simulate calling the script with no file arguments
    monkeypatch.setattr("sys.argv", ["linter.py"])
    # Act / Assert: calling main should print usage and exit with code 1
    with pytest.raises(SystemExit) as excinfo:
        linter_mod.main()
    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "Usage: python linter.py <file1> <file2> ..." in captured.out


def test_main_with_args_prints_errors_for_files(monkeypatch, capsys):
    # Arrange: simulate calling the script with two files
    monkeypatch.setattr("sys.argv", ["linter.py", "foo.py", "bar.py"])

    # Create a fake Linter that records calls and returns errors for 'foo.py'
    class FakeLinter:
        def __init__(self, *args, **kwargs):
            self.root = kwargs.get("root", None)
            self.calls = []

        def lint(self, fname, cmd=None):
            # record the call
            self.calls.append((fname, cmd))
            if fname == "foo.py":
                return ["E1"]
            return []

    # Patch the Linter in the module
    monkeypatch.setattr(linter_mod, "Linter", FakeLinter)

    # Act: run main
    linter_mod.main()

    # Capture output and assert expected printed errors
    captured = capsys.readouterr()
    # Only foo.py had errors, so its list representation should be printed
    assert "['E1']" in captured.out
    # bar.py produced no output (empty list should not be printed)
    assert "[]" not in captured.out
