# file: pr_agent/algo/pr_processing.py:38-142
# asked: {"lines": [45, 46, 55, 56, 57, 64, 65, 79, 81, 82, 84, 85, 86, 89, 90, 91, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 116, 117, 119, 120, 122, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 142], "branches": [[44, 45], [61, 68], [73, 79], [84, 85], [84, 89], [101, 102], [101, 125], [102, 103], [102, 125], [103, 104], [103, 105], [105, 106], [105, 111], [107, 108], [107, 110], [111, 112], [111, 117], [113, 114], [113, 116], [117, 102], [117, 119], [119, 120], [119, 122], [126, 127], [126, 129], [130, 131], [130, 133], [134, 135], [134, 137], [139, 140], [139, 142]]}
# gained: {"lines": [45, 46, 55, 56, 57, 64, 65, 79, 81, 82, 84, 85, 86, 89, 90, 91, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 111, 112, 113, 114, 116, 117, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 142], "branches": [[44, 45], [73, 79], [84, 85], [84, 89], [101, 102], [102, 103], [102, 125], [103, 104], [103, 105], [105, 106], [105, 111], [107, 108], [111, 112], [111, 117], [113, 114], [113, 116], [117, 119], [119, 120], [126, 127], [130, 131], [134, 135], [139, 140], [139, 142]]}

import pytest
import types

import pr_agent.algo.pr_processing as pr_processing


# Helper DummyToken class used in tests
class DummyToken:
    def count_tokens(self, s):
        return len(str(s).split()) if s is not None else 0


def test_disable_extra_lines_and_rate_limit(monkeypatch):
    # Arrange: create a git_provider whose get_diff_files raises RateLimitExceededException
    class DummyGitProvider:
        def get_diff_files(self):
            # Raise with the parameters expected by GithubException.__init__(status, data, headers)
            raise pr_processing.RateLimitExceededException(403, "rate limit exceeded for test", {})

        def get_languages(self):
            return []

    error_messages = []

    class Logger:
        def error(self, msg):
            error_messages.append(msg)

        def info(self, *args, **kwargs):
            pass

        def debug(self, *args, **kwargs):
            pass

    monkeypatch.setattr(pr_processing, "get_logger", lambda: Logger())

    git_provider = DummyGitProvider()
    token_handler = object()  # won't be used

    # Act / Assert: calling with disable_extra_lines True should set those local vars and then
    # raise the RateLimitExceededException which we catch here.
    with pytest.raises(pr_processing.RateLimitExceededException):
        pr_processing.get_pr_diff(git_provider, token_handler, model="any", disable_extra_lines=True)

    # Ensure logger.error was called and contains the original exception message
    assert error_messages, "Expected error to be logged on rate limit"
    assert "rate limit exceeded for test" in error_messages[0]


def test_over_limit_pruning_and_remaining_files(monkeypatch):
    # Arrange: prepare stubs and monkeypatch dependencies to force over-limit pruning flow
    # Create a dummy token handler with count_tokens
    class DummyTokenHandler:
        def count_tokens(self, s):
            if s is None:
                return 0
            # simple token count: words
            return len(str(s).split())

    token_handler = DummyTokenHandler()

    # stub sort_files_by_main_languages to return a non-empty list
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])

    # cap_and_log_extra_lines should be callable; return the same value
    monkeypatch.setattr(pr_processing, "cap_and_log_extra_lines", lambda v, side: v)

    # Make get_logger such that the first info call that contains "PR main language" raises (to hit the except/pass)
    class StatefulLogger:
        def __init__(self):
            self.first_info_called = False
            self.debug_messages = []

        def info(self, msg):
            if not self.first_info_called and "PR main language" in str(msg):
                self.first_info_called = True
                raise Exception("forced logger info exception")
            return None

        def error(self, msg):
            return None

        def debug(self, msg):
            self.debug_messages.append(msg)

    logger = StatefulLogger()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    # Force pr_generate_extended_diff to return a very large token count (so it is over limit)
    def fake_pr_generate_extended_diff(pr_langs, token_handler_arg, add_ln, patch_extra_lines_before=None, patch_extra_lines_after=None):
        return (["extended_patch_line1"], 2000, [10])  # total_tokens large -> will trigger pruning

    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff", fake_pr_generate_extended_diff)

    # Now configure pr_generate_compressed_diff to return a single compressed patch and file info to exercise added/modified/deleted logic
    file_dict = {
        "inpatch.txt": {"edit_type": pr_processing.EDIT_TYPE.MODIFIED},
        "added.txt": {"edit_type": pr_processing.EDIT_TYPE.ADDED},
        "mod.txt": {"edit_type": pr_processing.EDIT_TYPE.MODIFIED},
        "ren.txt": {"edit_type": pr_processing.EDIT_TYPE.RENAMED},
        "del.txt": {"edit_type": pr_processing.EDIT_TYPE.DELETED},
    }
    remaining_files_list = ["added.txt", "mod.txt", "ren.txt", "del.txt"]
    deleted_files_list = []

    def fake_pr_generate_compressed_diff(pr_langs, token_handler_arg, model_arg, add_ln, large_pr_handling_flag):
        patches_compressed_list = [["compressed_line1", "compressed_line2"]]
        # Use a small total token so that there is room to append added/modified/deleted lists
        total_tokens_list = [10]
        files_in_patches_list = [["inpatch.txt"]]
        return (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list)

    monkeypatch.setattr(pr_processing, "pr_generate_compressed_diff", fake_pr_generate_compressed_diff)

    # Ensure get_max_tokens returns a value that causes extended diff to be over limit but leaves room later
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 2000)

    # Execute the function (not requesting remaining files)
    git_provider = types.SimpleNamespace(get_diff_files=lambda: [], get_languages=lambda: {})
    final = pr_processing.get_pr_diff(git_provider, token_handler, model="anymodel", add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=False, return_remaining_files=False)

    # Assert the final diff contains compressed content and the filenames for added/modified/renamed/deleted
    assert "compressed_line1" in final
    assert "compressed_line2" in final
    # The unprocessed files should be present in the final diff (added/mod/renamed/deleted)
    assert "added.txt" in final
    assert "mod.txt" in final
    assert "ren.txt" in final
    assert "del.txt" in final

    # Now call requesting remaining files to get the tuple return branch
    final2, remaining = pr_processing.get_pr_diff(git_provider, token_handler, model="anymodel", add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=False, return_remaining_files=True)
    assert isinstance(final2, str)
    assert remaining == remaining_files_list


def test_large_pr_handling_returns_empty_when_multiple_patches(monkeypatch):
    # Arrange similar to previous test but pr_generate_compressed_diff returns multiple patches and large_pr_handling True
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: [{"language": "Python"}])
    monkeypatch.setattr(pr_processing, "cap_and_log_extra_lines", lambda v, side: v)
    # logger info should be a no-op here
    monkeypatch.setattr(pr_processing, "get_logger", lambda: types.SimpleNamespace(info=lambda *a, **k: None, debug=lambda *a, **k: None, error=lambda *a, **k: None))

    def fake_pr_generate_extended_diff(pr_langs, token_handler_arg, add_ln, patch_extra_lines_before=None, patch_extra_lines_after=None):
        return (["extended_patch_line"], 2000, [10])  # over limit to force compressed generation

    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff", fake_pr_generate_extended_diff)

    def fake_pr_generate_compressed_diff_multiple(pr_langs, token_handler_arg, model_arg, add_ln, large_pr_handling_flag):
        # Return multiple patches to trigger large_pr_handling path
        patches_compressed_list = [["patch1"], ["patch2"]]
        total_tokens_list = [10, 20]
        deleted_files_list = []
        remaining_files_list = []
        file_dict = {}
        files_in_patches_list = [[], []]
        return (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list)

    monkeypatch.setattr(pr_processing, "pr_generate_compressed_diff", fake_pr_generate_compressed_diff_multiple)
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 1000)

    git_provider = types.SimpleNamespace(get_diff_files=lambda: [], get_languages=lambda: {})
    result = pr_processing.get_pr_diff(git_provider, DummyToken(), model="anymodel", add_line_numbers_to_hunks=False, disable_extra_lines=False, large_pr_handling=True)
    assert result == "", "When large_pr_handling is True and multiple patches returned, function should return empty string"
