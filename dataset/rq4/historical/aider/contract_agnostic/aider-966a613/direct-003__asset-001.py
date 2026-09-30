import pytest

from aider.coders import editblock_coder as eb


def test_probe_001_failed_edit_reads_diagnostic_and_raises_value_error():
    # Bind the original unbound method
    apply_edits = eb.EditBlockCoder.apply_edits

    # Deterministically force do_replace to indicate 'no match'
    eb.do_replace = lambda full_path, content, original, updated, fence: ""

    # IO stub: first read returns content, second read for same path raises FileNotFoundError
    class DummyIO:
        def __init__(self):
            self._counts = {}

        def read_text(self, path):
            cnt = self._counts.get(path, 0) + 1
            self._counts[path] = cnt
            if cnt > 1:
                raise FileNotFoundError("simulated missing during diagnostic")
            return "original file contents\n"

        def write_text(self, path, content):
            # Should not be called in this probe because do_replace returns falsy
            raise AssertionError("write_text should not be called in this probe")

    # Minimal dummy 'self' with only the attributes used by apply_edits
    class DummySelf:
        def __init__(self):
            self.fence = ("```", "```")
            # abs_root_path should return a stable string per input path
            self.abs_root_path = lambda p: f"/abs/{p}"
            # No alternate files to search
            self.abs_fnames = []
            self.get_rel_fname = lambda p: p
            self.io = DummyIO()

    dummy = DummySelf()
    edits = [("some.txt", "orig_line\n", "updated_line\n")]

    # Primary oracle: when an edit fails and dry_run=False, a ValueError with the diagnostic should be raised.
    with pytest.raises(ValueError):
        apply_edits(dummy, edits, dry_run=False)
