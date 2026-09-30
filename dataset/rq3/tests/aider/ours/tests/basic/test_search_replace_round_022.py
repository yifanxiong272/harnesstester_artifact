import importlib
from pathlib import Path
import pytest


SEARCH_REPLACE = importlib.import_module("aider.coders.search_replace")


def _make_fake_proc(mapping):
    """Return a proc-like function that returns mapping[str(dname)].

    mapping keys should be strings (str(Path) or directory strings)."""

    def _proc(dname):
        key = str(dname)
        # Return a copy to emulate fresh results per call
        return list(mapping.get(key, []))

    return _proc


def test_main_strings_round_022(monkeypatch, capsys):
    """When dnames are plain strings, main should build and print a table.

    This covers the normal path where results_matrix keys (strings) match
    the population step using str(dname).
    """
    # Arrange: patch tqdm to be identity, patch colorize_result to predictable format
    monkeypatch.setattr(SEARCH_REPLACE, "tqdm", lambda x: x)
    monkeypatch.setattr(SEARCH_REPLACE, "colorize_result", lambda r: f"<{r}>")

    # Construct deterministic proc results for two directories
    mapping = {
        "dir1": [("A", "pass"), ("B", "fail")],
        "dir2": [("A", "fail"), ("B", "pass")],
    }
    monkeypatch.setattr(SEARCH_REPLACE, "proc", _make_fake_proc(mapping))

    # Act: call main with directory names as strings
    SEARCH_REPLACE.main(["dir1", "dir2"])

    # Capture output
    out = capsys.readouterr().out

    # Assert: header printed and method names present
    assert "Directory" in out
    assert "A" in out and "B" in out

    # Assert: colorized results appear (we patched colorize_result to wrap with <>)
    assert "<pass>" in out and "<fail>" in out

    # Assert: each directory row is present with its name
    assert "dir1" in out and "dir2" in out


def test_main_path_keyerror_round_022(monkeypatch):
    """When dnames are Path objects, population uses str(dname) to index
    results_matrix whose keys are Path objects -> leads to KeyError.

    This triggers the branch where results_matrix lookup by str(dname)
    does not find the originally-created key.
    """
    monkeypatch.setattr(SEARCH_REPLACE, "tqdm", lambda x: x)
    monkeypatch.setattr(SEARCH_REPLACE, "colorize_result", lambda r: f"[{r}]")

    # Provide a proc that returns one method so the population loop will run
    mapping = {
        # Use string keys for mapping but we will pass Path objects to main
        str(Path("dirX")): [("M", "pass")],
    }
    monkeypatch.setattr(SEARCH_REPLACE, "proc", _make_fake_proc(mapping))

    # Act & Assert: calling main with Path objects should raise KeyError when
    # results_matrix is populated using str(dname) while keys are Path objects.
    with pytest.raises(KeyError):
        SEARCH_REPLACE.main([Path("dirX")])
