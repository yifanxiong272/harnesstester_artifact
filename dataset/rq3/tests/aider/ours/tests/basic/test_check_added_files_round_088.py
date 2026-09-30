import types
import pytest

from aider.coders import base_coder
from aider.coders.base_coder import Coder
from aider import urls


class DummyIO:
    def __init__(self, content_map=None):
        # content_map: fname -> content string
        self.content_map = content_map or {}
        self.warnings = []

    def read_text(self, fname):
        # return mapped content or empty string if not found
        return self.content_map.get(fname, "")

    def tool_warning(self, message):
        # record warnings (called twice in success path)
        self.warnings.append(message)


class DummyModel:
    def __init__(self, token_map=None, default=0):
        # token_map: content -> token_count or fname->count (we'll support both)
        self.token_map = token_map or {}
        self.default = default
        self.calls = []

    def token_count(self, content):
        # record call and return configured token count deterministically
        self.calls.append(content)
        if content in self.token_map:
            return self.token_map[content]
        # if token_map keyed by filename (rare), return by that too
        if content in self.token_map:  # kept for clarity; same check as above
            return self.token_map[content]
        return self.default


def make_coder_instance(abs_fnames, io_obj, main_model, warning_given=False):
    # Create a Coder instance without invoking its heavy __init__
    coder = object.__new__(Coder)
    coder.abs_fnames = list(abs_fnames)
    coder.io = io_obj
    coder.main_model = main_model
    coder.warning_given = warning_given
    return coder


def test_warning_given_short_circuits_round_088(monkeypatch):
    """If warning_given is already True, check_added_files returns immediately and does not call io.tool_warning."""
    # Patch is_image_file to something deterministic (shouldn't matter here)
    monkeypatch.setattr(base_coder, "is_image_file", lambda fname: False)

    io = DummyIO({"a.txt": "x"})
    model = DummyModel(default=100)
    coder = make_coder_instance(["a.txt", "b.txt", "c.txt", "d.txt"], io, model, warning_given=True)

    coder.check_added_files()

    # No warnings should have been emitted and warning_given remains True
    assert io.warnings == []
    assert coder.warning_given is True


def test_less_than_warn_files_no_warning_round_088(monkeypatch):
    """If number of files is less than the warning threshold (4), no warning is produced."""
    monkeypatch.setattr(base_coder, "is_image_file", lambda fname: False)

    io = DummyIO({"a.txt": "alpha", "b.txt": "beta", "c.txt": "gamma"})
    model = DummyModel(default=10)
    # only 3 files -> should return early at the num_files check
    coder = make_coder_instance(["a.txt", "b.txt", "c.txt"], io, model, warning_given=False)

    coder.check_added_files()

    assert io.warnings == []
    # ensure token_count never called because we never iterate filenames
    assert model.calls == []
    assert coder.warning_given is False


def test_images_skipped_and_low_tokens_round_088(monkeypatch):
    """Image files are skipped; non-image files are token-counted and if tokens < threshold no warning is produced."""
    # Treat filenames ending with .png as images
    monkeypatch.setattr(base_coder, "is_image_file", lambda fname: fname.endswith(".png"))

    # Prepare 4 files (meets warn_number_of_files). One is image and should be skipped.
    files = ["one.txt", "two.png", "three.txt", "four.txt"]
    content_map = {
        "one.txt": "a",  # small content
        "two.png": "<binary>",
        "three.txt": "b",
        "four.txt": "c",
    }
    io = DummyIO(content_map)

    # Make token_count return 1000 for any small content -> total tokens 3000 < 20480
    model = DummyModel(default=1000)
    coder = make_coder_instance(files, io, model, warning_given=False)

    coder.check_added_files()

    # Image file should have been skipped: model.token_count called for 3 non-image files
    assert len(model.calls) == 3
    # No warnings expected because total tokens < warn threshold
    assert io.warnings == []
    assert coder.warning_given is False


def test_trigger_warning_round_088(monkeypatch):
    """When enough (>=4) files are added and token total >= threshold, two warnings are emitted and warning_given becomes True."""
    monkeypatch.setattr(base_coder, "is_image_file", lambda fname: False)

    # Four non-image files -> num_files >= 4
    files = ["a.txt", "b.txt", "c.txt", "d.txt"]
    # Read_text returns content per filename; token_count will use content string as key to token_map
    content_map = {f: f * 10 for f in files}
    io = DummyIO(content_map)

    # Set token counts such that sum >= 20*1024 (20480)
    # For determinism, return 6000 for each file -> total 24000
    token_map = {content_map[f]: 6000 for f in files}
    model = DummyModel(token_map=token_map, default=0)

    coder = make_coder_instance(files, io, model, warning_given=False)

    coder.check_added_files()

    # Should have called token_count for each of the 4 files
    assert len(model.calls) == 4
    # Two tool warnings expected: a message string and urls.edit_errors
    assert len(io.warnings) == 2
    assert "Warning" in io.warnings[0]
    # second warning should be the urls.edit_errors object/value
    assert io.warnings[1] == urls.edit_errors
    # Final state should mark warning_given True
    assert coder.warning_given is True
