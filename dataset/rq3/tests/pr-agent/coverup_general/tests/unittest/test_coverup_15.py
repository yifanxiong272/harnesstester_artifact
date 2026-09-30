# file: pr_agent/algo/file_filter.py:8-81
# asked: {"lines": [17, 20, 30, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 61, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 78, 79], "branches": [[16, 17], [19, 20], [29, 30], [42, 81], [46, 48], [49, 50], [49, 58], [50, 51], [50, 54], [51, 52], [51, 54], [54, 49], [54, 55], [55, 49], [55, 56], [59, 61], [61, 63], [61, 72], [64, 65], [64, 71], [65, 66], [65, 68], [68, 64], [68, 69], [72, 73], [72, 74], [74, 43], [74, 75]]}
# gained: {"lines": [17, 20, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 61, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 78, 79], "branches": [[16, 17], [19, 20], [46, 48], [49, 50], [49, 58], [50, 51], [51, 52], [51, 54], [54, 55], [55, 49], [55, 56], [59, 61], [61, 63], [61, 72], [64, 65], [64, 71], [65, 66], [65, 68], [68, 64], [68, 69], [72, 73], [72, 74], [74, 75]]}

import re
from types import SimpleNamespace

import pytest

import pr_agent.algo.file_filter as file_filter


def make_settings(ignore_regex=None, ignore_glob=None, config=None, generated_code=None):
    # Helper to create a settings object with nested attributes expected by filter_ignored
    ignore = SimpleNamespace(regex=ignore_regex, glob=ignore_glob)
    config = {} if config is None else config
    generated_code = {} if generated_code is None else generated_code
    return SimpleNamespace(ignore=ignore, config=config, generated_code=generated_code)


class _Logger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        self.warnings.append(msg)


class DummyNewOld:
    def __init__(self, new_path=None, old_path=None):
        class Sub:
            def __init__(self, path):
                self.path = path

        self.new = Sub(new_path) if new_path is not None else None
        self.old = Sub(old_path) if old_path is not None else None


def test_filter_ignored_github_with_string_and_glob_and_code_generator_string(monkeypatch):
    """
    Tests:
    - get_settings().ignore.regex as a string (lines 16-17)
    - get_settings().ignore.glob as a string which must be stripped and split (lines 19-20)
    - get_settings().config.ignore_language_framework as a string triggers a warning (lines 24-27)
    - generated_code entry as a string (lines 29-30)
    - translate_globs_to_regexes is used to add patterns
    - invalid regex is ignored at compile time
    - github branch filtering (lines 42-46)
    """
    # Prepare settings: regex is invalid so it will be skipped; but we also include valid patterns from translate_globs_to_regexes
    settings = make_settings(ignore_regex="(?", ignore_glob="[.*utils.py]", config={'ignore_language_framework': 'somegen'}, generated_code={'somegen': '*.gen.py'})
    monkeypatch.setattr(file_filter, "get_settings", lambda: settings)

    logger = _Logger()
    monkeypatch.setattr(file_filter, "get_logger", lambda: logger)

    # translate_globs_to_regexes should be called for both glob and generated globs; return patterns that match specific filenames
    def fake_translate(globs):
        # verify that we receive list input for both calls
        assert isinstance(globs, list)
        # return regexes that will match filenames ending with utils.py or gen.py
        return [r".*utils\.py$", r".*gen\.py$"]

    monkeypatch.setattr(file_filter, "translate_globs_to_regexes", fake_translate)

    # Prepare files: one to keep, two to be filtered by the patterns
    class F:
        def __init__(self, filename):
            self.filename = filename

    files = [F("keep.py"), F("something.utils.py"), F("something.gen.py")]

    out = file_filter.filter_ignored(files, platform="github")

    # only keep.py should remain (others matched glob-derived regexes)
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0].filename == "keep.py"

    # ensure warning was emitted because ignore_language_framework was a string
    assert logger.warnings, "Expected a warning when ignore_language_framework is a string"
    assert "'ignore_language_framework' should be a list" in logger.warnings[0]


def test_filter_ignored_bitbucket_new_old_paths(monkeypatch):
    """
    Tests bitbucket branch where files have .new and .old attributes (lines 48-58).
    Ensures items are filtered based on new.path and old.path.
    """
    settings = make_settings(ignore_regex=[r".*match.*"], ignore_glob=[])
    monkeypatch.setattr(file_filter, "get_settings", lambda: settings)
    monkeypatch.setattr(file_filter, "translate_globs_to_regexes", lambda g: [])

    # Files: some with new paths, some with old paths; those matching 'match' should be removed
    f1 = DummyNewOld(new_path="new_match.txt")  # should be filtered out
    f2 = DummyNewOld(new_path="new_keep.txt")   # should be kept
    f3 = DummyNewOld(old_path="old_keep.txt")   # should be kept
    f4 = DummyNewOld(old_path="old_match.txt")  # should be filtered out

    files = [f1, f2, f3, f4]

    out = file_filter.filter_ignored(files, platform="bitbucket")
    # Only f2 and f3 should remain
    assert out == [f2, f3]


def test_filter_ignored_gitlab_azure_gitea_bitbucket_server(monkeypatch):
    """
    Tests multiple platform-specific branches:
    - bitbucket_server (line 59)
    - gitlab (lines 63-71)
    - azure (lines 72-73)
    - gitea (lines 74-75)
    """
    # We'll run the filter multiple times with different settings and inputs
    # Common settings: regex filters anything containing 'remove'
    settings = make_settings(ignore_regex=[r".*remove.*"], ignore_glob=[])
    monkeypatch.setattr(file_filter, "get_settings", lambda: settings)
    monkeypatch.setattr(file_filter, "translate_globs_to_regexes", lambda g: [])

    # bitbucket_server: list of dicts with path.toString
    files_bs = [
        {'path': {'toString': 'keep.txt'}},
        {'path': {'toString': 'remove_me.txt'}},
        {'path': {}}  # missing toString should be filtered out by condition (f.get('path', {}).get('toString') is falsy)
    ]
    out_bs = file_filter.filter_ignored(list(files_bs), platform="bitbucket_server")
    # Only the one with 'keep.txt' should remain
    assert out_bs == [{'path': {'toString': 'keep.txt'}}]

    # gitlab: list of dicts with new_path/old_path keys
    files_gl = [
        {'new_path': 'keep.py'},
        {'new_path': 'remove_me.py'},
        {'old_path': 'old_keep.py'},
        {'old_path': 'old_remove_me.py'},
        {'some_other_key': 'value'},  # should be removed
    ]
    out_gl = file_filter.filter_ignored(list(files_gl), platform="gitlab")
    # Should keep entries where new_path or old_path exists and does not match 'remove'
    expected_gl = [{'new_path': 'keep.py'}, {'old_path': 'old_keep.py'}]
    assert out_gl == expected_gl

    # azure: files are strings; regex matches 'remove' so filter those out
    files_az = ["keep.txt", "remove_me.txt"]
    out_az = file_filter.filter_ignored(list(files_az), platform="azure")
    assert out_az == ["keep.txt"]

    # gitea: files are dicts with 'filename'
    files_gt = [{'filename': 'keep.txt'}, {'filename': 'remove_me.txt'}, {}]
    out_gt = file_filter.filter_ignored(list(files_gt), platform="gitea")
    # The function keeps items where filename missing (treated as "") or doesn't match the regex.
    # So we expect the keep entry and the empty dict to remain.
    assert out_gt == [{'filename': 'keep.txt'}, {}]


def test_filter_ignored_exception_is_caught_and_printed(monkeypatch, capsys):
    """
    Forces get_settings to raise an exception so the except branch is executed (lines 78-79).
    Verifies that the printed message contains the exception message.
    """
    def raising_get_settings():
        raise RuntimeError("boom")

    monkeypatch.setattr(file_filter, "get_settings", raising_get_settings)

    # Call with some files; should not raise but print the error message
    res = file_filter.filter_ignored(["a.py"], platform="github")
    assert res == ["a.py"]  # original input should be returned unchanged because exception prevented filtering

    captured = capsys.readouterr()
    assert "Could not filter file list: boom" in captured.out
