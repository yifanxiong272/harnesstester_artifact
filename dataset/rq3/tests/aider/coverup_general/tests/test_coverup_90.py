# file: aider/repomap.py:103-167
# asked: {"lines": [112, 143, 144, 145, 146, 149, 152, 153], "branches": [[111, 112], [115, 117], [148, 149], [151, 152]]}
# gained: {"lines": [112, 143, 144, 145, 146, 149, 152, 153], "branches": [[111, 112], [148, 149], [151, 152]]}

import pytest
from types import SimpleNamespace

from aider.repomap import RepoMap


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


@pytest.fixture(autouse=True)
def disable_load_tags_cache(monkeypatch):
    # Prevent any file system access during RepoMap initialization
    monkeypatch.setattr(RepoMap, "load_tags_cache", lambda self: None)
    yield


def test_get_repo_map_returns_none_when_max_map_tokens_zero():
    io = DummyIO()
    rp = RepoMap(map_tokens=0, io=io)
    result = rp.get_repo_map(chat_files=["a"], other_files=["b"])
    assert result is None


def test_recursion_error_disables_map_and_reports(monkeypatch):
    io = DummyIO()
    rp = RepoMap(map_tokens=1000, io=io, verbose=False)

    def fake_get_ranked_tags_map(self, *args, **kwargs):
        raise RecursionError("too deep")

    monkeypatch.setattr(RepoMap, "get_ranked_tags_map", fake_get_ranked_tags_map)

    # Call with other_files non-empty so the code reaches the try/except
    result = rp.get_repo_map(chat_files=[], other_files=["x"], mentioned_fnames=None, mentioned_idents=None)
    # The method should catch RecursionError, call tool_error, set max_map_tokens to 0 and return None
    assert result is None
    assert rp.max_map_tokens == 0
    assert any("Disabling repo map" in e for e in io.errors)


def test_get_repo_map_uses_sets_for_mentioned_and_verbose_reports(monkeypatch):
    io = DummyIO()

    # We'll assert inside fake_get_ranked that mentioned_fnames and mentioned_idents are sets
    captured = {}

    def fake_get_ranked_tags_map(self, chat_files, other_files, max_map_tokens, mentioned_fnames, mentioned_idents, force_refresh):
        # The method should have converted None -> set() for both mentioned arguments
        assert isinstance(mentioned_fnames, set)
        assert isinstance(mentioned_idents, set)
        # Return a non-empty listing so function proceeds past the empty check
        captured["max_map_tokens"] = max_map_tokens
        return "FILE_LISTING_CONTENT"

    # Provide a token_count implementation that returns a known value
    def fake_token_count(self, text):
        assert text == "FILE_LISTING_CONTENT"
        return 2048

    monkeypatch.setattr(RepoMap, "get_ranked_tags_map", fake_get_ranked_tags_map)
    monkeypatch.setattr(RepoMap, "token_count", fake_token_count)

    rp = RepoMap(map_tokens=1024, io=io, verbose=True, repo_content_prefix="REPO-{other}PREFIX:")
    # Call with chat_files non-empty to exercise the "other " branch when formatting prefix
    result = rp.get_repo_map(chat_files=["cf"], other_files=["of"], mentioned_fnames=None, mentioned_idents=None)
    # It should return the repo_content_prefix formatted with other="other " plus the listing
    assert result == "REPO-other PREFIX:FILE_LISTING_CONTENT" or result == "REPO-other PREFIX:FILE_LISTING_CONTENT".replace(" ", " ")
    # Ensure token_count was used (we set it to record via assertion) and that a Repo-map output was produced
    assert any("Repo-map:" in out for out in io.outputs)


def test_get_repo_map_returns_none_when_files_listing_empty(monkeypatch):
    io = DummyIO()

    def fake_get_ranked_tags_map_empty(self, *args, **kwargs):
        return ""  # empty falsy listing should trigger early return

    monkeypatch.setattr(RepoMap, "get_ranked_tags_map", fake_get_ranked_tags_map_empty)

    rp = RepoMap(map_tokens=1024, io=io, verbose=False)
    result = rp.get_repo_map(chat_files=["cf"], other_files=["of"])
    assert result is None
