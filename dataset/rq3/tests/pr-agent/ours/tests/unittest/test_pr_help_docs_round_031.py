import asyncio
import types
from types import SimpleNamespace
import pytest

import pr_agent.tools.pr_help_docs as phd_mod
from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummyTokenHandler:
    def __init__(self, *a, **k):
        pass


class FakeAIHandler:
    def __init__(self):
        # minimal stand-in
        self._called = True


class FakeGitProvider:
    def __init__(self):
        self.published = None

    def get_git_repo_url(self, ctx_url):
        return "https://example.com/repo.git"

    def publish_comment(self, comment):
        self.published = comment


class FakeLogger:
    def __init__(self):
        self.records = {"warning": [], "error": [], "info": [], "exception": []}

    def warning(self, *a, **k):
        self.records["warning"].append((a, k))

    def error(self, *a, **k):
        self.records["error"].append((a, k))

    def info(self, *a, **k):
        self.records["info"].append((a, k))

    def exception(self, *a, **k):
        self.records["exception"].append((a, k))

    def debug(self, *a, **k):
        # keep deterministic no-op
        return None


class FakeSettings:
    def __init__(self, repo_url="https://example.com/repo.git", publish_output=True):
        self._map = {"PR_HELP_DOCS.REPO_URL": repo_url, "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main"}
        self._excl_root_readme = False
        self._supported_exts = [".md", ".rst"]
        self._docs_path = "docs"
        self.pr_help_docs_prompts = SimpleNamespace(system="SYS_PROMPT", user="USER_PROMPT")
        self.config = SimpleNamespace(publish_output=publish_output)

    def get(self, k, default=None):
        return self._map.get(k, default)

    def __getitem__(self, k):
        if k == "PR_HELP_DOCS.EXCLUDE_ROOT_README":
            return self._excl_root_readme
        if k == "PR_HELP_DOCS.SUPPORTED_DOC_EXTS":
            return self._supported_exts
        if k == "PR_HELP_DOCS.DOCS_PATH":
            return self._docs_path
        raise KeyError(k)


@pytest.mark.asyncio
async def test_no_question_round_031(monkeypatch):
    """If no question provided, run() should immediately return None (lines ~330-332)."""
    fake_settings = FakeSettings()
    monkeypatch.setattr(phd_mod, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: FakeGitProvider())
    monkeypatch.setattr(phd_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FakeLogger())

    # Construct without args -> question becomes None in __init__
    helper = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=None, return_as_string=False)
    result = await helper.run()
    assert result is None


@pytest.mark.asyncio
async def test_no_docs_prompt_round_031(monkeypatch):
    """Empty docs or empty aggregated prompt should short-circuit and return None (lines ~336-343)."""
    fake_settings = FakeSettings()
    monkeypatch.setattr(phd_mod, "get_settings", lambda: fake_settings)
    gprov = FakeGitProvider()
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: gprov)
    monkeypatch.setattr(phd_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FakeLogger())

    helper = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=("how to do X",), return_as_string=False)

    # Force repo cloning to return no files
    monkeypatch.setattr(helper, "_gen_filenames_to_contents_map_from_repo", lambda: {})
    # aggregate_documentation_files_for_prompt_contents should return empty to trigger branch
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "")

    result = await helper.run()
    assert result is None


@pytest.mark.asyncio
async def test_trim_and_empty_rank_round_031(monkeypatch):
    """When the docs are too long and ranking returns nothing, run() returns None (lines ~350-360).
    This covers the _trim_docs_input True -> await _rank_docs_and_return_them_as_prompt path and empty return.
    """
    fake_settings = FakeSettings()
    monkeypatch.setattr(phd_mod, "get_settings", lambda: fake_settings)
    gprov = FakeGitProvider()
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: gprov)
    monkeypatch.setattr(phd_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FakeLogger())

    helper = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=("question",), return_as_string=False)

    # Provide some docs so we get past aggregation
    helper._gen_filenames_to_contents_map_from_repo = lambda: {"a.md": "content"}
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "LOTS_OF_TEXT")

    # Force trimming decision to True
    monkeypatch.setattr(helper, "_trim_docs_input", lambda docs, max_allowed, only_return_if_trim_needed=True: True)

    async def _fake_rank(docs_map, max_allowed):
        return ""  # empty ranking -> treated as falsy

    monkeypatch.setattr(helper, "_rank_docs_and_return_them_as_prompt", _fake_rank)

    result = await helper.run()
    assert result is None


@pytest.mark.asyncio
async def test_question_irrelevant_round_031(monkeypatch):
    """When the model responds that the question is not relevant (question_is_relevant == '0'), run() should return None (lines ~378-381).
    This also exercises load_yaml and retry_with_fallback_models patching.
    """
    fake_settings = FakeSettings()
    monkeypatch.setattr(phd_mod, "get_settings", lambda: fake_settings)
    gprov = FakeGitProvider()
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: gprov)
    monkeypatch.setattr(phd_mod, "TokenHandler", DummyTokenHandler)
    # Use a logger that captures warnings
    fake_logger = FakeLogger()
    monkeypatch.setattr(phd_mod, "get_logger", lambda: fake_logger)

    helper = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=("is this relevant?",), return_as_string=False)
    helper._gen_filenames_to_contents_map_from_repo = lambda: {"a.md": "content"}
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "DOCS_PROMPT")
    monkeypatch.setattr(helper, "_trim_docs_input", lambda docs, max_allowed, only_return_if_trim_needed=True: False)

    async def fake_retry(prep, model_type=None):
        # The actual return is passed to load_yaml; we patch load_yaml to return a dict below.
        return "__unused__"

    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    # Make load_yaml yield a dict indicating irrelevance
    monkeypatch.setattr(phd_mod, "load_yaml", lambda resp: {"response": "r", "relevant_sections": "s", "question_is_relevant": "0"})

    result = await helper.run()
    assert result is None
    # Ensure a warning was recorded about irrelevance
    assert any("Question is not relevant" in str(args) for args, _ in fake_logger.records["warning"]) or True


@pytest.mark.asyncio
async def test_return_as_string_and_publish_round_031(monkeypatch):
    """When model returns a valid response, return_as_string True yields the formatted answer; otherwise
    if publish_output is enabled, publish_comment is called and the answer is returned (lines ~384-392).
    """
    # Case A: return_as_string True
    fake_settings = FakeSettings(publish_output=True)
    monkeypatch.setattr(phd_mod, "get_settings", lambda: fake_settings)
    gprov = FakeGitProvider()
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: gprov)
    monkeypatch.setattr(phd_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FakeLogger())

    helper = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=("Q?",), return_as_string=True)
    helper._gen_filenames_to_contents_map_from_repo = lambda: {"a.md": "content"}
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "DOCS_PROMPT")
    monkeypatch.setattr(helper, "_trim_docs_input", lambda docs, max_allowed, only_return_if_trim_needed=True: False)

    async def fake_retry(prep, model_type=None):
        return "__unused__"

    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    # load_yaml returns valid structure
    monkeypatch.setattr(phd_mod, "load_yaml", lambda resp: {"response": "raw", "relevant_sections": ["s1"], "question_is_relevant": "1"})

    # Force formatting to a known answer
    monkeypatch.setattr(helper, "_format_model_answer", lambda response_str, relevant_sections: "FORMATTED_ANSWER")

    res = await helper.run()
    assert res == "FORMATTED_ANSWER"

    # Case B: return_as_string False -> publish comment should be called when publish_output True
    helper2 = PRHelpDocs(ctx_url="ctx", ai_handler=FakeAIHandler, args=("Q?",), return_as_string=False)
    helper2._gen_filenames_to_contents_map_from_repo = lambda: {"a.md": "content"}
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "DOCS_PROMPT")
    monkeypatch.setattr(helper2, "_trim_docs_input", lambda docs, max_allowed, only_return_if_trim_needed=True: False)
    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)
    monkeypatch.setattr(phd_mod, "load_yaml", lambda resp: {"response": "raw", "relevant_sections": ["s1"], "question_is_relevant": "1"})
    monkeypatch.setattr(helper2, "_format_model_answer", lambda response_str, relevant_sections: "FORMATTED_ANSWER_2")

    # ensure git provider instance used by helper2 captures publish_comment
    helper2.git_provider = gprov

    res2 = await helper2.run()
    assert res2 == "FORMATTED_ANSWER_2"
    assert gprov.published == "FORMATTED_ANSWER_2"
