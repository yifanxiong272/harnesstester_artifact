import importlib
import pathlib
import pytest


# Tests for aider.coders.search_replace.proc
# These tests patch module-level symbols to avoid filesystem/network dependencies
# and to deterministically exercise branches in the proc function.


def test_proc_file_not_found_round_009(monkeypatch, tmp_path):
    """If read_text raises FileNotFoundError, proc should return None (early return).
    Covers the FileNotFoundError branch near the start of proc.
    """
    sr = importlib.import_module("aider.coders.search_replace")

    # Make read_text raise FileNotFoundError for the first attempted read
    def fake_read_text_raise(fname):
        raise FileNotFoundError("simulated missing file")

    monkeypatch.setattr(sr, "read_text", fake_read_text_raise)

    # Call proc with a path that doesn't need to exist; behaviour is driven by patched read_text
    result = sr.proc(str(tmp_path))
    assert result is None


def test_proc_various_preprocs_round_009(monkeypatch, tmp_path):
    """Exercise branching that builds method names, writes outputs, and classifies results as pass/WRONG/fail.

    - Patches all_preprocs to a deterministic set of preprocessing tuples.
    - Patches try_strategy to return controlled values depending on the preproc tuple.
    - Patches read_text for initial file reads (search/replace/original), but leaves Path.read_text
      for the 'correct' file to be real so the equality check runs naturally.
    - Uses tmp_path for real file IO of 'original.<method>' files and 'correct'.
    """
    sr = importlib.import_module("aider.coders.search_replace")

    # Prepare deterministic preprocessor tuples that map to different method name mutations
    # Each tuple is (strip_blank, rel_indent, rev_lines)
    p1 = (False, False, False)  # -> method "dmpl"
    p2 = (True, False, False)   # -> method "dmpl_s"
    p3 = (False, True, False)   # -> method "dmpl_i"

    monkeypatch.setattr(sr, "all_preprocs", [p1, p2, p3])

    # Provide fake try_strategy that returns different results per preproc
    def fake_try_strategy(texts, strategy, preproc):
        mapping = {
            p1: "content_pass",
            p2: "content_wrong",
            p3: None,
        }
        # Return None for unknown preprocs to simulate a failing strategy
        return mapping.get(preproc, None)

    monkeypatch.setattr(sr, "try_strategy", fake_try_strategy)

    # Patch read_text to return dummy strings for the initial three reads (search, replace, original)
    def fake_read_text(fname):
        name = pathlib.Path(fname).name
        if name == "search":
            return "search-text"
        if name == "replace":
            return "replace-text"
        if name == "original":
            return "original-text"
        # fall back to raising so unexpected calls are obvious
        raise FileNotFoundError(f"unexpected read_text call: {fname}")

    monkeypatch.setattr(sr, "read_text", fake_read_text)

    # Create the 'correct' file so equality comparisons in proc are exercised
    correct_path = tmp_path / "correct"
    correct_path.write_text("content_pass")

    # Pre-create one of the output files to ensure the exists()/unlink() branch runs
    preexisting = tmp_path / "original.dmpl_s"
    preexisting.write_text("stale")

    # Call proc with the temp directory
    results = sr.proc(str(tmp_path))

    # Expected method names as produced by proc's short_names + mutation logic
    expected = [
        ("dmpl", "pass"),      # content_pass == correct -> 'pass'
        ("dmpl_s", "WRONG"),  # content_wrong != correct -> 'WRONG'
        ("dmpl_i", "fail"),   # None -> 'fail'
    ]

    assert results == expected

    # Check that the files were written for the truthy results and contain expected content
    out_dmpl = tmp_path / "original.dmpl"
    out_dmpl_s = tmp_path / "original.dmpl_s"
    out_dmpl_i = tmp_path / "original.dmpl_i"

    assert out_dmpl.exists()
    assert out_dmpl.read_text() == "content_pass"

    assert out_dmpl_s.exists()
    assert out_dmpl_s.read_text() == "content_wrong"

    # The failing strategy should not have produced a file
    assert not out_dmpl_i.exists()
