# file: pr_agent/algo/pr_processing.py:38-142
# asked: {"lines": [45, 46, 55, 56, 57, 64, 65, 79, 81, 82, 84, 85, 86, 89, 90, 91, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 116, 117, 119, 120, 122, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 142], "branches": [[44, 45], [61, 68], [73, 79], [84, 85], [84, 89], [101, 102], [101, 125], [102, 103], [102, 125], [103, 104], [103, 105], [105, 106], [105, 111], [107, 108], [107, 110], [111, 112], [111, 117], [113, 114], [113, 116], [117, 102], [117, 119], [119, 120], [119, 122], [126, 127], [126, 129], [130, 131], [130, 133], [134, 135], [134, 137], [139, 140], [139, 142]]}
# gained: {"lines": [45, 46, 55, 56, 57, 79, 81, 82, 84, 89, 90, 91, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 111, 112, 113, 114, 117, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 142], "branches": [[44, 45], [73, 79], [84, 89], [101, 102], [102, 103], [102, 125], [103, 104], [103, 105], [105, 106], [105, 111], [107, 108], [111, 112], [111, 117], [113, 114], [117, 119], [119, 120], [126, 127], [130, 131], [134, 135], [139, 140], [139, 142]]}

import pytest

import pr_agent.algo.pr_processing as pr_processing


class DummyGitProvider:
    def __init__(self, diff_files=None, languages=None, raise_on_diff=False):
        self._diff_files = diff_files or []
        self._languages = languages or []
        self._raise_on_diff = raise_on_diff

    def get_diff_files(self):
        if self._raise_on_diff:
            raise pr_processing.RateLimitExceededException("rate limit hit")
        return self._diff_files

    def get_languages(self):
        return self._languages


class DummyTokenHandler:
    def __init__(self, base=1):
        self.base = base

    def count_tokens(self, text: str):
        # simple deterministic token count: number of words + base
        if not text:
            return 0
        return len(text.split()) + self.base


class DummyLogger:
    def __init__(self, info_side_effect=None, record=None):
        self.info_side_effect = info_side_effect
        self.record = record if record is not None else {"info": [], "error": [], "debug": []}

    def info(self, msg):
        self.record["info"].append(msg)
        if self.info_side_effect:
            raise self.info_side_effect

    def error(self, msg):
        self.record["error"].append(msg)

    def debug(self, msg):
        self.record["debug"].append(msg)


def make_settings_obj(before=3, after=4):
    class Cfg:
        pass

    class S:
        config = Cfg()

    S.config.patch_extra_lines_before = before
    S.config.patch_extra_lines_after = after
    return S


def test_rate_limit_exception_propagates_and_logs(monkeypatch):
    # Replace the RateLimitExceededException with a simple Exception subclass to avoid GitHub dependency
    class SimpleRateLimitError(Exception):
        pass

    monkeypatch.setattr(pr_processing, "RateLimitExceededException", SimpleRateLimitError)

    # Setup git provider that raises RateLimitExceededException
    gp = DummyGitProvider(raise_on_diff=True)
    th = DummyTokenHandler()

    # capture logger calls
    record = {"info": [], "error": [], "debug": []}
    dummy_logger = DummyLogger(record=record)
    monkeypatch.setattr(pr_processing, "get_logger", lambda: dummy_logger)

    # Execute and assert exception propagates
    with pytest.raises(SimpleRateLimitError):
        pr_processing.get_pr_diff(gp, th, model="m")

    # ensure logger.error was called with expected content
    assert any("Rate limit exceeded" in msg or "Rate limit" in msg or "rate limit" in msg for msg in record["error"])


def test_disable_extra_lines_and_under_limit_returns_full_diff_and_handles_pr_language_logging(monkeypatch):
    # This test covers:
    # - disable_extra_lines True (lines 45-46)
    # - pr_languages truthy and logging works (so try block executed)
    # - under limit path (returns full diff)
    gp = DummyGitProvider(diff_files=[{"f": "x"}], languages=[{"language": "Python"}])
    th = DummyTokenHandler()

    # monkeypatch get_settings to ensure it is NOT used when disable_extra_lines True,
    # but still present for safety
    monkeypatch.setattr(pr_processing, "get_settings", lambda: make_settings_obj())

    # Make sort_files_by_main_languages return a non-empty list
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])

    # Make pr_generate_extended_diff return small total_tokens to be under limit
    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff",
                        lambda pr_langs, token_handler, add_ln, patch_extra_lines_before, patch_extra_lines_after:
                        (["patch_line_1", "patch_line_2"], 1, [1, 1]))

    # set thresholds and get_max_tokens to allow under-limit path
    monkeypatch.setattr(pr_processing, "OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD", 5)
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 100)

    # logger that will operate normally (info won't raise)
    record = {"info": [], "error": [], "debug": []}
    dummy_logger = DummyLogger(record=record)
    monkeypatch.setattr(pr_processing, "get_logger", lambda: dummy_logger)

    result = pr_processing.get_pr_diff(gp, th, model="m", add_line_numbers_to_hunks=False, disable_extra_lines=True)
    assert result == "patch_line_1\npatch_line_2"
    # Ensure PR main language info log was recorded
    assert any("PR main language" in msg or "Python" in msg for msg in record["info"])


def test_over_limit_pruning_builds_lists_and_returns_remaining_files(monkeypatch):
    # This test covers:
    # - cap_and_log_extra_lines path (disable_extra_lines False)
    # - over-limit path, compression, pruning and building added/modified/deleted lists
    # - return_remaining_files True and False
    gp = DummyGitProvider(diff_files=[{"f": "x"}], languages=[{"language": "Python"}])
    th = DummyTokenHandler(base=0)  # simpler counting

    # Provide get_settings and cap_and_log_extra_lines
    monkeypatch.setattr(pr_processing, "get_settings", lambda: make_settings_obj(before=2, after=3))
    monkeypatch.setattr(pr_processing, "cap_and_log_extra_lines", lambda n, s: n)

    # sort_files_by_main_languages returns something non-empty
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])

    # pr_generate_extended_diff returns big total_tokens to force pruning path
    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff",
                        lambda pr_langs, token_handler, add_ln, patch_extra_lines_before, patch_extra_lines_after:
                        (["ext_line"], 1000, [1000]))

    # Prepare a compressed diff result with one compressed patch
    # The file_dict should contain various edit types to generate added/modified/deleted lists
    file_dict = {
        "file_added.py": {"edit_type": pr_processing.EDIT_TYPE.ADDED},
        "file_modified.py": {"edit_type": pr_processing.EDIT_TYPE.MODIFIED},
        "file_deleted.py": {"edit_type": pr_processing.EDIT_TYPE.DELETED},
        "file_in_patch.py": {"edit_type": pr_processing.EDIT_TYPE.MODIFIED},
    }
    patches_compressed_list = [["compressed_patch_line"]]
    total_tokens_list = [5]
    deleted_files_list = []
    remaining_files_list = ["file_in_patch.py"]
    files_in_patches_list = [["file_in_patch.py"]]

    def fake_pr_generate_compressed_diff(pr_langs, token_handler, model, add_ln, large_pr_handling):
        return (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list)

    monkeypatch.setattr(pr_processing, "pr_generate_compressed_diff", fake_pr_generate_compressed_diff)

    # Make get_max_tokens such that max_tokens - curr_token > delta_tokens (delta_tokens=10)
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 100)
    monkeypatch.setattr(pr_processing, "OUTPUT_BUFFER_TOKENS_HARD_THRESHOLD", 10)

    # clip_tokens just returns input
    monkeypatch.setattr(pr_processing, "clip_tokens", lambda s, x: s)

    # Provide a logger
    record = {"info": [], "error": [], "debug": []}
    dummy_logger = DummyLogger(record=record)
    monkeypatch.setattr(pr_processing, "get_logger", lambda: dummy_logger)

    # First, call with return_remaining_files False
    final = pr_processing.get_pr_diff(gp, th, model="m", add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=False, return_remaining_files=False)
    assert "compressed_patch_line" in final
    # Should include added and deleted lists (modified also possible). Use module constants to check presence.
    assert pr_processing.ADDED_FILES_ in final
    assert pr_processing.DELETED_FILES_ in final or pr_processing.MORE_MODIFIED_FILES_ in final

    # Now call with return_remaining_files True; should return tuple (final_diff, remaining_files_list)
    final_tuple = pr_processing.get_pr_diff(gp, th, model="m", add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=False, return_remaining_files=True)
    assert isinstance(final_tuple, tuple) and len(final_tuple) == 2
    final_diff_str, remaining = final_tuple
    assert "compressed_patch_line" in final_diff_str
    assert remaining == remaining_files_list
