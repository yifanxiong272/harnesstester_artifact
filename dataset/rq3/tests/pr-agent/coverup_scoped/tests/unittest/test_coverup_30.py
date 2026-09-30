# file: pr_agent/tools/pr_help_docs.py:494-534
# asked: {"lines": [495, 497, 498, 499, 501, 502, 503, 504, 505, 507, 509, 510, 511, 513, 514, 515, 516, 518, 519, 520, 521, 522, 523, 526, 527, 528, 529, 530, 531, 532, 533, 534], "branches": [[503, 504], [503, 507], [514, 515], [514, 518], [528, 529], [528, 531]]}
# gained: {"lines": [495, 497, 498, 499, 501, 502, 503, 504, 505, 507, 509, 510, 511, 513, 514, 515, 516, 518, 519, 520, 521, 522, 523, 526, 527, 528, 531, 532, 533, 534], "branches": [[503, 504], [503, 507], [514, 515], [514, 518], [528, 531]]}

import pytest
import asyncio
from types import SimpleNamespace

from pr_agent.tools import pr_help_docs as ph


class DummyLogger:
    def __init__(self):
        self.error_calls = []
        self.exception_calls = []
        self.debug_calls = []

    def error(self, msg, artifacts=None):
        self.error_calls.append((msg, artifacts))

    def exception(self, msg):
        self.exception_calls.append(msg)

    def debug(self, msg):
        self.debug_calls.append(msg)


class FakeSettings(dict):
    def __init__(self):
        super().__init__(
            {
                "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
                "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
                "PR_HELP_DOCS.DOCS_PATH": "docs",
                "PR_HELP_DOCS.REPO_URL": "",
                "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
            }
        )
        self.pr_help_docs_headings_prompts = SimpleNamespace(system="sys_prompt", user="user_prompt")
        self.pr_help_docs_prompts = SimpleNamespace(system="sys2", user="user2")

    def get(self, k, d=None):
        return super().get(k, d)

    def __getitem__(self, k):
        return super().__getitem__(k)


class DummyTokenHandler:
    def __init__(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_rank_docs_success(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Provide a fake settings that satisfies PRHelpDocs.__init__
    fake_settings = FakeSettings()
    fake_settings.pr_help_docs_headings_prompts = SimpleNamespace(system="sys_h", user="usr_h")
    fake_settings.pr_help_docs_prompts = SimpleNamespace(system="sys_p", user="usr_p")
    monkeypatch.setattr(ph, "get_settings", lambda: fake_settings)

    # Provide a fake git provider that can deduce a repo url
    class FakeGitProvider:
        def __init__(self):
            pass

        def get_git_repo_url(self, ctx_url):
            return "https://example.com/repo.git"

    monkeypatch.setattr(ph, "get_git_provider_with_context", lambda ctx: FakeGitProvider())

    # Replace TokenHandler to avoid heavy initialization
    monkeypatch.setattr(ph, "TokenHandler", DummyTokenHandler)

    # Capture calls to aggregate_documentation_files_for_prompt_contents
    calls = []

    def aggregate_mock(docs, return_just_headings=False):
        # store a shallow copy of keys to inspect later
        calls.append((list(docs.keys()), return_just_headings))
        if return_just_headings:
            return "h1: heading for a\nh2: heading for b"
        return "FULL_PROMPT_FOR_SELECTED_DOCS"

    monkeypatch.setattr(ph, "aggregate_documentation_files_for_prompt_contents", aggregate_mock)

    # Trim behavior: return as-is for headings, convert full to final
    def trim_mock(s, max_allowed_txt_input, only_return_if_trim_needed=False):
        if s.startswith("h1:"):
            return s
        if s.startswith("FULL_PROMPT"):
            return "FINAL_PROMPT"
        return s

    # retry_with_fallback_models should be async and return a response string
    async def retry_mock(prep, model_type=None):
        return "DUMMY_RESPONSE"

    monkeypatch.setattr(ph, "retry_with_fallback_models", retry_mock)

    # load_yaml should parse the dummy response into a dict with relevant_files_ranking
    def load_yaml_mock(response):
        assert response == "DUMMY_RESPONSE"
        # include some invalid indices to test filtering
        return {"relevant_files_ranking": [{"idx": "1"}, {"idx": "-1"}, {"idx": "5"}]}

    monkeypatch.setattr(ph, "load_yaml", load_yaml_mock)

    # Prepare PRHelpDocs instance with required ctx_url and a simple ai_handler factory
    pr = ph.PRHelpDocs(ctx_url="http://ctx-url", ai_handler=lambda: object())
    pr._trim_docs_input = trim_mock

    docs = {"a.md": "content A", "b.md": "content B"}

    result = await pr._rank_docs_and_return_them_as_prompt(docs, max_allowed_txt_input=1000)

    assert result == "FINAL_PROMPT"
    # First aggregate call should be headings, second should be with selected docs (only index 1 valid -> "b.md")
    assert len(calls) >= 2
    assert calls[0][1] is True
    assert calls[-1][1] is False
    assert calls[-1][0] == ["b.md"]
    assert pr.vars["snippets"] == "h1: heading for a\nh2: heading for b".strip()
    assert logger.error_calls == []
    assert logger.exception_calls == []


@pytest.mark.asyncio
async def test_trim_input_empty_first_returns_empty_and_logs(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    fake_settings = FakeSettings()
    fake_settings.pr_help_docs_headings_prompts = SimpleNamespace(system="s", user="u")
    fake_settings.pr_help_docs_prompts = SimpleNamespace(system="s2", user="u2")
    monkeypatch.setattr(ph, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(ph, "get_git_provider_with_context", lambda ctx: SimpleNamespace(get_git_repo_url=lambda url: "repo"))
    monkeypatch.setattr(ph, "TokenHandler", DummyTokenHandler)

    def aggregate_mock(docs, return_just_headings=False):
        return "SOME_HEADINGS"

    monkeypatch.setattr(ph, "aggregate_documentation_files_for_prompt_contents", aggregate_mock)

    # _trim_docs_input returns empty string to trigger early return
    def trim_empty(s, max_allowed_txt_input, only_return_if_trim_needed=False):
        return ""

    pr = ph.PRHelpDocs(ctx_url="ctx://", ai_handler=lambda: object())
    pr._trim_docs_input = trim_empty

    docs = {"a.md": "content A"}

    result = await pr._rank_docs_and_return_them_as_prompt(docs, max_allowed_txt_input=10)

    assert result == ""
    assert any("_trim_docs_input returned an empty result." in call[0] for call in logger.error_calls)


@pytest.mark.asyncio
async def test_load_yaml_failure_logs_and_returns_empty(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    fake_settings = FakeSettings()
    fake_settings.pr_help_docs_headings_prompts = SimpleNamespace(system="s", user="u")
    fake_settings.pr_help_docs_prompts = SimpleNamespace(system="s2", user="u2")
    monkeypatch.setattr(ph, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(ph, "get_git_provider_with_context", lambda ctx: SimpleNamespace(get_git_repo_url=lambda url: "repo"))
    monkeypatch.setattr(ph, "TokenHandler", DummyTokenHandler)

    def aggregate_mock(docs, return_just_headings=False):
        return "HEADINGS_OK" if return_just_headings else "FULL_OK"

    monkeypatch.setattr(ph, "aggregate_documentation_files_for_prompt_contents", aggregate_mock)

    # _trim_docs_input returns non-empty for both calls
    def trim_ok(s, max_allowed_txt_input, only_return_if_trim_needed=False):
        return s

    pr = ph.PRHelpDocs(ctx_url="ctx://", ai_handler=lambda: object())
    pr._trim_docs_input = trim_ok

    async def retry_mock(prep, model_type=None):
        return "BAD_RESPONSE"

    monkeypatch.setattr(ph, "retry_with_fallback_models", retry_mock)
    monkeypatch.setattr(ph, "load_yaml", lambda response: None)

    docs = {"a.md": "content A", "b.md": "content B"}

    result = await pr._rank_docs_and_return_them_as_prompt(docs, max_allowed_txt_input=100)

    assert result == ""
    assert any("Failed to parse the AI response." in call[0] for call in logger.error_calls)


@pytest.mark.asyncio
async def test_exception_path_returns_empty_and_logs_exception(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    fake_settings = FakeSettings()
    fake_settings.pr_help_docs_headings_prompts = SimpleNamespace(system="s", user="u")
    fake_settings.pr_help_docs_prompts = SimpleNamespace(system="s2", user="u2")
    monkeypatch.setattr(ph, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(ph, "get_git_provider_with_context", lambda ctx: SimpleNamespace(get_git_repo_url=lambda url: "repo"))
    monkeypatch.setattr(ph, "TokenHandler", DummyTokenHandler)

    # Make aggregate_documentation_files_for_prompt_contents raise an exception to hit except block
    def aggregate_raises(docs, return_just_headings=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(ph, "aggregate_documentation_files_for_prompt_contents", aggregate_raises)

    pr = ph.PRHelpDocs(ctx_url="ctx://", ai_handler=lambda: object())

    docs = {"a.md": "content A"}

    result = await pr._rank_docs_and_return_them_as_prompt(docs, max_allowed_txt_input=100)

    assert result == ""
    assert len(logger.exception_calls) >= 1
    assert any("Unexpected exception thrown" in msg or "Unexpected exception" in msg for msg in logger.exception_calls)
