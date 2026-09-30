import types
import pytest

from pr_agent.algo import pr_processing
from pr_agent.algo.pr_processing import get_pr_diff
from pr_agent.algo.types import EDIT_TYPE
from github import RateLimitExceededException


class DummyTokenHandler:
    def __init__(self):
        pass

    def count_tokens(self, s: str) -> int:
        # deterministic simple token count: number of whitespace-separated words or 0 for empty
        if not s:
            return 0
        return len(str(s).split())


class DummyGitProviderBase:
    def __init__(self, diff_files=None, languages=None):
        self._diff_files = diff_files if diff_files is not None else ["f1"]
        self._languages = languages if languages is not None else [{"language": "Python"}]

    def get_diff_files(self):
        return self._diff_files

    def get_languages(self):
        return self._languages


def make_logger_recorder():
    calls = {"info": [], "error": [], "debug": []}

    class Logger:
        def info(self, msg):
            calls["info"].append(msg)

        def error(self, msg):
            calls["error"].append(msg)

        def debug(self, msg):
            calls["debug"].append(msg)

    return Logger(), calls


def test_get_pr_diff_disable_extra_lines_returns_full_diff_round_016(monkeypatch):
    """
    - disable_extra_lines True should set extra lines to zero path
    - small total_tokens should take the early-return path and return the full extended diff
    """
    # Arrange
    git_provider = DummyGitProviderBase(diff_files=["file1.py"], languages=[{"language": "Python"}])
    token_handler = DummyTokenHandler()
    model = "any-model"

    # Ensure pr_generate_extended_diff returns a small total_tokens so function returns full diff
    def fake_pr_generate_extended_diff(pr_languages, token_handler_arg, add_ln, patch_extra_lines_before=None, patch_extra_lines_after=None):
        return (["+++ patch A", "--- patch B"], 1, None)

    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff", fake_pr_generate_extended_diff)
    # Stub sort_files_by_main_languages to avoid calling real language handler
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])
    # Make get_max_tokens large enough
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda m: 1000)
    # Ensure soft threshold doesn't interfere with the inequality
    monkeypatch.setattr(pr_processing, "OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD", 0)
    # Logger no-op
    logger, calls = make_logger_recorder()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    # Act
    out = get_pr_diff(git_provider, token_handler, model, add_line_numbers_to_hunks=False, disable_extra_lines=True, large_pr_handling=False, return_remaining_files=False)

    # Assert
    assert isinstance(out, str) and "+++ patch A" in out and "--- patch B" in out
    # logger data structure should exist and be a dict
    assert isinstance(calls, dict)


def test_get_pr_diff_pruning_builds_added_modified_deleted_and_returns_remaining_round_016(monkeypatch):
    """
    - Simulate a large PR that triggers pruning
    - Ensure file_dict entries with ADDED, MODIFIED/RENAMED, and DELETED are processed and appended to final diff
    - Ensure return_remaining_files True returns (final_diff, remaining_files_list)
    """
    # Arrange
    git_provider = DummyGitProviderBase(diff_files=["file1.py"], languages=[{"language": "Python"}])
    token_handler = DummyTokenHandler()
    model = "any-model"

    # make settings.config.* values used when disable_extra_lines is False
    class Cfg:
        def __init__(self):
            self.patch_extra_lines_before = 2
            self.patch_extra_lines_after = 3

    class Settings:
        def __init__(self):
            self.config = Cfg()

    monkeypatch.setattr(pr_processing, "get_settings", lambda: Settings())
    monkeypatch.setattr(pr_processing, "cap_and_log_extra_lines", lambda v, d: v)

    # Stub sort_files_by_main_languages to avoid real language handler expectations
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])

    # Force extended diff to be large so total_tokens triggers pruning
    def fake_pr_generate_extended_diff(pr_languages, token_handler_arg, add_ln, patch_extra_lines_before=None, patch_extra_lines_after=None):
        return (["ext_patch_line1"], 10000, None)

    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff", fake_pr_generate_extended_diff)

    # Provide compressed diff results used in pruning
    patches_compressed_list = [["comp_patch_line1"]]
    total_tokens_list = [20]
    deleted_files_list = []
    remaining_files_list = ["remaining1.txt"]
    # files_in_patches_list contains filenames present in patch (none of our file_dict keys) so loop processes them
    files_in_patches_list = [["not_in_dict.txt"]]

    file_dict = {
        "a_added.py": {"edit_type": EDIT_TYPE.ADDED},
        "b_modified.py": {"edit_type": EDIT_TYPE.MODIFIED},
        "c_renamed.py": {"edit_type": EDIT_TYPE.RENAMED},
        "d_deleted.py": {"edit_type": EDIT_TYPE.DELETED},
    }

    def fake_pr_generate_compressed_diff(pr_languages, token_handler_arg, model_arg, add_ln, large_pr_handling_arg):
        return (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list)

    monkeypatch.setattr(pr_processing, "pr_generate_compressed_diff", fake_pr_generate_compressed_diff)

    # Clip tokens returns the input unchanged for deterministic behavior
    monkeypatch.setattr(pr_processing, "clip_tokens", lambda s, max_t: s)

    # Control get_max_tokens so max_tokens - curr_token is comfortably > delta_tokens
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda m: 1000)
    # Ensure soft threshold does not change logic here
    monkeypatch.setattr(pr_processing, "OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD", 0)

    # Ensure the ADDED/MORE_MODIFIED/DELETED markers exist and are deterministic
    monkeypatch.setattr(pr_processing, "ADDED_FILES_", "ADDED_FILES_")
    monkeypatch.setattr(pr_processing, "MORE_MODIFIED_FILES_", "MORE_MODIFIED_FILES_")
    monkeypatch.setattr(pr_processing, "DELETED_FILES_", "DELETED_FILES_")

    # Logger no-op
    logger, calls = make_logger_recorder()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    # Act
    final, remaining = get_pr_diff(git_provider, token_handler, model, add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=False, return_remaining_files=True)

    # Assert: final is string and contains compressed patch and added/modified/deleted headers
    assert isinstance(final, str)
    assert "comp_patch_line1" in final
    assert "ADDED_FILES_" in final
    assert "MORE_MODIFIED_FILES_" in final
    assert "DELETED_FILES_" in final
    # remaining should be the remaining_files_list we provided
    assert remaining == remaining_files_list


def test_get_pr_diff_rate_limit_exception_propagates_round_016(monkeypatch):
    """
    If the git provider raises RateLimitExceededException when fetching diff files, the exception should propagate
    """
    class BrokenGitProvider:
        def get_diff_files(self):
            # PyGithub's RateLimitExceededException (subclass of GithubException) expects (status, data, headers)
            raise RateLimitExceededException(429, "limit hit", {})

        def get_languages(self):
            return []

    git_provider = BrokenGitProvider()
    token_handler = DummyTokenHandler()
    model = "any-model"

    # No other monkeypatching needed for this path
    with pytest.raises(RateLimitExceededException):
        get_pr_diff(git_provider, token_handler, model, add_line_numbers_to_hunks=False, disable_extra_lines=True, large_pr_handling=False, return_remaining_files=False)
