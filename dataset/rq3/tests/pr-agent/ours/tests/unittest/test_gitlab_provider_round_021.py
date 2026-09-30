import types
import builtins

import pr_agent.git_providers.gitlab_provider as glmod
from pr_agent.algo.types import EDIT_TYPE, FilePatchInfo


class _StubLogger:
    def __init__(self, info_side_effect=None):
        self.info_calls = []
        self._side_effect = info_side_effect

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))
        if self._side_effect:
            raise self._side_effect


class FakeMR:
    def __init__(self, raw_changes, diff_refs=None):
        self._raw_changes = raw_changes
        self.diff_refs = diff_refs or {'base_sha': 'base', 'head_sha': 'head'}

    def changes(self):
        # mimic the real API shape
        return {'changes': self._raw_changes}


class FakeSelf:
    def __init__(self, raw_changes, id_mr='1'):
        self.diff_files = None
        self.id_mr = id_mr
        self.mr = FakeMR(raw_changes)
        # allow overriding behaviors from tests
        self._get_pr_file_content_map = {}

    def _expand_submodule_changes(self, changes):
        # identity by default (tests may patch glmod._expand_submodule_changes if needed)
        return changes

    def get_pr_file_content(self, file_path, branch):
        # return configured values when available, otherwise a deterministic byte string
        return self._get_pr_file_content_map.get((file_path, branch), b'default-old')


def test_cached_diff_files_round_021():
    """If self.diff_files is already set, function should return it immediately without calling MR changes."""
    fake = FakeSelf([])
    fake.diff_files = ['already_cached']

    # replace MR changes with a function that would raise if called, to ensure it's not executed
    def bad_changes():
        raise AssertionError("mr.changes should not be called when diff_files is cached")

    fake.mr.changes = bad_changes

    result = glmod.GitLabProvider.get_diff_files(fake)
    assert result == ['already_cached']


def test_mixed_edit_types_round_021():
    """Covers normal path where multiple diffs are processed and edit_type resolves to ADDED/DELETED/RENAMED/MODIFIED."""
    # ensure no filtering occurs
    glmod.filter_ignored = lambda diffs, source: diffs
    glmod.is_valid_file = lambda p: True

    # make file limit large so we always load full content path
    glmod.MAX_FILES_ALLOWED_FULL = 10

    # provide three diffs with different flags and patch content
    raw_changes = [
        {
            'old_path': 'file_a.txt',
            'new_path': 'file_a.txt',
            'diff': '+added_line\n-removed_line\n',
            'new_file': True,
            'deleted_file': False,
            'renamed_file': False,
        },
        {
            'old_path': 'file_b.txt',
            'new_path': 'file_b.txt',
            'diff': '+only_plus\n',
            'new_file': False,
            'deleted_file': True,
            'renamed_file': False,
        },
        {
            'old_path': 'old_name_c.txt',
            'new_path': 'new_name_c.txt',
            'diff': '-only_minus\n',
            'new_file': False,
            'deleted_file': False,
            'renamed_file': True,
        },
    ]

    fake = FakeSelf(raw_changes)
    # make get_pr_file_content return bytes to exercise decode_if_bytes path
    fake._get_pr_file_content_map[('file_a.txt', 'base')] = b'orig-a'
    fake._get_pr_file_content_map[('file_a.txt', 'head')] = b'new-a'
    fake._get_pr_file_content_map[('file_b.txt', 'base')] = b'orig-b'
    fake._get_pr_file_content_map[('file_b.txt', 'head')] = b'new-b'
    fake._get_pr_file_content_map[('new_name_c.txt', 'base')] = b'orig-c'
    fake._get_pr_file_content_map[('new_name_c.txt', 'head')] = b'new-c'

    result = glmod.GitLabProvider.get_diff_files(fake)

    # Expect three FilePatchInfo items returned in the same order
    assert isinstance(result, list)
    assert len(result) == 3

    # first: new file -> EDIT_TYPE.ADDED
    f0 = result[0]
    assert isinstance(f0, FilePatchInfo)
    assert f0.filename == 'file_a.txt'
    assert f0.edit_type == EDIT_TYPE.ADDED
    # one plus and one minus line from the diff
    assert f0.num_plus_lines == 1
    assert f0.num_minus_lines == 1

    # second: deleted file -> EDIT_TYPE.DELETED
    f1 = result[1]
    assert f1.filename == 'file_b.txt'
    assert f1.edit_type == EDIT_TYPE.DELETED
    assert f1.num_plus_lines == 1
    assert f1.num_minus_lines == 0

    # third: renamed -> EDIT_TYPE.RENAMED and old_filename must be set
    f2 = result[2]
    assert f2.filename == 'new_name_c.txt'
    assert f2.edit_type == EDIT_TYPE.RENAMED
    assert f2.old_filename == 'old_name_c.txt'
    assert f2.num_plus_lines == 0
    assert f2.num_minus_lines == 1


def test_large_files_and_filter_exception_round_021():
    """Covers branch where filter_ignored changes the list and logger.info raises (triggering except),
    and the MAX_FILES_ALLOWED_FULL limit causes content bypass and load_large_diff to be used for a diff with empty patch."""
    # Original raw changes contains two entries, but filter_ignored will return a smaller list
    raw_changes = [
        {'old_path': 'skip_me.txt', 'new_path_missing': 'oops'},
        {'old_path': 'bigfile.txt', 'new_path': 'bigfile.txt', 'diff': '' , 'new_file': False, 'deleted_file': False, 'renamed_file': False},
    ]

    # make filter_ignored return only the second entry, ensuring diffs != diffs_original
    glmod.filter_ignored = lambda diffs, source: [diffs[1]]

    # Monkeypatch logger so info raises when called in the try block (to exercise except path)
    stub_logger = _StubLogger(info_side_effect=RuntimeError("logger failure"))
    glmod.get_logger = lambda: stub_logger

    # set MAX_FILES_ALLOWED_FULL small so the function will hit the 'Too many files' branch
    glmod.MAX_FILES_ALLOWED_FULL = 1

    # record if load_large_diff was called
    called = {'load_large_diff': False}

    def fake_load_large_diff(filename, new_content, old_content):
        called['load_large_diff'] = True
        # return a patch that has one plus and one minus
        return '+from_big\n-from_big_old\n'

    glmod.load_large_diff = fake_load_large_diff

    # assume file is valid
    glmod.is_valid_file = lambda p: True

    fake = FakeSelf(raw_changes)
    # ensure get_pr_file_content returns bytes so decode_if_bytes path is exercised
    fake._get_pr_file_content_map[('bigfile.txt', 'base')] = b'old-big'
    fake._get_pr_file_content_map[('bigfile.txt', 'head')] = b'new-big'

    result = glmod.GitLabProvider.get_diff_files(fake)

    # load_large_diff must have been called because the diff was empty
    assert called['load_large_diff'] is True

    # Ensure we got one FilePatchInfo and its counts match fake_load_large_diff
    assert isinstance(result, list)
    assert len(result) == 1
    info = result[0]
    assert info.filename == 'bigfile.txt'
    assert info.num_plus_lines == 1
    assert info.num_minus_lines == 1

    # Ensure that the logger.info inside the try was attempted (it should have been called once and raised)
    # The stub captured the attempted calls before raising
    assert len(stub_logger.info_calls) >= 1
