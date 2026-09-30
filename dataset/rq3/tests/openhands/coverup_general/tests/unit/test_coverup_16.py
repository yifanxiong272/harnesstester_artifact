# file: openhands/runtime/utils/git_changes.py:72-160
# asked: {"lines": [75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 93, 94, 95, 97, 100, 102, 103, 104, 105, 106, 107, 110, 111, 112, 113, 116, 119, 121, 122, 123, 124, 125, 128, 131, 132, 134, 136, 137, 138, 139, 142, 143, 144, 145, 146, 150, 153, 154, 155, 156, 157, 158, 160], "branches": [[76, 77], [76, 80], [84, 85], [84, 153], [85, 86], [85, 93], [94, 95], [94, 97], [100, 102], [100, 119], [119, 121], [119, 131], [131, 132], [131, 134], [136, 137], [136, 138], [138, 139], [138, 142], [142, 143], [142, 150], [156, 157], [156, 160], [157, 156], [157, 158]]}
# gained: {"lines": [75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 93, 94, 95, 97, 100, 102, 103, 104, 105, 106, 107, 110, 111, 112, 113, 116, 119, 121, 122, 123, 124, 125, 128, 131, 132, 136, 137, 138, 139, 142, 143, 144, 145, 146, 150, 153, 154, 155, 156, 157, 158, 160], "branches": [[76, 77], [76, 80], [84, 85], [84, 153], [85, 86], [85, 93], [94, 95], [94, 97], [100, 102], [100, 119], [119, 121], [119, 131], [131, 132], [136, 137], [136, 138], [138, 139], [138, 142], [142, 143], [142, 150], [156, 157], [156, 160], [157, 156], [157, 158]]}

import pytest
from types import SimpleNamespace

import openhands.runtime.utils.git_changes as git_changes


def _make_run(diff_output: str, ls_output: str):
    def run(cmd: str, repo_dir: str):
        if 'git --no-pager diff --name-status' in cmd:
            return diff_output
        if 'git --no-pager ls-files --others --exclude-standard' in cmd:
            return ls_output
        raise AssertionError(f"Unexpected command passed to run: {cmd!r}")
    return run


def test_no_ref_returns_empty(monkeypatch):
    # get_valid_ref falsy -> should return empty list and not call run
    monkeypatch.setattr(git_changes, 'get_valid_ref', lambda repo_dir: '')
    # Provide a run that would fail if called, to ensure it's not used
    def bad_run(cmd, repo_dir):
        raise AssertionError("run should not be called when no ref is returned")
    monkeypatch.setattr(git_changes, 'run', bad_run)

    res = git_changes.get_changes_in_repo('some/repo')
    assert res == []


def test_blank_line_in_diff_raises(monkeypatch):
    # diff contains a blank/whitespace-only line -> RuntimeError
    monkeypatch.setattr(git_changes, 'get_valid_ref', lambda repo_dir: 'origin/main')
    monkeypatch.setattr(git_changes, 'run', _make_run("   \n", ""))

    with pytest.raises(RuntimeError) as exc:
        git_changes.get_changes_in_repo('repo')
    assert 'unexpected_value_in_git_diff' in str(exc.value)


def test_too_few_parts_in_diff_raises(monkeypatch):
    # diff line splits into less than 2 parts -> RuntimeError
    monkeypatch.setattr(git_changes, 'get_valid_ref', lambda repo_dir: 'origin/main')
    monkeypatch.setattr(git_changes, 'run', _make_run("SINGLETOKEN\n", ""))

    with pytest.raises(RuntimeError) as exc:
        git_changes.get_changes_in_repo('repo')
    assert 'unexpected_value_in_git_diff' in str(exc.value)


def test_unexpected_status_in_diff_raises(monkeypatch):
    # diff line with 2 parts but invalid status -> RuntimeError about unexpected_status_in_git_diff
    monkeypatch.setattr(git_changes, 'get_valid_ref', lambda repo_dir: 'origin/main')
    monkeypatch.setattr(git_changes, 'run', _make_run("Z file.txt\n", ""))

    with pytest.raises(RuntimeError) as exc:
        git_changes.get_changes_in_repo('repo')
    assert 'unexpected_status_in_git_diff' in str(exc.value)


def test_get_changes_handles_rename_copy_regular_and_untracked(monkeypatch):
    # Compose a diff output that covers:
    # - Rename: R100 old.txt new.txt -> produces D old.txt and A new.txt
    # - Copy: C100 orig.txt copied.txt -> produces A copied.txt
    # - Regular modify: M mod.txt -> produces M mod.txt
    # - Unusual statuses mapped: '??' -> A, '*' -> M
    diff_lines = [
        "R100 old.txt new.txt",
        "C100 orig.txt copied.txt",
        "M mod.txt",
        "?? untracked_from_diff.txt",
        "* starred.txt",
    ]
    diff_output = "\n".join(diff_lines) + "\n"
    # ls-files returns two untracked files, one empty line in between should be ignored
    ls_output = "u1.txt\n\nu2.txt\n"

    monkeypatch.setattr(git_changes, 'get_valid_ref', lambda repo_dir: 'origin/main')
    monkeypatch.setattr(git_changes, 'run', _make_run(diff_output, ls_output))

    changes = git_changes.get_changes_in_repo('repo')

    # Expected order:
    # From diff:
    #  - D old.txt
    #  - A new.txt
    #  - A copied.txt
    #  - M mod.txt
    #  - A untracked_from_diff.txt  (converted from '??')
    #  - M starred.txt            (converted from '*')
    # From ls-files (untracked):
    #  - A u1.txt
    #  - A u2.txt
    expected = [
        {'status': 'D', 'path': 'old.txt'},
        {'status': 'A', 'path': 'new.txt'},
        {'status': 'A', 'path': 'copied.txt'},
        {'status': 'M', 'path': 'mod.txt'},
        {'status': 'A', 'path': 'untracked_from_diff.txt'},
        {'status': 'M', 'path': 'starred.txt'},
        {'status': 'A', 'path': 'u1.txt'},
        {'status': 'A', 'path': 'u2.txt'},
    ]

    assert changes == expected
