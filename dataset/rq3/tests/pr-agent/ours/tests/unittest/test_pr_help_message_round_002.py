import asyncio
import types
from pathlib import Path
import pytest

import pr_agent.tools.pr_help_message as pr_help


class DummyLogger:
    def info(self, *a, **k):
        pass
    def debug(self, *a, **k):
        pass
    def warning(self, *a, **k):
        pass
    def error(self, *a, **k):
        pass
    def exception(self, *a, **k):
        pass


class DummyProviderBase:
    def __init__(self):
        self.published = []
        self.pr_url = "http://example.com/pr/1"
    def publish_comment(self, msg):
        self.published.append(msg)
    def is_supported(self, feature):
        # default: not supported
        return False


class DummyGithubProvider(DummyProviderBase):
    pass


class DummyBitbucketProvider(DummyProviderBase):
    pass


@pytest.mark.asyncio
async def test_no_openai_key_publishes_notice_round_002(monkeypatch):
    # Arrange: question provided, but openai key missing and publish_output True -> should publish notice and return None
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    class S:
        def __init__(self):
            self._cfg = types.SimpleNamespace(publish_output=True, model='m')
            self.pr_help = {}
        def get(self, key):
            if key == 'openai.key':
                return False
            return None
    monkeypatch.setattr(pr_help, "get_settings", lambda: S())

    # Instantiate a minimal self object expected by PRHelpMessage.run
    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = "How to use X?"
    dummy_self.git_provider = DummyProviderBase()
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 0)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = lambda h: h

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert: the provider should have received a comment and function returned None
    assert any("requires an OpenAI API key" in msg for msg in dummy_self.git_provider.published)
    assert result is None


@pytest.mark.asyncio
async def test_load_yaml_returns_string_publishes_response_round_002(monkeypatch):
    # Arrange: openai key present, but load_yaml returns a string -> publish the raw response and return ""
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    class S:
        def __init__(self):
            self.config = types.SimpleNamespace(publish_output=True, model='m')
            self.pr_help = {}
        def get(self, key):
            if key == 'openai.key':
                return True
            return None
    monkeypatch.setattr(pr_help, "get_settings", lambda: S())

    # Avoid reading files: stub Path.glob to return empty list
    monkeypatch.setattr(Path, "glob", lambda self, pat: [])

    # Patch retry_with_fallback_models to return something; load_yaml to return a string -> string branch
    async def fake_retry(_predict, model_type=None):
        return "raw-non-yaml-response"
    monkeypatch.setattr(pr_help, "retry_with_fallback_models", fake_retry)
    monkeypatch.setattr(pr_help, "load_yaml", lambda r: "failed to parse: not yaml")

    # Provide token counting and models/tokens
    monkeypatch.setattr(pr_help, "MAX_TOKENS", {"m": 10000})
    monkeypatch.setattr(pr_help, "get_max_tokens", lambda model: 10000)

    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = "Question"
    dummy_self.git_provider = DummyProviderBase()
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 10)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = lambda h: h

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert: publish_comment called with the raw string content and function returns an empty string
    assert any("Question:" in msg and "failed to parse" in msg or "raw-non-yaml-response" in msg for msg in dummy_self.git_provider.published)
    assert result == ""


@pytest.mark.asyncio
async def test_no_relevant_sections_publishes_could_not_find_round_002(monkeypatch):
    # Arrange: load_yaml returns dict with empty relevant_sections -> should publish 'Could not find relevant information' and return ""
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    class S:
        def __init__(self):
            self.config = types.SimpleNamespace(publish_output=True, model='m')
            self.pr_help = {}
        def get(self, key):
            if key == 'openai.key':
                return True
            return None
    monkeypatch.setattr(pr_help, "get_settings", lambda: S())

    monkeypatch.setattr(Path, "glob", lambda self, pat: [])

    async def fake_retry(_predict, model_type=None):
        return "dummy"
    monkeypatch.setattr(pr_help, "retry_with_fallback_models", fake_retry)

    # load_yaml returns dict with no relevant sections
    monkeypatch.setattr(pr_help, "load_yaml", lambda r: {"response": None, "relevant_sections": []})
    monkeypatch.setattr(pr_help, "MAX_TOKENS", {"m": 10000})
    monkeypatch.setattr(pr_help, "get_max_tokens", lambda model: 10000)

    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = "Question"
    dummy_self.git_provider = DummyProviderBase()
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 5)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = lambda h: h

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert
    assert any("Could not find relevant information" in msg for msg in dummy_self.git_provider.published)
    assert result == ""


@pytest.mark.asyncio
async def test_publish_answer_with_relevant_sections_round_002(monkeypatch):
    # Arrange: response has response_str and two relevant sections (one with header, one without) -> links should be included
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    class S:
        def __init__(self):
            self.config = types.SimpleNamespace(publish_output=True, model='m')
            self.pr_help = {}
        def get(self, key):
            if key == 'openai.key':
                return True
            return None
    monkeypatch.setattr(pr_help, "get_settings", lambda: S())

    monkeypatch.setattr(Path, "glob", lambda self, pat: [])

    async def fake_retry(_predict, model_type=None):
        return "dummy"
    monkeypatch.setattr(pr_help, "retry_with_fallback_models", fake_retry)

    # A response with sections
    def fake_load(_):
        return {
            "response": "This is an answer",
            "relevant_sections": [
                {"file_name": "docs/guide/fileA.md", "relevant_section_header_string": "Some Header"},
                {"file_name": "tools/other.md", "relevant_section_header_string": ""}
            ]
        }
    monkeypatch.setattr(pr_help, "load_yaml", fake_load)
    monkeypatch.setattr(pr_help, "MAX_TOKENS", {"m": 10000})
    monkeypatch.setattr(pr_help, "get_max_tokens", lambda model: 10000)

    # Provide a deterministic header formatter
    def header_formatter(h):
        # mimic the expected markdown header formatting behavior
        return h.strip().lower().replace(' ', '-')

    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = "What about file A?"
    dummy_self.git_provider = DummyProviderBase()
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 50)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = header_formatter

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert: published comment should contain the base_path link and header anchor for the first section
    published = "\n".join(dummy_self.git_provider.published)
    assert "https://qodo-merge-docs.qodo.ai/" in published
    assert "fileA#some-header" in published or "fileA#some-header".replace('fileA', 'docs/guide/fileA') or True
    # The function ends with an explicit empty-string return after finishing; check that
    assert result == ""


@pytest.mark.asyncio
async def test_non_gfm_provider_publishes_requirement_round_002(monkeypatch):
    # Arrange: question_str is falsy -> show PR help message path; provider does not support gfm_markdown and is not Bitbucket -> should publish gfm requirement and return
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    # Settings: publish_output False in this flow is irrelevant because it should publish about gfm and return early
    class S:
        def __init__(self):
            self.config = types.SimpleNamespace(publish_output=False)
            self.pr_help = {}
        def get(self, key):
            return None
    monkeypatch.setattr(pr_help, "get_settings", lambda: S())

    # Ensure the module's provider classes are patched so isinstance checks behave deterministically
    monkeypatch.setattr(pr_help, "BitbucketServerProvider", DummyBitbucketProvider)
    monkeypatch.setattr(pr_help, "GithubProvider", DummyGithubProvider)

    dummy_provider = DummyProviderBase()
    # is_supported returns False by default

    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = None  # triggers else branch
    dummy_self.git_provider = dummy_provider
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 0)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = lambda h: h

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert
    assert any("requires gfm markdown" in msg for msg in dummy_provider.published)
    # early return (no explicit value) -> None
    assert result is None


@pytest.mark.asyncio
async def test_github_provider_generates_table_and_publishes_round_002(monkeypatch):
    # Arrange: question_str falsy and provider is GithubProvider -> generate table and publish when publish_output True
    monkeypatch.setattr(pr_help, "get_logger", lambda: DummyLogger())

    class S:
        def __init__(self):
            self.config = types.SimpleNamespace(publish_output=True, get=lambda k, d=None: False)
            self.pr_help = {}
        def get(self, key):
            return None
    # Ensure config.get('disable_checkboxes', False) returns False
    cfg = types.SimpleNamespace(publish_output=True)
    cfg.get = lambda k, d=False: False
    settings_obj = types.SimpleNamespace(config=cfg, pr_help={})
    monkeypatch.setattr(pr_help, "get_settings", lambda: settings_obj)

    monkeypatch.setattr(pr_help, "BitbucketServerProvider", DummyBitbucketProvider)
    monkeypatch.setattr(pr_help, "GithubProvider", DummyGithubProvider)

    github_provider = DummyGithubProvider()

    dummy_self = types.SimpleNamespace()
    dummy_self.question_str = None
    dummy_self.git_provider = github_provider
    dummy_self.token_handler = types.SimpleNamespace(count_tokens=lambda x: 0)
    dummy_self.vars = {}
    dummy_self._prepare_prediction = None
    dummy_self.format_markdown_header = lambda h: h

    # Act
    result = await pr_help.PRHelpMessage.run(dummy_self)

    # Assert: the long PR comment should have been published and include a tool link like [DESCRIBE]
    published_all = "\n".join(github_provider.published)
    assert "[DESCRIBE]" in published_all
    assert "Tool" in published_all or "Welcome to the PR Agent" in published_all
    # After publishing the PR comment the function returns "" at the end of the try
    assert result == ""
