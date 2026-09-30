# file: pr_agent/git_providers/gitlab_provider.py:395-477
# asked: {"lines": [405, 406, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 421, 422, 424, 425, 426, 427, 428, 429, 430, 433, 434, 435, 436, 438, 439, 440, 441, 444, 445, 447, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 476, 477], "branches": [[405, 406], [405, 409], [413, 414], [413, 424], [427, 428], [427, 473], [428, 429], [428, 433], [434, 435], [434, 438], [438, 439], [438, 440], [448, 449], [448, 450], [450, 451], [450, 452], [452, 453], [452, 455], [457, 458], [457, 462], [473, 474], [473, 476]]}
# gained: {"lines": [405, 406, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 421, 422, 424, 425, 426, 427, 428, 429, 430, 433, 434, 435, 436, 438, 439, 440, 441, 444, 445, 447, 448, 449, 450, 452, 455, 456, 457, 458, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 476, 477], "branches": [[405, 406], [405, 409], [413, 414], [427, 428], [427, 473], [428, 429], [428, 433], [434, 435], [434, 438], [438, 439], [448, 449], [448, 450], [450, 452], [452, 455], [457, 458], [457, 462], [473, 474], [473, 476]]}

import pytest

import pr_agent.git_providers.gitlab_provider as gl_mod
from pr_agent.git_providers.gitlab_provider import GitLabProvider
from pr_agent.algo.types import FilePatchInfo


def make_mr_stub(changes_list, base_sha="BASE", head_sha="HEAD"):
    class MR:
        def __init__(self, changes_list):
            self._changes = changes_list
            self.diff_refs = {'base_sha': base_sha, 'head_sha': head_sha}

        def changes(self):
            return {'changes': list(self._changes)}
    return MR(changes_list)


def make_logger_stub(calls_list, raise_on_extra=False):
    class Logger:
        def info(self, msg, extra=None):
            calls_list.append((msg, extra))
            if raise_on_extra and extra is not None:
                raise RuntimeError("logger forced error")
    return Logger()


def make_provider_instance():
    # Create instance without running __init__
    prov = object.__new__(GitLabProvider)
    # set some default attributes used by get_diff_files
    prov.diff_files = None
    prov.id_mr = 123
    return prov


def test_get_diff_files_early_return():
    prov = make_provider_instance()
    cached = [FilePatchInfo("o", "n", patch="p", filename="f")]
    prov.diff_files = cached
    res = prov.get_diff_files()
    assert res is cached
    assert prov.diff_files is cached


def test_get_diff_files_main_flow_info_ok(monkeypatch):
    # Prepare diffs: we'll have five raw changes; filter_ignored will remove one of them
    raw_changes = [
        # will be kept - modified with diff
        {'old_path': 'a.txt', 'new_path': 'a.txt', 'diff': '+line1\n-line2\n', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
        # will be kept - second file, non-empty diff; this will trigger "Too many files..." for counter == MAX
        {'old_path': 'b.py', 'new_path': 'b.py', 'diff': '+added\n', 'new_file': True, 'deleted_file': False, 'renamed_file': False},
        # will be kept - empty diff (force load_large_diff)
        {'old_path': 'c.md', 'new_path': 'c.md', 'diff': '', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
        # will be kept - invalid extension (is_valid_file should return False)
        {'old_path': 'e.invalid', 'new_path': 'e.invalid', 'diff': '-removed\n', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
        # will be filtered out by filter_ignored
        {'old_path': 'ignored.txt', 'new_path': 'ignored.txt', 'diff': '+x\n', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
    ]
    # filtered list will remove the last one
    filtered = raw_changes[:-1]

    # Setup provider
    prov = make_provider_instance()
    prov.mr = make_mr_stub(raw_changes)
    prov.get_pr_file_content = lambda path, sha: (b'OLD:' + path.encode()) if sha == prov.mr.diff_refs['base_sha'] else (b'NEW:' + path.encode())

    # monkeypatch helpers used in module
    calls = []
    monkeypatch.setattr(gl_mod, 'filter_ignored', lambda diffs, src='gitlab': filtered)

    # decode_if_bytes should decode bytes to string
    monkeypatch.setattr(gl_mod, 'decode_if_bytes', lambda v: v.decode() if isinstance(v, (bytes, bytearray)) else v)

    # Track load_large_diff calls
    load_calls = []
    monkeypatch.setattr(gl_mod, 'load_large_diff', lambda filename, new, old: load_calls.append((filename, new, old)) or ("+++generated\n+new\n-old\n"))

    # is_valid_file: mark only .invalid as invalid
    monkeypatch.setattr(gl_mod, 'is_valid_file', lambda name: not name.endswith('.invalid'))

    # Replace _expand_submodule_changes to identity
    monkeypatch.setattr(GitLabProvider, '_expand_submodule_changes', lambda self, changes: changes)

    # Logger stub
    logger = make_logger_stub(calls, raise_on_extra=False)
    monkeypatch.setattr(gl_mod, 'get_logger', lambda: logger)

    # Set MAX_FILES_ALLOWED_FULL low to trigger the "Too many files..." branch
    monkeypatch.setattr(gl_mod, 'MAX_FILES_ALLOWED_FULL', 2)

    res = GitLabProvider.get_diff_files(prov)

    # Results: filtered had 4 kept entries, one is invalid -> 3 valid FilePatchInfo expected
    assert isinstance(res, list)
    assert len(res) == 3

    # Verify filenames and edit types
    filenames = [fp.filename for fp in res]
    assert 'a.txt' in filenames
    assert 'b.py' in filenames
    assert 'c.md' in filenames
    # Verify that for b.py (new_file True) edit_type is ADDED
    for fp in res:
        if fp.filename == 'b.py':
            from pr_agent.algo.types import EDIT_TYPE
            assert fp.edit_type == EDIT_TYPE.ADDED
        if fp.filename == 'a.txt':
            from pr_agent.algo.types import EDIT_TYPE
            assert fp.edit_type == EDIT_TYPE.MODIFIED

    # Ensure load_large_diff was called at least once (for c.md where diff was empty)
    assert any(call[0] == 'c.md' for call in load_calls)

    # Ensure logger calls include 'Too many files' message and filtered out invalid extensions message
    logged_msgs = [m for m, extra in calls]
    assert any('Too many files' in str(m) for m in logged_msgs)
    assert any('Filtered out files with invalid extensions' in str(m) for m in logged_msgs)
    # Ensure filter_ignored logging was called (first info with extra dict)
    assert any(extra is not None for _, extra in calls)


def test_get_diff_files_filter_info_raises_does_not_crash(monkeypatch):
    # Similar setup but force get_logger().info to raise when called with extra (the filter logging)
    raw_changes = [
        {'old_path': 'a.txt', 'new_path': 'a.txt', 'diff': '+L\n', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
        {'old_path': 'b.py', 'new_path': 'b.py', 'diff': '+M\n', 'new_file': False, 'deleted_file': False, 'renamed_file': False},
    ]
    filtered = list(raw_changes)  # same, but will still attempt to call logger.info in the filtering block only if module's filter_ignored returns different list; to force the try/except, we make it return a different list
    # Make original have an extra element so filter_ignored returns filtered != original
    original_raw = list(raw_changes) + [{'old_path': 'x', 'new_path': 'x', 'diff': '', 'new_file': False, 'deleted_file': False, 'renamed_file': False}]

    prov = make_provider_instance()
    prov.mr = make_mr_stub(original_raw)
    prov.get_pr_file_content = lambda path, sha: b''

    monkeypatch.setattr(gl_mod, 'filter_ignored', lambda diffs, src='gitlab': filtered)
    monkeypatch.setattr(GitLabProvider, '_expand_submodule_changes', lambda self, changes: changes)
    monkeypatch.setattr(gl_mod, 'decode_if_bytes', lambda v: v)
    monkeypatch.setattr(gl_mod, 'load_large_diff', lambda filename, new, old: "+++g\n+1\n-1\n")
    monkeypatch.setattr(gl_mod, 'is_valid_file', lambda name: True)

    # Logger that raises when extra is provided to simulate exception inside the try block
    calls = []
    logger = make_logger_stub(calls, raise_on_extra=True)
    monkeypatch.setattr(gl_mod, 'get_logger', lambda: logger)

    # Ensure MAX_FILES_ALLOWED_FULL large so no "Too many files" log is triggered
    monkeypatch.setattr(gl_mod, 'MAX_FILES_ALLOWED_FULL', 100)

    # Should not raise despite logger.info raising in the filter logging; test will fail if exception propagates
    res = GitLabProvider.get_diff_files(prov)
    assert isinstance(res, list)
    # we expected two files processed
    assert len(res) == 2
    # verify that even though logger.info raised, other logging calls might exist; ensure we captured the attempted call
    assert any(isinstance(x, tuple) for x in calls)
