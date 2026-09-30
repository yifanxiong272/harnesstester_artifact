# file: aider/coders/patch_coder.py:642-706
# asked: {"lines": [647, 649, 651, 652, 653, 656, 658, 661, 663, 665, 666, 667, 671, 675, 676, 679, 680, 682, 685, 686, 687, 688, 689, 690, 694, 697, 700, 703, 704, 705, 706], "branches": [[647, 649], [647, 651], [658, 661], [658, 700], [663, 665], [663, 671], [682, 685], [682, 694], [704, 705], [704, 706]]}
# gained: {"lines": [647, 649, 651, 652, 653, 656, 658, 661, 663, 665, 666, 667, 671, 675, 676, 679, 680, 682, 685, 686, 687, 688, 689, 690, 694, 697, 700, 703, 704, 705, 706], "branches": [[647, 649], [647, 651], [658, 661], [658, 700], [663, 665], [663, 671], [682, 685], [682, 694], [704, 705], [704, 706]]}

import pytest
from types import SimpleNamespace

from aider.coders.patch_coder import PatchCoder, DiffError, ActionType


def make_coder_without_init():
    # Create an instance without calling Coder.__init__
    return object.__new__(PatchCoder)


def test_non_update_raises():
    coder = make_coder_without_init()
    action = SimpleNamespace(type=ActionType.ADD, chunks=[], path="some/path")
    with pytest.raises(DiffError) as exc:
        coder._apply_update("a\nb\n", action, "some/path")
    assert "_apply_update called with non-update action" in str(exc.value)


def test_overlapping_chunks_raises():
    coder = make_coder_without_init()
    text = "a\nb\nc\nd\n"
    chunk1 = SimpleNamespace(orig_index=1, del_lines=["b", "c"], ins_lines=[])
    chunk2 = SimpleNamespace(orig_index=2, del_lines=["x"], ins_lines=[])
    action = SimpleNamespace(type=ActionType.UPDATE, chunks=[chunk1, chunk2], path="file.txt")
    with pytest.raises(DiffError) as exc:
        coder._apply_update(text, action, "file.txt")
    assert "Overlapping or out-of-order chunk detected" in str(exc.value)


def test_mismatch_deleted_lines_raises():
    coder = make_coder_without_init()
    text = "line1\nline2\nline3\n"
    chunk = SimpleNamespace(orig_index=1, del_lines=["WRONG"], ins_lines=[])
    action = SimpleNamespace(type=ActionType.UPDATE, chunks=[chunk], path="mismatch.txt")
    with pytest.raises(DiffError) as exc:
        coder._apply_update(text, action, "mismatch.txt")
    msg = str(exc.value)
    assert "Mismatch applying patch near line" in msg
    assert "- WRONG" in msg
    assert "Found lines in file" in msg


def test_successful_update_adds_trailing_newline():
    coder = make_coder_without_init()
    text = "a\nb\n"
    chunk = SimpleNamespace(orig_index=1, del_lines=["b"], ins_lines=["B"])
    action = SimpleNamespace(type=ActionType.UPDATE, chunks=[chunk], path="up.txt")
    result = coder._apply_update(text, action, "up.txt")
    assert result == "a\nB\n"


def test_empty_original_and_no_chunks_returns_empty_string():
    coder = make_coder_without_init()
    text = ""
    action = SimpleNamespace(type=ActionType.UPDATE, chunks=[], path="empty.txt")
    result = coder._apply_update(text, action, "empty.txt")
    assert result == ""


def test_chunk_sorting_and_multiple_changes_applied_in_order():
    coder = make_coder_without_init()
    orig = "line0\nline1\nline2\nline3\n"
    chunkA = SimpleNamespace(orig_index=2, del_lines=["line2"], ins_lines=["LINE2"])
    chunkB = SimpleNamespace(orig_index=0, del_lines=[], ins_lines=["NEW0"])
    action = SimpleNamespace(type=ActionType.UPDATE, chunks=[chunkA, chunkB], path="sorted.txt")
    result = coder._apply_update(orig, action, "sorted.txt")
    expected = "NEW0\nline0\nline1\nLINE2\nline3\n"
    assert result == expected
