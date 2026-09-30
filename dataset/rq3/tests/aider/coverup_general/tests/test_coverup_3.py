# file: aider/coders/patch_coder.py:412-514
# asked: {"lines": [416, 417, 418, 419, 421, 422, 424, 425, 432, 435, 436, 437, 438, 439, 440, 443, 446, 447, 448, 450, 451, 453, 454, 456, 457, 458, 459, 460, 461, 462, 464, 466, 467, 468, 469, 471, 472, 474, 475, 476, 477, 478, 479, 480, 481, 483, 484, 485, 488, 491, 492, 494, 495, 496, 497, 498, 499, 503, 506, 507, 510, 512, 514], "branches": [[421, 422], [421, 514], [424, 432], [424, 435], [436, 437], [436, 443], [438, 439], [438, 440], [443, 446], [443, 488], [448, 450], [448, 464], [451, 452], [451, 458], [452, 451], [452, 456], [458, 459], [458, 462], [464, 466], [464, 483], [467, 468], [467, 483], [469, 470], [469, 476], [470, 469], [470, 474], [476, 477], [476, 481], [483, 484], [483, 488], [494, 495], [494, 503], [503, 506], [503, 510]]}
# gained: {"lines": [416, 417, 418, 419, 421, 422, 424, 425, 432, 435, 436, 437, 438, 439, 440, 443, 446, 447, 448, 450, 451, 453, 454, 456, 457, 458, 459, 460, 461, 462, 464, 466, 467, 468, 469, 471, 472, 474, 475, 476, 481, 483, 484, 485, 488, 491, 492, 494, 495, 496, 497, 498, 499, 503, 510, 512, 514], "branches": [[421, 422], [424, 432], [424, 435], [436, 437], [436, 443], [438, 439], [443, 446], [443, 488], [448, 450], [448, 464], [451, 452], [451, 458], [452, 451], [452, 456], [458, 459], [458, 462], [464, 466], [464, 483], [467, 468], [467, 483], [469, 470], [470, 474], [476, 481], [483, 484], [483, 488], [494, 495], [494, 503], [503, 510]]}

import pytest
from aider.coders.patch_coder import PatchCoder, DiffError


def make_patch_coder_instance():
    # Avoid calling Coder.__init__ which requires parameters; the method under test
    # does not use instance state, so a bare instance is sufficient.
    return object.__new__(PatchCoder)


def test_breaks_immediately_on_terminator():
    pc = make_patch_coder_instance()
    lines = ["*** Update File: something"]
    action, index, total_fuzz = pc._parse_update_file_sections(lines, 0, "line1\nline2")
    # Should break immediately: no chunks, index unchanged, no fuzz
    assert action.type.name == "UPDATE"
    assert action.chunks == []
    assert index == 0
    assert total_fuzz == 0


def test_parse_update_file_sections_direct_scope_match():
    pc = make_patch_coder_instance()
    # Original file has lines a, b, c
    file_content = "a\nb\nc\n"
    # Provide a scope for 'a' and a single context keep line for 'b'
    lines = ["@@ a", " b", "*** Update File:"]
    action, index, total_fuzz = pc._parse_update_file_sections(lines, 0, file_content)
    # Should have consumed up to the terminator line index (2), no fuzz, and no chunks (only keep)
    assert index == 2
    assert total_fuzz == 0
    assert isinstance(action.chunks, list)
    assert action.chunks == []


def test_scope_not_found_raises_diff_error():
    pc = make_patch_coder_instance()
    file_content = "a\nb\nc\n"
    # Scope 'z' does not exist in file_content, should raise DiffError about scope
    lines = ["@@ z", " b", "*** Update File:"]
    with pytest.raises(DiffError) as exc:
        pc._parse_update_file_sections(lines, 0, file_content)
    msg = str(exc.value)
    assert "Could not find scope context" in msg
    assert "z" in msg


def test_context_not_found_with_eof_marker_raises_diff_error_and_includes_marker():
    pc = make_patch_coder_instance()
    file_content = "line1\nline2\n"
    # Provide a context that does not exist and include '*** End of File' to trigger EOF marker path
    lines = [" unknown_context", "*** End of File", "*** Update File:"]
    with pytest.raises(DiffError) as exc:
        pc._parse_update_file_sections(lines, 0, file_content)
    msg = str(exc.value)
    assert "Could not find patch context" in msg
    assert "*** End of File" in msg
