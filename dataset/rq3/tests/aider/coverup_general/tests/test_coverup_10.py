# file: aider/coders/patch_coder.py:220-288
# asked: {"lines": [225, 226, 227, 230, 232, 233, 238, 239, 240, 242, 244, 246, 247, 249, 250, 252, 254, 257, 258, 259, 260, 261, 263, 264, 265, 266, 268, 269, 270, 271, 272, 274, 276, 279, 280, 281, 282, 283, 285, 286, 288], "branches": [[226, 227], [226, 230], [231, 238], [231, 254], [244, 246], [244, 249], [259, 260], [259, 274], [264, 265], [264, 268], [280, 281], [280, 282]]}
# gained: {"lines": [225, 226, 227, 230, 232, 233, 238, 239, 240, 242, 244, 246, 247, 249, 250, 252, 257, 258, 259, 260, 261, 263, 264, 265, 266, 268, 269, 270, 271, 272, 274, 276, 279, 280, 281, 282, 283, 285, 286, 288], "branches": [[226, 227], [226, 230], [231, 238], [244, 246], [244, 249], [259, 260], [259, 274], [264, 265], [264, 268], [280, 281], [280, 282]]}

import types
import pytest

from aider.coders.patch_coder import PatchCoder, DiffError


class DummyIO:
    def __init__(self, read_text_behavior=None):
        # read_text_behavior can be:
        # - a callable taking (abs_path) and returning content or raising
        # - a mapping dict abs_path -> content
        self._behavior = read_text_behavior
        self.warnings = []

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def read_text(self, abs_path):
        if callable(self._behavior):
            return self._behavior(abs_path)
        if isinstance(self._behavior, dict):
            if abs_path in self._behavior:
                return self._behavior[abs_path]
            # emulate file not found by raising FileNotFoundError
            raise FileNotFoundError(abs_path)
        # default: return None to emulate unreadable
        return None


def make_coder_with_content(content, io_obj=None):
    coder = object.__new__(PatchCoder)
    coder.partial_response_content = content
    coder.io = io_obj or DummyIO()
    # abs_root_path should map relative path to an absolute path string used by DummyIO
    coder.abs_root_path = lambda rel: f"/abs/{rel}"
    return coder


def test_empty_content_returns_empty_list():
    coder = make_coder_with_content("   ")
    res = coder.get_edits()
    assert res == []


def test_non_patch_like_warns_and_returns_empty():
    io = DummyIO()
    coder = make_coder_with_content("This is not a patch", io_obj=io)
    res = coder.get_edits()
    assert res == []
    # Should have warned once about not being in patch format
    assert any("Response does not appear to be in patch format." in w for w in io.warnings)


def test_missing_sentinel_but_patch_like_read_text_returns_none_raises_differror():
    # content looks like a patch (has Update File) but missing Begin/End sentinels
    content = "*** Update File: foo.txt\n@@ -1,2 +1,2 @@\n- old\n+ new\n"
    io = DummyIO()  # default behavior returns None (unreadable)
    coder = make_coder_with_content(content, io_obj=io)
    # Ensure warning about missing sentinels appears and unreadable file raises DiffError
    with pytest.raises(DiffError) as exc:
        coder.get_edits()
    # Confirm the DiffError indicates unreadable or missing file (accept either phrasing)
    msg = str(exc.value)
    assert ("could not be read" in msg) or ("File referenced in patch not found" in msg)
    assert any("Patch format warning" in w for w in io.warnings)


def test_read_text_raises_filenotfound_converted_to_differror():
    content = "*** Update File: missing.txt\n@@\n"
    # behavior callable that raises FileNotFoundError
    def behavior(abs_path):
        raise FileNotFoundError(abs_path)

    io = DummyIO(read_text_behavior=behavior)
    coder = make_coder_with_content(content, io_obj=io)
    with pytest.raises(DiffError) as exc:
        coder.get_edits()
    assert "File referenced in patch not found: missing.txt" in str(exc.value)


def test_read_text_raises_ioerror_converted_to_differror():
    content = "*** Update File: bad.txt\n@@\n"
    def behavior(abs_path):
        raise IOError("boom")
    io = DummyIO(read_text_behavior=behavior)
    coder = make_coder_with_content(content, io_obj=io)
    with pytest.raises(DiffError) as exc:
        coder.get_edits()
    assert "Error reading file bad.txt" in str(exc.value)
    assert "boom" in str(exc.value)


def test_successful_parse_returns_actions_list():
    content = "*** Update File: foo.txt\n@@\n- a\n+ b\n"
    # Provide file content for foo.txt
    io = DummyIO({"/abs/foo.txt": "a\nb\n"})
    coder = make_coder_with_content(content, io_obj=io)

    # monkeypatch _parse_patch_text to return an object with actions attribute
    fake_patch = types.SimpleNamespace(actions={"foo.txt": "SOME_ACTION"})
    def fake_parse(lines, start_index, current_files):
        # assert we get the expected start_index (no sentinel => 0)
        assert start_index == 0
        assert "foo.txt" in current_files
        return fake_patch

    coder._parse_patch_text = fake_parse

    res = coder.get_edits()
    assert res == [("foo.txt", "SOME_ACTION")]


def test_parse_raises_differror_is_wrapped_as_valueerror():
    content = "*** Update File: foo.txt\n@@\n"
    io = DummyIO({"/abs/foo.txt": "content"})
    coder = make_coder_with_content(content, io_obj=io)

    def raise_diff(lines, start_index, current_files):
        raise DiffError("parse problem")
    coder._parse_patch_text = raise_diff

    with pytest.raises(ValueError) as exc:
        coder.get_edits()
    assert "Error parsing patch content: parse problem" in str(exc.value)


def test_parse_raises_unexpected_exception_wrapped_as_valueerror():
    content = "*** Update File: foo.txt\n@@\n"
    io = DummyIO({"/abs/foo.txt": "content"})
    coder = make_coder_with_content(content, io_obj=io)

    def raise_unexpected(lines, start_index, current_files):
        raise RuntimeError("unexpected")
    coder._parse_patch_text = raise_unexpected

    with pytest.raises(ValueError) as exc:
        coder.get_edits()
    assert "Unexpected error parsing patch: " in str(exc.value)
    assert "unexpected" in str(exc.value)
