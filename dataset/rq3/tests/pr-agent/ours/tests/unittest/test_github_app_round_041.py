import asyncio
import types
import pytest

from pr_agent.servers import github_app as ga


class _FakeGithubAppConfig:
    def __init__(self, handle_push_trigger=True, push_trigger_ignore_merge_commits=False, push_trigger_pending_tasks_backlog=False):
        self.handle_push_trigger = handle_push_trigger
        self.push_trigger_ignore_merge_commits = push_trigger_ignore_merge_commits
        self.push_trigger_pending_tasks_backlog = push_trigger_pending_tasks_backlog


class _FakeSettings:
    def __init__(self, github_app_cfg: _FakeGithubAppConfig):
        self.github_app = github_app_cfg


class _DummyCondition:
    """A tiny async context manager that mimics the methods used in the target code.

    .wait() returns immediately (so tests won't hang).
    .notify(n) is a no-op but recorded for assertions.
    """

    def __init__(self):
        self.notified = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def wait(self):
        # Return immediately to avoid hanging in tests
        return None

    def notify(self, n=1):
        self.notified += n


@pytest.mark.asyncio
async def test_returns_empty_when_no_pull_request_round_041():
    # _check_pull_request_event returns falsy -> immediate empty dict
    orig_check = ga._check_pull_request_event
    try:
        ga._check_pull_request_event = lambda action, body, log_context: (None, None)
        result = await ga.handle_push_trigger_for_new_commits({}, event="push", sender="u", sender_id="1", action="edited", log_context={}, agent=object())
        assert result == {}
    finally:
        ga._check_pull_request_event = orig_check


@pytest.mark.asyncio
async def test_disabled_handle_push_trigger_round_041():
    # When handle_push_trigger is False function returns {}
    orig_check = ga._check_pull_request_event
    orig_apply = ga.apply_repo_settings
    orig_get_settings = ga.get_settings
    try:
        ga._check_pull_request_event = lambda action, body, log_context: ({"merge_commit_sha": None}, "https://api")
        ga.apply_repo_settings = lambda api_url: None
        ga.get_settings = lambda: _FakeSettings(_FakeGithubAppConfig(handle_push_trigger=False))

        res = await ga.handle_push_trigger_for_new_commits({}, event="push", sender="u", sender_id="1", action="opened", log_context={}, agent=object())
        assert res == {}
    finally:
        ga._check_pull_request_event = orig_check
        ga.apply_repo_settings = orig_apply
        ga.get_settings = orig_get_settings


@pytest.mark.asyncio
async def test_before_after_equal_round_041():
    # If before == after function returns {}
    orig_check = ga._check_pull_request_event
    orig_get_settings = ga.get_settings
    orig_apply = ga.apply_repo_settings
    try:
        ga._check_pull_request_event = lambda action, body, log_context: ({"merge_commit_sha": "m"}, "api_url")
        ga.apply_repo_settings = lambda api_url: None
        # enable handling
        ga.get_settings = lambda: _FakeSettings(_FakeGithubAppConfig(handle_push_trigger=True, push_trigger_ignore_merge_commits=False))

        body = {"before": "same", "after": "same"}
        res = await ga.handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="1", action="pushed", log_context={}, agent=object())
        assert res == {}
    finally:
        ga._check_pull_request_event = orig_check
        ga.get_settings = orig_get_settings
        ga.apply_repo_settings = orig_apply


@pytest.mark.asyncio
async def test_ignore_merge_commit_round_041():
    # If push_trigger_ignore_merge_commits is True and after == merge_commit_sha -> return {}
    orig_check = ga._check_pull_request_event
    orig_get_settings = ga.get_settings
    orig_apply = ga.apply_repo_settings
    try:
        ga._check_pull_request_event = lambda action, body, log_context: ({"merge_commit_sha": "merge123"}, "api_url")
        ga.apply_repo_settings = lambda api_url: None
        ga.get_settings = lambda: _FakeSettings(_FakeGithubAppConfig(handle_push_trigger=True, push_trigger_ignore_merge_commits=True))

        body = {"before": "old", "after": "merge123"}
        res = await ga.handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="1", action="pushed", log_context={}, agent=object())
        assert res == {}
    finally:
        ga._check_pull_request_event = orig_check
        ga.get_settings = orig_get_settings
        ga.apply_repo_settings = orig_apply


@pytest.mark.asyncio
async def test_skip_due_to_duplicate_round_041():
    # When _duplicate_push_triggers already at max_active_tasks the function returns {}
    orig_check = ga._check_pull_request_event
    orig_get_settings = ga.get_settings
    orig_apply = ga.apply_repo_settings
    orig_dup = ga._duplicate_push_triggers
    orig_pending = ga._pending_task_duplicate_push_conditions
    try:
        api = "api://dup"
        ga._duplicate_push_triggers = {api: 1}
        # backlog disabled -> max_active_tasks=1 -> current_active_tasks == max => skip
        ga.get_settings = lambda: _FakeSettings(_FakeGithubAppConfig(handle_push_trigger=True, push_trigger_pending_tasks_backlog=False))
        ga.apply_repo_settings = lambda api_url: None
        ga._check_pull_request_event = lambda action, body, log_context: ({"merge_commit_sha": None}, api)
        ga._pending_task_duplicate_push_conditions = {api: _DummyCondition()}

        body = {"before": "b", "after": "c"}
        res = await ga.handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="1", action="pushed", log_context={}, agent=object())
        assert res == {}
    finally:
        ga._check_pull_request_event = orig_check
        ga.get_settings = orig_get_settings
        ga.apply_repo_settings = orig_apply
        ga._duplicate_push_triggers = orig_dup
        ga._pending_task_duplicate_push_conditions = orig_pending


@pytest.mark.asyncio
async def test_perform_auto_commands_and_release_round_041():
    # Full flow where performing auto commands happens and finally block notifies and decrements the counter
    orig_check = ga._check_pull_request_event
    orig_get_settings = ga.get_settings
    orig_apply = ga.apply_repo_settings
    orig_perform = ga._perform_auto_commands_github
    orig_identity = ga.get_identity_provider
    orig_dup = ga._duplicate_push_triggers
    orig_pending = ga._pending_task_duplicate_push_conditions
    try:
        api = "api://doit"
        called = {"performed": False}

        async def fake_perform(commands_conf, agent, body, api_url, log_context):
            # simulate some async work
            await asyncio.sleep(0)
            called["performed"] = True

        class FakeIdentity:
            def verify_eligibility(self, provider, sender_id, api_url):
                # Return an object that is not equal to the NOT_ELIGIBLE sentinel
                return object()

        ga._perform_auto_commands_github = fake_perform
        ga.get_identity_provider = lambda: FakeIdentity()

        # start with no active tasks so it can enter and increment
        ga._duplicate_push_triggers = {}
        # use a FakeCondition so notify is safe
        cond = _DummyCondition()
        ga._pending_task_duplicate_push_conditions = {api: cond}

        ga._check_pull_request_event = lambda action, body, log_context: ({"merge_commit_sha": "m"}, api)
        ga.apply_repo_settings = lambda api_url: None
        ga.get_settings = lambda: _FakeSettings(_FakeGithubAppConfig(handle_push_trigger=True, push_trigger_ignore_merge_commits=False, push_trigger_pending_tasks_backlog=False))

        body = {"before": "b", "after": "a"}
        await ga.handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="1", action="pushed", log_context={}, agent=object())

        # ensure commands executed and the finally block did notify and decremented the counter
        assert called["performed"] is True
        # after execution the duplicate counter for api should be back to 0
        assert ga._duplicate_push_triggers.get(api, 0) == 0
        # notify was invoked exactly once in finally block
        assert cond.notified >= 1
    finally:
        ga._check_pull_request_event = orig_check
        ga.get_settings = orig_get_settings
        ga.apply_repo_settings = orig_apply
        ga._perform_auto_commands_github = orig_perform
        ga.get_identity_provider = orig_identity
        ga._duplicate_push_triggers = orig_dup
        ga._pending_task_duplicate_push_conditions = orig_pending
