import types
import builtins
from types import SimpleNamespace
import pytest

import pr_agent.git_providers.bitbucket_provider as bbmod


class _NoOpLogger:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def exception(self, *a, **k):
        pass


def _make_linked_side(path, has_links=True):
    class Side:
        def __init__(self, path, has_links):
            self.path = path
            self._has_links = has_links

        def get_data(self, key):
            if key != 'links':
                return None
            if self._has_links:
                return {'self': {'href': f'https://example/{self.path}'}}
            return {}

    return Side(path, has_links)


class _MockFilePatchInfo:
    def __init__(self, original, new, diff, path):
        self.original = original
        self.new = new
        self.diff = diff
        self.path = path
        self.edit_type = None


class _MockEditType:
    ADDED = 'added'
    DELETED = 'deleted'
    MODIFIED = 'modified'
    RENAMED = 'renamed'


def _make_diff(name, status, lines_added=1, lines_removed=0, old_links=True, new_links=True):
    # Create an object similar to what bitbucket diffstat/diff would produce
    data = {'status': status, 'lines_added': lines_added, 'lines_removed': lines_removed}
    return SimpleNamespace(
        data=data,
        new=_make_linked_side(name, new_links),
        old=_make_linked_side(name, old_links)
    )


@pytest.fixture(autouse=True)
def patch_module_defaults(monkeypatch):
    # Patch logger, FilePatchInfo, EDIT_TYPE, helper functions, settings, and MAX_FILES_ALLOWED_FULL
    monkeypatch.setattr(bbmod, 'get_logger', lambda: _NoOpLogger())
    monkeypatch.setattr(bbmod, 'FilePatchInfo', _MockFilePatchInfo)
    monkeypatch.setattr(bbmod, 'EDIT_TYPE', _MockEditType)
    monkeypatch.setattr(bbmod, '_gef_filename', lambda d: d.new.path)
    monkeypatch.setattr(bbmod, 'is_valid_file', lambda p: True)
    monkeypatch.setattr(bbmod, 'get_settings', lambda: {})
    # Make MAX_FILES_ALLOWED_FULL reasonably large so counter_valid path uses full content
    monkeypatch.setattr(bbmod, 'MAX_FILES_ALLOWED_FULL', 1000)
    yield


def test_cached_diff_files_round_003():
    # If diff_files is already set, get_diff_files should simply return it (lines 215-216)
    provider = object.__new__(bbmod.BitbucketProvider)
    provider.diff_files = ['cached']
    res = bbmod.BitbucketProvider.get_diff_files(provider)
    assert res == ['cached']


def test_encoding_fallback_and_status_mapping_round_003(monkeypatch):
    # Test fallback to other encodings and mapping of statuses to edit_type (lines 235-246 and 330-338)

    # Create 4 diffs with different statuses
    diffs = [
        _make_diff('file_a.py', 'added'),
        _make_diff('file_b.py', 'removed'),
        _make_diff('file_c.py', 'modified'),
        _make_diff('file_d.py', 'renamed'),
    ]

    # pr.diffstat returns the diffs
    def dummy_difffunc(*_, **kwargs):
        encoding = kwargs.get('encoding', None)
        if encoding is None:
            # Simulate initial decode failure
            raise Exception('utf-8 decode error')
        # Build a patch string with 4 diff sections. Each section includes header lines so the code trims header.
        parts = []
        for d in diffs:
            section = (
                "diff --git a/{n} b/{n}\n"
                "new file mode 100644\n"
                "--- a/{n}\n"
                "+++ b/{n}\n"
                "@@ -1,1 +1,1 @@\n"
                "+added line\n"
            ).format(n=d.new.path)
            parts.append(section)
        return "".join(parts)

    pr = SimpleNamespace(diffstat=lambda: list(diffs), diff=dummy_difffunc)

    provider = object.__new__(bbmod.BitbucketProvider)
    provider.diff_files = None
    provider.pr = pr

    # Patch _get_pr_file_content to return deterministic content when called
    monkeypatch.setattr(provider, '_get_pr_file_content', lambda href: f"contents-for-{href}")

    # Ensure filter_ignored returns the same list (no filtering here)
    monkeypatch.setattr(bbmod, 'filter_ignored', lambda x, provider_name: x)

    result = bbmod.BitbucketProvider.get_diff_files(provider)

    # Expect 4 file patch structures with edit_type set according to status mapping
    assert isinstance(result, list)
    assert len(result) == 4
    # Check mapping order: added, removed, modified, renamed
    assert result[0].edit_type == _MockEditType.ADDED
    assert result[1].edit_type == _MockEditType.DELETED
    assert result[2].edit_type == _MockEditType.MODIFIED
    assert result[3].edit_type == _MockEditType.RENAMED
    # Also confirm that payloads store expected path strings
    assert result[0].path == 'file_a.py'
    assert result[3].path == 'file_d.py'


def test_diff_split_filtering_and_filter_ignored_round_003(monkeypatch):
    # This test triggers the branch where filter_ignored shortens diffs and diff_split is filtered accordingly
    # (lines 220-229 and 255-257)

    # Create three original diffs, but filter_ignored will remove one
    d1 = _make_diff('keep1.py', 'modified')
    d2 = _make_diff('remove_me.py', 'modified')
    d3 = _make_diff('keep2.py', 'modified')
    diffs_original = [d1, d2, d3]

    # filter_ignored will return only [d1, d3]
    monkeypatch.setattr(bbmod, 'filter_ignored', lambda orig, prov: [d for d in orig if d is not d2])

    # pr.diff returns 3 diff sections (one per original)
    def diff_func(*args, **kwargs):
        parts = []
        for d in diffs_original:
            parts.append(
                "diff --git a/{n} b/{n}\nnew file mode 100644\n--- a/{n}\n+++ b/{n}\n@@ -1,1 +1,1 @@\n+L\n".format(n=d.new.path)
            )
        return "".join(parts)

    pr = SimpleNamespace(diffstat=lambda: list(diffs_original), diff=diff_func)
    provider = object.__new__(bbmod.BitbucketProvider)
    provider.pr = pr
    provider.diff_files = None

    # Keep is_valid_file True so files are processed
    monkeypatch.setattr(bbmod, 'is_valid_file', lambda p: True)
    # Provide file content retrieval
    monkeypatch.setattr(provider, '_get_pr_file_content', lambda href: 'x')

    result = bbmod.BitbucketProvider.get_diff_files(provider)

    # Because filter_ignored removed one diff, the final result should have 2 entries
    assert isinstance(result, list)
    assert len(result) == 2
    # Their paths should match keep1.py and keep2.py in order
    assert result[0].path == 'keep1.py'
    assert result[1].path == 'keep2.py'


def test_mismatched_diff_split_length_returns_empty_round_003(monkeypatch):
    # If the number of split patches does not match the number of diffs, function should return [] (lines 253-259)
    d1 = _make_diff('a.py', 'modified')
    d2 = _make_diff('b.py', 'modified')
    diffs = [d1, d2]

    # pr.diff returns only 1 diff section, while diffstat returns 2 entries -> mismatch
    def diff_func_single(*args, **kwargs):
        return (
            "diff --git a/x b/x\nnew file mode 100644\n--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n+L\n"
        )

    pr = SimpleNamespace(diffstat=lambda: list(diffs), diff=diff_func_single)
    provider = object.__new__(bbmod.BitbucketProvider)
    provider.pr = pr
    provider.diff_files = None

    # No filtering
    monkeypatch.setattr(bbmod, 'filter_ignored', lambda x, provider_name: x)

    res = bbmod.BitbucketProvider.get_diff_files(provider)
    assert res == []
