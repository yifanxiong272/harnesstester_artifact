# file: aider/coders/patch_coder.py:220-288
# asked: {"lines": [225, 226, 227, 230, 232, 233, 238, 239, 240, 242, 244, 246, 247, 249, 250, 252, 254, 257, 258, 259, 260, 261, 263, 264, 265, 266, 268, 269, 270, 271, 272, 274, 276, 279, 280, 281, 282, 283, 285, 286, 288], "branches": [[226, 227], [226, 230], [231, 238], [231, 254], [244, 246], [244, 249], [259, 260], [259, 274], [264, 265], [264, 268], [280, 281], [280, 282]]}
# gained: {"lines": [225, 226, 227, 230, 232, 233, 238, 239, 240, 242, 244, 246, 247, 249, 250, 252, 254, 257, 258, 259, 260, 261, 263, 264, 268, 269, 270, 271, 272, 274, 276, 283, 285, 286, 288], "branches": [[226, 227], [226, 230], [231, 238], [231, 254], [244, 246], [244, 249], [259, 260], [259, 274], [264, 268]]}

import importlib
import types
import pytest

mod = importlib.import_module("aider.coders.patch_coder")
PatchCoder = mod.PatchCoder
DiffError = getattr(mod, "DiffError", Exception)  # Fallback if not present


class DummyIO:
    def __init__(self):
        self.warnings = []

    def read_text(self, path):
        raise NotImplementedError

    def tool_warning(self, msg: str):
        self.warnings.append(msg)


def make_instance():
    # Create instance without calling __init__
    inst = PatchCoder.__new__(PatchCoder)
    # attach defaults
    inst.io = DummyIO()
    # default abs_root_path
    inst.abs_root_path = lambda p: "/abs/" + p
    return inst


def test_get_edits_empty_content():
    inst = make_instance()
    inst.partial_response_content = ""  # empty content -> immediate []
    result = inst.get_edits()
    assert result == []


def test_get_edits_non_patch_content_warns_and_returns_empty():
    inst = make_instance()
    inst.partial_response_content = "this is not a patch\njust some text\n"
    # Ensure no identify_files_needed interaction; don't patch it
    res = inst.get_edits()
    # Should return empty and issue a tool warning
    assert res == []
    assert inst.io.warnings, "Expected a warning for non-patch content"
    assert any("does not appear to be in patch format" in w for w in inst.io.warnings)


def test_get_edits_missing_sentinels_but_patch_like_file_not_found(monkeypatch):
    inst = make_instance()
    # Content lacks Begin/End sentinels but looks patch-like due to "*** Update File:"
    inst.partial_response_content = "*** Update File: a.py\n@@ -1 +1 @@\n-print('x')\n+print('y')\n"
    # Patch the module-level identify_files_needed to return a needed path
    monkeypatch.setattr(mod, "identify_files_needed", lambda content: ["a.py"])
    # Make read_text raise FileNotFoundError
    def read_text_raise(path):
        raise FileNotFoundError("no such file")
    inst.io.read_text = read_text_raise

    with pytest.raises(DiffError) as excinfo:
        inst.get_edits()
    assert "not found" in str(excinfo.value)


def test_get_edits_io_error_while_reading(monkeypatch):
    inst = make_instance()
    inst.partial_response_content = "*** Update File: b.py\n@@\n"
    monkeypatch.setattr(mod, "identify_files_needed", lambda content: ["b.py"])

    def read_text_ioerr(path):
        raise IOError("io problem")
    inst.io.read_text = read_text_ioerr

    with pytest.raises(DiffError) as excinfo:
        inst.get_edits()
    assert "Error reading file b.py" in str(excinfo.value)


def test_get_edits_parse_differror(monkeypatch):
    inst = make_instance()
    # Include proper Begin Patch sentinel so start_index = 1 branch is taken
    inst.partial_response_content = "*** Begin Patch\n*** Update File: c.py\n@@\n*** End Patch\n"
    # identify_files_needed returns c.py; read_text returns content
    monkeypatch.setattr(mod, "identify_files_needed", lambda content: ["c.py"])
    inst.io.read_text = lambda path: "original content"

    # Make _parse_patch_text raise DiffError to trigger ValueError conversion
    def raise_differror(lines, start_index, current_files):
        raise DiffError("parse failed")
    inst._parse_patch_text = raise_differror

    with pytest.raises(ValueError) as excinfo:
        inst.get_edits()
    assert "Error parsing patch content: parse failed" in str(excinfo.value)


def test_get_edits_parse_unexpected_exception(monkeypatch):
    inst = make_instance()
    inst.partial_response_content = "*** Begin Patch\n*** Update File: d.py\n@@\n*** End Patch\n"
    monkeypatch.setattr(mod, "identify_files_needed", lambda content: ["d.py"])
    inst.io.read_text = lambda path: "content"

    def raise_generic(lines, start_index, current_files):
        raise RuntimeError("unexpected")
    inst._parse_patch_text = raise_generic

    with pytest.raises(ValueError) as excinfo:
        inst.get_edits()
    assert "Unexpected error parsing patch: unexpected" in str(excinfo.value)
