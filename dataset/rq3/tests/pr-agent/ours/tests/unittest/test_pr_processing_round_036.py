import types
import pytest

from pr_agent.algo import pr_processing


class _SimpleConfig:
    def __init__(self, mapping):
        # allow attribute access like config.patch_extra_lines_before
        self.__dict__.update(mapping)
        self._mapping = mapping

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class _Settings:
    def __init__(self, mapping):
        # config attribute used in code
        self.config = _SimpleConfig(mapping)

    def get(self, key, default=None):
        if isinstance(key, str) and key.startswith('config.'):
            k = key.split('.', 1)[1]
            return self.config._mapping.get(k, default)
        return default


class FakeFile:
    def __init__(self, filename, patch, tokens=0, base_file='', head_file='', edit_type=None, ai_file_summary=None):
        self.filename = filename
        self.patch = patch
        self.tokens = tokens
        self.base_file = base_file
        self.head_file = head_file
        self.edit_type = edit_type
        self.ai_file_summary = ai_file_summary


class FakeTokenHandler:
    def __init__(self, prompt_tokens=0, counts=None):
        self.prompt_tokens = prompt_tokens
        self._counts = counts or {}

    def count_tokens(self, s):
        return self._counts.get(s, len(s))


class DummyGitProvider:
    def __init__(self, diff_files=None, languages=None):
        # ensure languages is a mapping by default to match sort_files_by_main_languages expectations
        self._diff_files = diff_files or []
        self._languages = languages if languages is not None else {}

    def get_diff_files(self):
        return self._diff_files

    def get_languages(self):
        return self._languages


def _noop_logger(*args, **kwargs):
    return None


def test_early_return_extended_diff_round_036(monkeypatch):
    """Early return when pr_generate_extended_diff yields an under-limit total_tokens."""
    # Patch pr_generate_extended_diff to return a non-empty extended patches list
    monkeypatch.setattr(pr_processing, 'pr_generate_extended_diff', lambda *a, **k: (['EXT_PATCH_LINE'], 10, 0))

    # Ensure module threshold and model max allow early return path
    monkeypatch.setattr(pr_processing, 'OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD', 5)
    monkeypatch.setattr(pr_processing, 'get_max_tokens', lambda model: 100)

    # Minimal token handler and git provider (get_languages returns a dict to satisfy language handler)
    th = FakeTokenHandler(prompt_tokens=0)
    gp = DummyGitProvider(diff_files=['f1'], languages={})

    res = pr_processing.get_pr_multi_diffs(gp, th, model='any-model')
    assert res == ['EXT_PATCH_LINE'], "Should return joined extended patches when under token limit"


def test_handle_patch_deletions_returning_none_round_036(monkeypatch):
    """If handle_patch_deletions returns None, the file is skipped and no patches are produced."""
    # make pr_generate_extended_diff empty so flow continues (but ensure total_tokens is large enough to avoid early return)
    monkeypatch.setattr(pr_processing, 'pr_generate_extended_diff', lambda *a, **k: ([], 1000, 0))

    # stub sort_files_by_main_languages to provide one file
    file = FakeFile(filename='f.py', patch='SOME_PATCH', tokens=5, base_file='a', head_file='b')
    monkeypatch.setattr(pr_processing, 'sort_files_by_main_languages', lambda langs, files: [{'files': [file]}])

    # make handle_patch_deletions return None to trigger the continue branch
    monkeypatch.setattr(pr_processing, 'handle_patch_deletions', lambda patch, original, new, filename, edit_type: None)

    # stub settings and logger and also stub get_max_tokens to avoid utils.get_max_tokens calling real settings
    monkeypatch.setattr(pr_processing, 'get_settings', lambda: _Settings({'patch_extra_lines_before': 0, 'patch_extra_lines_after': 0, 'verbosity_level': 0, 'custom_model_max_tokens': 0, 'max_model_tokens': 0}))
    monkeypatch.setattr(pr_processing, 'get_max_tokens', lambda model: 100)
    monkeypatch.setattr(pr_processing, 'get_logger', lambda: types.SimpleNamespace(info=_noop_logger, warning=_noop_logger, error=_noop_logger))

    # token handler
    th = FakeTokenHandler(prompt_tokens=0)
    gp = DummyGitProvider(diff_files=['f1'], languages={})

    res = pr_processing.get_pr_multi_diffs(gp, th, model='m')
    assert res == [], "If handle_patch_deletions returns None the file should be skipped and result empty"


def test_finalizing_chunks_and_max_calls_break_round_036(monkeypatch):
    """Build two-file scenario that forces chunk finalization and breaks because of max_calls limit."""
    # Ensure pr_generate_extended_diff returns empty but with large total_tokens so main logic runs
    monkeypatch.setattr(pr_processing, 'pr_generate_extended_diff', lambda *a, **k: ([], 1000, 0))

    # Create two files; add_line_numbers path will be used
    file1 = FakeFile(filename='file1.py', patch="patch1", tokens=0, base_file='a', head_file='b')
    file2 = FakeFile(filename='file2.py', patch="patch2", tokens=0, base_file='a', head_file='b')

    # Provide sorted files directly
    monkeypatch.setattr(pr_processing, 'sort_files_by_main_languages', lambda langs, files: [{'files': [file1, file2]}])

    # Make handle_patch_deletions return the patch unchanged
    monkeypatch.setattr(pr_processing, 'handle_patch_deletions', lambda patch, original, new, filename, edit_type: patch)

    # When add_line_numbers is True the function decouple_and_convert_to_hunks_with_lines_numbers will be called
    monkeypatch.setattr(pr_processing, 'decouple_and_convert_to_hunks_with_lines_numbers', lambda patch, file: f"NUM:{patch}")

    # Settings: set extra lines fields and verbosity >=2 to traverse logging branches
    monkeypatch.setattr(pr_processing, 'get_settings', lambda: _Settings({'patch_extra_lines_before': 0, 'patch_extra_lines_after': 0, 'verbosity_level': 2, 'large_patch_policy': 'skip'}))

    # Provide a token handler with deterministic counts for the transformed patches
    counts = {'NUM:patch1': 50, 'NUM:patch2': 10}
    th = FakeTokenHandler(prompt_tokens=0, counts=counts)

    # Make get_max_tokens small so second file triggers finalization
    monkeypatch.setattr(pr_processing, 'get_max_tokens', lambda model: 60)
    monkeypatch.setattr(pr_processing, 'OUTPUT_BUFFER_TOKENS_SOFT_THRESHOLD', 5)

    # Prevent real logging side-effects
    monkeypatch.setattr(pr_processing, 'get_logger', lambda: types.SimpleNamespace(info=_noop_logger, warning=_noop_logger, error=_noop_logger))

    gp = DummyGitProvider(diff_files=['f1'], languages={})

    # Call with max_calls=1 to ensure call_number increments beyond max and breaks
    res = pr_processing.get_pr_multi_diffs(gp, th, model='m', max_calls=1, add_line_numbers=True)

    # Expect that first file forms the first chunk and second file triggered finalization then break
    assert res == ['NUM:patch1'], "Should finalize first chunk and break due to max_calls, returning only the first chunk"
