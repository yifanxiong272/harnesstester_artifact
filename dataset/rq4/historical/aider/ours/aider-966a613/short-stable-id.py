def test_probe_001():

    from aider.coders.editblock_coder import EditBlockCoder

    # Prepare deterministic paths and edit block
    declared_rel = "missing.txt"
    declared_full = "/root/missing.txt"
    candidate_full = "/root/candidate.txt"

    original = "Two\n"
    updated = "Tooooo\n"

    edits = [(declared_rel, original, updated)]

    # Dummy IO that raises for the declared path and returns content for the candidate
    class DummyIO:
        def __init__(self, files):
            # files: mapping full_path -> content
            self._files = dict(files)
            self.writes = []

        def read_text(self, path):
            if path in self._files:
                return self._files[path]
            raise FileNotFoundError(path)

        def write_text(self, path, content):
            # Record writes for inspection
            self.writes.append((path, content))

    # Candidate file contains the ORIGINAL so do_replace should produce a replacement
    candidate_content = "Line A\n" + original + "Line B\n"
    io = DummyIO({candidate_full: candidate_content})

    # Build a minimal EditBlockCoder instance without invoking __init__
    inst = object.__new__(EditBlockCoder)
    # abs_root_path maps declared relative name to a missing (non-existent in DummyIO) full path
    inst.abs_root_path = lambda p: declared_full
    # abs_fnames lists candidate full paths; include the candidate that has the ORIGINAL
    inst.abs_fnames = [candidate_full]
    inst.io = io
    # fence value passed through to do_replace; choose a common fence tuple
    inst.fence = ("```", "```")
    # get_rel_fname returns a stable relative name for the matched candidate
    inst.get_rel_fname = lambda full: "candidate.txt"

    # Run apply_edits and assert behavior
    try:
        # Call the bound function via the class entrypoint as required by the probe plan
        EditBlockCoder.apply_edits(inst, edits, dry_run=False)
    except Exception as exc:
        # The invariant expects no FileNotFoundError (or any exception) here; fail with context
        raise AssertionError(f"apply_edits raised an unexpected exception: {exc!r}")

    # Primary oracle: exactly one write to the candidate full path, content contains updated and not original
    writes = io.writes
    assert len(writes) == 1, f"Expected exactly one write_text call, got: {writes!r}"
    written_path, written_content = writes[0]
    assert written_path == candidate_full, f"Expected write to {candidate_full!r}, wrote to {written_path!r}"
    assert updated in written_content, "Written content does not contain the UPDATED text"
    assert original not in written_content, "Written content still contains the ORIGINAL text"
