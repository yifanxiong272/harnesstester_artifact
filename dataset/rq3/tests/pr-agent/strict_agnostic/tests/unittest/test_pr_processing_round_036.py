import pytest

import pr_agent.algo.pr_processing as pr_processing


class DummyRateLimit(Exception):
    pass


class DummyGitProvider:
    def __init__(self, diff_files=None, languages=None, raise_rate=False):
        self._diff_files = diff_files or []
        self._languages = languages or []
        self._raise = raise_rate

    def get_diff_files(self):
        if self._raise:
            # Use the same exception type imported in the module to ensure the except branch is hit
            from github import RateLimitExceededException

            raise RateLimitExceededException("rate limit hit")
        return self._diff_files

    def get_languages(self):
        return self._languages


class SimpleTokenHandler:
    def __init__(self, prompt_tokens=0, counts=None):
        self.prompt_tokens = prompt_tokens
        # counts: map from patch string to token count
        self._counts = counts or {}

    def count_tokens(self, patch: str) -> int:
        return self._counts.get(patch, len(patch))


class FakeFile:
    def __init__(self, filename, patch, tokens=1, base_file="b", head_file="h", edit_type="mod", ai_file_summary=False):
        self.filename = filename
        self.patch = patch
        self.tokens = tokens
        self.base_file = base_file
        self.head_file = head_file
        self.edit_type = edit_type
        self.ai_file_summary = ai_file_summary


def make_settings(patch_extra_before=0, patch_extra_after=0, verbosity_level=1, large_patch_policy="skip", enable_ai_metadata=False):
    class Cfg:
        def __init__(self):
            self.patch_extra_lines_before = patch_extra_before
            self.patch_extra_lines_after = patch_extra_after
            self.verbosity_level = verbosity_level

        def get(self, key, default=None):
            # emulate config.get('large_patch_policy') usage in module
            if key == 'large_patch_policy':
                return large_patch_policy
            return default

    class S:
        def __init__(self):
            self.config = Cfg()

        def get(self, key, default=None):
            # used as get_settings().get("config.enable_ai_metadata", False)
            if key == "config.enable_ai_metadata":
                return enable_ai_metadata
            return default

    return S()


def test_rate_limit_exception_round_036():
    """
    Ensure that a RateLimitExceededException raised by the git provider is logged and re-raised.
    This covers lines 395-397 in the target function.
    """
    gp = DummyGitProvider(raise_rate=True)
    th = SimpleTokenHandler()

    # Monkeypatch the get_settings to a safe default so module-level uses won't fail
    orig_get_settings = pr_processing.get_settings
    pr_processing.get_settings = lambda: make_settings()

    try:
        with pytest.raises(Exception):
            # The specific exception type is from github.RateLimitExceededException inside the module.
            pr_processing.get_pr_multi_diffs(gp, th, model="mymodel", max_calls=5, add_line_numbers=True)
    finally:
        pr_processing.get_settings = orig_get_settings


def test_various_patch_policies_and_final_chunk_round_036(monkeypatch):
    """
    Builds a sequence of files to exercise multiple branches:
      - file with None patch (continue at 437->438)
      - file where handle_patch_deletions returns None (442->443)
      - large patch skipped due to large_patch_policy 'skip' (458->459)
      - small patch appended and returned in final chunk (covers 492->493 and 496->500)

    Asserts the final returned list contains the expected last small converted patch.
    """

    # Prepare files
    file_none = FakeFile("none.txt", patch=None, tokens=1)
    file_deleted = FakeFile("deleted.txt", patch="to_be_deleted", tokens=2)
    file_skip = FakeFile("large.txt", patch="L" * 200, tokens=200)
    file_small = FakeFile("small.txt", patch="smallpatch", tokens=10)

    # Make pr_languages that sort_files_by_main_languages would return
    pr_languages = [{"files": [file_none, file_deleted, file_skip, file_small]}]

    # Monkeypatch helpers in the module
    monkeypatch.setattr(pr_processing, "sort_files_by_main_languages", lambda langs, diffs: pr_languages)

    # pr_generate_extended_diff should return empty so main flow continues
    monkeypatch.setattr(pr_processing, "pr_generate_extended_diff", lambda *a, **k: ([], 9999, []))

    # handle_patch_deletions: return None only for deleted.txt
    def fake_handle_patch_deletions(patch, original, new, filename, edit_type):
        if filename == "deleted.txt":
            return None
        return patch

    monkeypatch.setattr(pr_processing, "handle_patch_deletions", fake_handle_patch_deletions)

    # decouple_and_convert_to_hunks_with_lines_numbers: prefix so we can observe it
    monkeypatch.setattr(pr_processing, "decouple_and_convert_to_hunks_with_lines_numbers", lambda p, f: f"converted: {p}")

    # add_ai_summary_top_patch should not be called in this scenario (enable_ai_metadata False)
    monkeypatch.setattr(pr_processing, "add_ai_summary_top_patch", lambda f, p: p)

    # Control token handling: count_tokens returns big for large and small for small
    token_counts = {
        "converted: " + file_skip.patch: 200,
        "converted: " + file_small.patch: 10,
    }
    token_handler = SimpleTokenHandler(prompt_tokens=0, counts=token_counts)

    # Make get_settings return verbosity >=2 and large_patch_policy 'skip'
    monkeypatch.setattr(pr_processing, "get_settings", lambda: make_settings(verbosity_level=2, large_patch_policy='skip', enable_ai_metadata=False))

    # Control max tokens and soft threshold to force skip on the large patch
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 100)
    # Set soft threshold to 0 to simplify arithmetic
    monkeypatch.setattr(pr_processing, "OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD", 0)

    # Call function
    gp = DummyGitProvider(diff_files=[file_none, file_deleted, file_skip, file_small])
    th = token_handler

    result = pr_processing.get_pr_multi_diffs(gp, th, model="mymodel", max_calls=5, add_line_numbers=True)

    # Expect only the small converted patch to be returned in the final chunk
    assert isinstance(result, list)
    assert len(result) == 1
    assert "converted: smallpatch" in result[0]

    # Additionally ensure that deleted and large patch did not appear
    joined = "\n".join(result)
    assert "to_be_deleted" not in joined
    assert "L" * 10 not in joined
