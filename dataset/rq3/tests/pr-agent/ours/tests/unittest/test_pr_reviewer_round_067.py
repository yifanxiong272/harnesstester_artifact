import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from pr_agent.tools import pr_reviewer as pr_module
from pr_agent.tools.pr_reviewer import PRReviewer


class DummyAI:
    def __init__(self):
        self.main_pr_language = None


class DummyTokenHandler:
    def __init__(self, *args, **kwargs):
        pass


class FakeProvider:
    def __init__(self, *, files=None, unreviewed_files_set=None, previous_review=None):
        # files can be any truthy/falsey that get_files() should return
        self._files = files
        self.unreviewed_files_set = unreviewed_files_set
        self.previous_review = previous_review
        self.pr = SimpleNamespace(title="the-pr-title")
        self._removed_initial = False
        self.published_comments = []
        self.persistent_calls = []

    def get_files(self):
        return self._files

    def get_languages(self):
        return {"python": 1}

    def get_pr_branch(self):
        return "main"

    def get_pr_description(self, split_changes_walkthrough=False):
        return ("pr description", None)

    def get_num_of_files(self):
        return 0

    def get_commit_messages(self):
        return "commit message"

    def is_supported(self, feature):
        # keep it simple
        return True

    def publish_comment(self, *args, **kwargs):
        self.published_comments.append((args, kwargs))

    def publish_persistent_comment(self, *args, **kwargs):
        self.persistent_calls.append((args, kwargs))

    def remove_initial_comment(self):
        self._removed_initial = True


async def _noop_extract_and_cache_pr_tickets(*args, **kwargs):
    return None


async def _retry_stub(callable_obj, *args, **kwargs):
    # Do not call the real preparation to keep deterministic control: simply set prediction to None
    reviewer = getattr(callable_obj, "__self__", None)
    if reviewer is not None:
        reviewer.prediction = None
    return None


class Config:
    def __init__(self):
        self.publish_output = False
        self.enable_custom_labels = False
        self.is_auto_command = False
        # any other flags accessed via .get
    def get(self, k, default=None):
        return getattr(self, k, default)


class PRReviewerConfig:
    def __init__(self):
        self.num_max_findings = 10
        self.require_score_review = False
        self.require_tests_review = False
        self.require_estimate_effort_to_review = False
        self.require_estimate_contribution_time_cost = False
        self.require_can_be_split_review = False
        self.require_security_review = False
        self.extra_instructions = ""
        self.persistent_comment = False
        self.final_update_message = ""
    def get(self, k, default=None):
        return getattr(self, k, default)


class FakeSettings:
    def __init__(self):
        self.config = Config()
        def get(k, default=None):
            # top-level get behaves like retrieving from config when 'config.' prefix not used by callers
            return getattr(self.config, k, default)
        self.get = get
        self.pr_reviewer = PRReviewerConfig()
        self.pr_review_prompt = SimpleNamespace(system="s", user="u")
        self.data = None
    def set(self, k, v):
        setattr(self.config, k, v)


def setup_common(monkeypatch, provider, settings=None):
    # Patch providers and handlers in the module under test to deterministic fakes
    if settings is None:
        settings = FakeSettings()
    monkeypatch.setattr(pr_module, "get_git_provider_with_context", lambda pr_url: provider)
    # ensure default ai handler symbol exists but tests pass explicit ai_handler where needed
    monkeypatch.setattr(pr_module, "LiteLLMAIHandler", DummyAI)
    monkeypatch.setattr(pr_module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(pr_module, "get_settings", lambda: settings)
    monkeypatch.setattr(pr_module, "extract_and_cache_pr_tickets", _noop_extract_and_cache_pr_tickets)
    monkeypatch.setattr(pr_module, "retry_with_fallback_models", _retry_stub)
    # simple logger mock
    logger = Mock()
    monkeypatch.setattr(pr_module, "get_logger", lambda: logger)
    return settings, logger


@pytest.mark.asyncio
async def test_run_no_files_round_067(monkeypatch):
    """
    If provider.get_files() is empty/falsey, run should log and return None early.
    Covers lines ~122-124
    """
    fake = FakeProvider(files=[])  # falsy
    settings, logger = setup_common(monkeypatch, fake)

    # instantiate PRReviewer but pass a trivial ai_handler factory to avoid heavy behavior
    reviewer = PRReviewer("http://fake/pr", ai_handler=lambda: DummyAI())

    # Force incremental off so the branch tested is the early file check
    reviewer.incremental = SimpleNamespace(is_incremental=False)

    result = await reviewer.run()

    assert result is None
    # ensure logger was used to indicate no files
    logger.info.assert_called()
    # inspect last call message contains 'no files' or 'PR has no files'
    last_msg = logger.info.call_args[0][0]
    assert "no files" in last_msg or "PR has no files" in last_msg


@pytest.mark.asyncio
async def test_run_incremental_no_new_files_publish_skipped_round_067(monkeypatch):
    """
    When incremental is enabled and provider.unreviewed_files_set is empty, and publish_output True,
    the code should publish a skip comment referencing previous_review if present and return None.
    Covers branches 142-150
    """
    prev = SimpleNamespace(html_url="http://prev/review")
    fake = FakeProvider(files=["f.py"], unreviewed_files_set=set(), previous_review=prev)

    settings, logger = setup_common(monkeypatch, fake)
    # enable publish_output so publish_comment is invoked
    settings.config.publish_output = True

    reviewer = PRReviewer("http://fake/pr", ai_handler=lambda: DummyAI())
    # set incremental to true
    reviewer.incremental = SimpleNamespace(is_incremental=True)

    result = await reviewer.run()

    assert result is None
    # publish_comment should have been called once with the skip message
    assert fake.published_comments, "expected a publish_comment call"
    # the message should include reference to previous_review html_url
    args, kwargs = fake.published_comments[-1]
    # message is in args[0]
    published_text = args[0]
    assert "Incremental Review Skipped" in published_text
    assert prev.html_url in published_text


@pytest.mark.asyncio
async def test_run_prediction_none_removes_initial_comment_round_067(monkeypatch):
    """
    When publish_output is True and not auto command, the reviewer should post a temporary preparing
    comment and then, if prediction ends up falsy, remove the initial comment and return None.
    Covers lines 152-158
    """
    fake = FakeProvider(files=["f.py"])  # truthy
    settings, logger = setup_common(monkeypatch, fake)
    settings.config.publish_output = True
    # ensure 'is_auto_command' is False via direct assignment on config
    settings.config.is_auto_command = False

    # instantiate reviewer with an ai handler factory
    reviewer = PRReviewer("http://fake/pr", ai_handler=lambda: DummyAI())
    # ensure incremental isn't set so we proceed to publish flow
    reviewer.incremental = SimpleNamespace(is_incremental=False)

    # The retry stub sets reviewer.prediction = None, leading to removal of initial comment
    result = await reviewer.run()

    assert result is None
    # Confirm temporary preparing comment was posted
    assert fake.published_comments, "expected a temporary 'Preparing review...' publish"
    args, kwargs = fake.published_comments[0]
    assert isinstance(kwargs.get("is_temporary"), bool)
    assert kwargs.get("is_temporary") is True

    # Confirm the initial comment removal was invoked
    assert fake._removed_initial is True
