import builtins
from sweagent.utils.patch_formatter import PatchFormatter


class FakeHunk:
    def __init__(self, source_start, source_length, target_start=0, target_length=0):
        self.source_start = source_start
        self.source_length = source_length
        self.target_start = target_start
        self.target_length = target_length


class FakePatch:
    def __init__(self, path, hunks, is_modified_file=True):
        self.path = path
        self._hunks = list(hunks)
        self.is_modified_file = is_modified_file

    def __iter__(self):
        return iter(self._hunks)


def test_get_hunk_lines_original_small_start_round_107():
    """Ensure _get_hunk_lines handles source_start smaller than context_length (max->1).

    This targets the branch where original is True, hitting the max(1, ...) path
    and computing the stop using source_start + source_length + context_length.
    """
    pf = PatchFormatter.__new__(PatchFormatter)
    # Single hunk with source_start=1 and source_length=3, context_length=2
    pf._patch = [FakePatch("file1.py", [FakeHunk(source_start=1, source_length=3)])]

    result = pf._get_hunk_lines(original=True, context_length=2)

    # start should be max(1, 1 - 2) == 1
    # stop should be 1 + 3 + 2 == 6
    assert result == {"file1.py": ([1], [6])}


def test_get_hunk_lines_original_multiple_hunks_and_skip_round_107():
    """Multiple hunks produce lists of starts/stops; non-modified files are skipped.

    This ensures iteration over hunks appends corresponding starts/stops and that
    patches with is_modified_file=False are ignored.
    """
    pf = PatchFormatter.__new__(PatchFormatter)

    # Two hunks for file2.py and one patch that should be skipped
    hunk_a = FakeHunk(source_start=10, source_length=2)
    hunk_b = FakeHunk(source_start=3, source_length=1)
    modified_patch = FakePatch("file2.py", [hunk_a, hunk_b], is_modified_file=True)
    skipped_patch = FakePatch("ignored.py", [FakeHunk(source_start=5, source_length=1)], is_modified_file=False)

    pf._patch = [modified_patch, skipped_patch]

    result = pf._get_hunk_lines(original=True, context_length=4)

    # For hunk_a: start = max(1, 10 - 4) = 6 ; stop = 10 + 2 + 4 = 16
    # For hunk_b: start = max(1, 3 - 4) = 1  ; stop = 3 + 1 + 4 = 8
    assert "file2.py" in result
    starts, stops = result["file2.py"]
    assert starts == [6, 1]
    assert stops == [16, 8]

    # skipped patch must not appear in the result
    assert "ignored.py" not in result
