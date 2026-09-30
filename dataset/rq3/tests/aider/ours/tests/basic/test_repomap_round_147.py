import pytest

from aider.repomap import RepoMap


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


def test_return_when_max_map_tokens_nonpositive_round_147():
    # Ensure early return when max_map_tokens <= 0 (covers line 111->112)
    get_repo_map = RepoMap.get_repo_map

    class S:
        pass

    s = S()
    s.max_map_tokens = 0
    s.max_context_window = 0
    s.map_mul_no_files = 1
    s.repo_content_prefix = None
    s.verbose = False
    s.io = DummyIO()

    # If the function continues it would call get_ranked_tags_map; fail if that happens
    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("get_ranked_tags_map should not be called when max_map_tokens <= 0")

    s.get_ranked_tags_map = _should_not_be_called

    res = get_repo_map(s, chat_files=["a.py"], other_files=["b.py"])  # other_files non-empty
    assert res is None


def test_handle_recursion_error_disables_map_round_147():
    # Simulate get_ranked_tags_map raising RecursionError to hit the except block
    get_repo_map = RepoMap.get_repo_map

    class S:
        pass

    s = S()
    s.max_map_tokens = 123
    s.max_context_window = 10000
    s.map_mul_no_files = 1
    s.repo_content_prefix = None
    s.verbose = False
    s.io = DummyIO()

    def raising_recursion(*args, **kwargs):
        raise RecursionError()

    s.get_ranked_tags_map = raising_recursion

    res = get_repo_map(s, chat_files=["a.py"], other_files=["b.py"])

    # The function should return None, set max_map_tokens to 0, and call io.tool_error with the expected message
    assert res is None
    assert s.max_map_tokens == 0
    assert s.io.errors == ["Disabling repo map, git repo too large?"]


def test_verbose_outputs_token_count_and_returns_content_round_147():
    # When verbose is True and files_listing is returned, token_count and tool_output should be used
    get_repo_map = RepoMap.get_repo_map

    class S:
        pass

    s = S()
    s.max_map_tokens = 100
    s.max_context_window = 10000
    s.map_mul_no_files = 1
    # prefix with a placeholder for {other}, so we can assert the formatted output
    s.repo_content_prefix = "PREFIX: {other}"
    s.verbose = True
    s.io = DummyIO()

    # token_count returns 2048 to produce 2.0 k-tokens in the formatted output
    s.token_count = lambda text: 2048

    def rank_and_capture(chat_files, other_files, max_map_tokens, mentioned_fnames, mentioned_idents, force_refresh):
        # The function should have converted a None mentioned_fnames to an empty set
        assert isinstance(mentioned_fnames, set)
        # Return non-empty listing so later code path continues to verbose output and concatenation
        return "LISTING"

    s.get_ranked_tags_map = rank_and_capture

    # Use no chat_files to exercise the branch that sets `other` to "" and uses larger max_map_tokens
    res = get_repo_map(s, chat_files=[], other_files=["b.py"], mentioned_fnames=None, mentioned_idents=None)

    # The repo_content_prefix is "PREFIX: {other}" and other is empty, so result should be "PREFIX: LISTING"
    assert res == "PREFIX: LISTING"
    # token_count 2048 -> 2.0 k-tokens formatting
    assert s.io.outputs == ["Repo-map: 2.0 k-tokens"]


def test_files_listing_empty_returns_none_round_147():
    # If get_ranked_tags_map returns a falsy files_listing, the function should return None (line 148->149)
    get_repo_map = RepoMap.get_repo_map

    class S:
        pass

    s = S()
    s.max_map_tokens = 50
    s.max_context_window = 1000
    s.map_mul_no_files = 1
    s.repo_content_prefix = None
    s.verbose = False
    s.io = DummyIO()

    # Return empty string which is falsy and should trigger the early return at 149
    s.get_ranked_tags_map = lambda *args, **kwargs: ""

    res = get_repo_map(s, chat_files=["a.py"], other_files=["b.py"])
    assert res is None
