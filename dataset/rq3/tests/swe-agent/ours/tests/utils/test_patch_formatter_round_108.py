from sweagent.utils.patch_formatter import PatchFormatter
import sweagent.utils.patch_formatter as pf_mod
import pytest


class FakePatch:
    def __init__(self, path, is_modified_file=True):
        self.path = path
        self.is_modified_file = is_modified_file


class FakePatchSet(list):
    def __init__(self, patch_str):
        # Return a single modified-file patch with a deterministic path
        super().__init__([FakePatch("a/path.py")])


def test_read_files_patched_populated_round_108():
    """When initialized, PatchFormatter should populate _patched_files for modified files
    using the provided read_method. This verifies the non-original branch exercised
    during __init__ (which calls _read_files(original=False))."""
    original_patchset = pf_mod.PatchSet
    pf_mod.PatchSet = FakePatchSet
    try:
        calls = {}

        def read_method(path):
            # deterministic read output
            calls['last'] = path
            return f"read:{path}"

        pf = PatchFormatter(patch="irrelevant patch text", read_method=read_method)

        # The fake patch has path "a/path.py" and should have been read during __init__
        assert "a/path.py" in pf._patched_files
        assert pf._patched_files["a/path.py"] == "read:a/path.py"
        # ensure our read_method was invoked with the exact path
        assert calls['last'] == "a/path.py"
    finally:
        pf_mod.PatchSet = original_patchset


def test_read_files_original_raises_round_108():
    """Calling _read_files(original=True) for a modified file raises the expected
    NotImplementedError with the exact message.
    """
    original_patchset = pf_mod.PatchSet
    pf_mod.PatchSet = FakePatchSet
    try:
        def read_method(path):
            return "unused"

        pf = PatchFormatter(patch="irrelevant patch text", read_method=read_method)

        with pytest.raises(NotImplementedError) as exc:
            pf._read_files(original=True)

        assert str(exc.value) == "Original file reading not implemented"
    finally:
        pf_mod.PatchSet = original_patchset
