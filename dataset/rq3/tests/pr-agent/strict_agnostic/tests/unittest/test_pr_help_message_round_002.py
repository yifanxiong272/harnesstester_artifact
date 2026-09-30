import pytest
from types import SimpleNamespace
from pr_agent.tools import pr_help_message as phm

# Simple fake logger to capture calls deterministically
class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.warnings = []
        self.debugs = []
        self.exceptions = []

    def info(self, msg, *args, **kwargs):
        self.infos.append(str(msg))

    def error(self, msg, *args, **kwargs):
        self.errors.append(str(msg))

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(str(msg))

    def debug(self, msg, *args, **kwargs):
        self.debugs.append(str(msg))

    def exception(self, msg, *args, **kwargs):
        self.exceptions.append(str(msg))


@pytest.mark.asyncio
async def test_question_requires_api_key_publish_true_round_002(monkeypatch):
    """
    Scenario: question_str is set, but openai.key is missing and settings.config.publish_output is True.
    Expectation: the git_provider.publish_comment is called with a message about OpenAI API key requirement,
    and the function returns early (None or empty string as per implementation path).
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    # Fake settings: get('openai.key') -> None, and config.publish_output True
    fake_config = SimpleNamespace(publish_output=True, model=None)
    # add .get on config to match usage elsewhere
    fake_config.get = lambda k, d=None: None if k == 'disable_checkboxes' else d
    class FakeSettings:
        def __init__(self):
            self.config = fake_config
            self.pr_help = {}
        def get(self, key, default=None):
            if key == 'openai.key':
                return None
            return default
    monkeypatch.setattr(phm, "get_settings", lambda: FakeSettings())

    published = {}
    class FakeGitProvider:
        def __init__(self):
            self.pr_url = "https://example/pr/1"
        def publish_comment(self, text):
            published['text'] = text

    fake_self = SimpleNamespace()
    fake_self.question_str = "How does this work?"
    fake_self.git_provider = FakeGitProvider()
    fake_self.token_handler = SimpleNamespace(count_tokens=lambda x: 0)
    fake_self.vars = {}

    # Call the async run method with our fake self
    result = await phm.PRHelpMessage.run(fake_self)

    # Assertions: publish_comment was invoked with the API key message
    assert 'OpenAI API key' in published.get('text', '') or 'requires an OpenAI API key' in published.get('text', ''), \
        f"Expected publish_comment to mention OpenAI API key, got: {published.get('text')!r}"
    # The implementation returns early; ensure result is None or empty string
    assert result in (None, ""), f"Expected early return None/'' but got: {result!r}"


@pytest.mark.asyncio
async def test_question_requires_api_key_publish_false_logs_error_round_002(monkeypatch):
    """
    Scenario: question_str is set, openai.key missing, but publish_output is False.
    Expectation: no publish_comment called and logger.error is invoked with the API key message.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    fake_config = SimpleNamespace(publish_output=False, model=None)
    fake_config.get = lambda k, d=None: None if k == 'disable_checkboxes' else d
    class FakeSettings:
        def __init__(self):
            self.config = fake_config
            self.pr_help = {}
        def get(self, key, default=None):
            if key == 'openai.key':
                return None
            return default
    monkeypatch.setattr(phm, "get_settings", lambda: FakeSettings())

    published = {}
    class FakeGitProvider:
        def __init__(self):
            self.pr_url = "https://example/pr/2"
        def publish_comment(self, text):
            published['text'] = text

    fake_self = SimpleNamespace()
    fake_self.question_str = "Is this supported?"
    fake_self.git_provider = FakeGitProvider()
    fake_self.token_handler = SimpleNamespace(count_tokens=lambda x: 0)
    fake_self.vars = {}

    result = await phm.PRHelpMessage.run(fake_self)

    # Should have logged an error about missing API key and not published
    assert any('OpenAI API key' in e or 'requires an OpenAI API key' in e for e in fake_logger.errors), \
        f"Expected logger.error to mention OpenAI API key, got errors: {fake_logger.errors}"
    assert 'text' not in published, f"Did not expect publish_comment to be called when publish_output is False: {published}"
    assert result in (None, ""), f"Expected early return None/'' but got: {result!r}"


@pytest.mark.asyncio
async def test_no_question_provider_missing_gfm_round_002(monkeypatch):
    """
    Scenario: question_str is falsy; provider does not support gfm_markdown and is not BitbucketServerProvider.
    Expectation: publish_comment is called notifying that gfm markdown is required.
    This covers the branch where question_str is falsy and the provider lacks gfm support.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    # settings can be minimal for this branch
    fake_config = SimpleNamespace(publish_output=True, model=None)
    fake_config.get = lambda k, d=None: False
    class FakeSettings:
        def __init__(self):
            self.config = fake_config
            self.pr_help = {}
        def get(self, key, default=None):
            return default
    monkeypatch.setattr(phm, "get_settings", lambda: FakeSettings())

    published = {}
    class ProviderNoGfm:
        def is_supported(self, name):
            # explicitly not supporting gfm_markdown
            return False
        def publish_comment(self, text):
            published['text'] = text

    fake_self = SimpleNamespace()
    fake_self.question_str = None  # falsy -> go into the else branch
    fake_self.git_provider = ProviderNoGfm()
    fake_self.token_handler = SimpleNamespace(count_tokens=lambda x: 0)
    fake_self.vars = {}

    result = await phm.PRHelpMessage.run(fake_self)

    assert 'gfm' in published.get('text', '').lower() or 'gfm markdown' in published.get('text', '').lower(), \
        f"Expected publish_comment to mention gfm markdown requirement, got: {published.get('text')!r}"
    assert result in (None, ""), f"Expected early return None/'' but got: {result!r}"
