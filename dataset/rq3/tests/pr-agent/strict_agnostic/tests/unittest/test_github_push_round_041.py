import asyncio
from types import SimpleNamespace
from pr_agent.servers import github_app
from pr_agent.servers.github_app import handle_push_trigger_for_new_commits

# Helpers used in tests
class _FakeCondition:
    def __init__(self):
        self.wait_called = False
        self.notify_called_with = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def wait(self):
        # simulate a waiter that returns immediately but records it was called
        self.wait_called = True
        return None

    def notify(self, n=1):
        self.notify_called_with = n


def _make_settings(handle_push_trigger=True, ignore_merge=False, backlog=False):
    ga = SimpleNamespace(
        handle_push_trigger=handle_push_trigger,
        push_trigger_ignore_merge_commits=ignore_merge,
        push_trigger_pending_tasks_backlog=backlog,
    )
    return SimpleNamespace(github_app=ga)


def _reset_module_state(module):
    # ensure deterministic state for module-level dicts used in the implementation
    module._duplicate_push_triggers.clear()
    module._pending_task_duplicate_push_conditions.clear()


def test_no_pull_request_round_041():
    """
    If _check_pull_request_event returns (None, None), function should return {}
    Covers early-return branch (lines ~152-154)
    """
    _reset_module_state(github_app)

    # Patch the private checker to return no PR
    github_app._check_pull_request_event = lambda action, body, log_context: (None, None)

    # Run the coroutine deterministically
    result = asyncio.run(handle_push_trigger_for_new_commits({}, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))
    assert result == {}


def test_push_disabled_round_041():
    """
    When repo settings disable push triggers, should return {}
    Covers apply_repo_settings call + handle_push_trigger False branch (lines ~156-158)
    """
    _reset_module_state(github_app)

    # Make _check_pull_request_event return something valid
    pull = {"merge_commit_sha": "msha"}
    api_url = "api://repo"
    github_app._check_pull_request_event = lambda action, body, log_context: (pull, api_url)

    # apply_repo_settings should be callable but do nothing
    github_app.apply_repo_settings = lambda api: None

    # get_settings returns github_app.handle_push_trigger False
    github_app.get_settings = lambda: _make_settings(handle_push_trigger=False)

    result = asyncio.run(handle_push_trigger_for_new_commits({}, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))
    assert result == {}


def test_before_after_equal_round_041():
    """
    If before == after, should return {}, covering the before/after equality branch (lines ~161-165)
    """
    _reset_module_state(github_app)

    pull = {"merge_commit_sha": None}
    api_url = "api://repo"
    github_app._check_pull_request_event = lambda action, body, log_context: (pull, api_url)
    github_app.apply_repo_settings = lambda api: None
    github_app.get_settings = lambda: _make_settings(handle_push_trigger=True, ignore_merge=False, backlog=False)

    body = {"before": "same", "after": "same"}
    result = asyncio.run(handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))
    assert result == {}


def test_ignore_merge_commit_round_041():
    """
    If push_trigger_ignore_merge_commits is True and after == merge_commit_sha, should return {}
    Covers branch at lines ~166-167
    """
    _reset_module_state(github_app)

    pull = {"merge_commit_sha": "merge-sha"}
    api_url = "api://repo"
    github_app._check_pull_request_event = lambda action, body, log_context: (pull, api_url)
    github_app.apply_repo_settings = lambda api: None
    # enable ignore_merge behavior
    github_app.get_settings = lambda: _make_settings(handle_push_trigger=True, ignore_merge=True, backlog=False)

    body = {"before": "a", "after": "merge-sha"}
    result = asyncio.run(handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))
    assert result == {}


def test_perform_commands_notify_round_041():
    """
    Full flow where a perform_auto_commands call is triggered and finally block notifies and decrements counters.
    Covers branches where action proceeds to eligibility check and _perform_auto_commands_github is awaited,
    and the finally block that calls notify and decrements the duplicate counter (lines ~197-206).
    """
    _reset_module_state(github_app)

    pull = {"merge_commit_sha": None}
    api_url = "api://repo"
    github_app._check_pull_request_event = lambda action, body, log_context: (pull, api_url)
    github_app.apply_repo_settings = lambda api: None

    # settings: allow processing, no backlog -> max_active_tasks == 1
    github_app.get_settings = lambda: _make_settings(handle_push_trigger=True, ignore_merge=False, backlog=False)

    # Prepare a fake condition object for this api_url
    fake_cond = _FakeCondition()
    github_app._pending_task_duplicate_push_conditions[api_url] = fake_cond

    # make sure there is no active task currently
    github_app._duplicate_push_triggers[api_url] = 0

    # Patch identity provider to be eligible (return something not identical to Eligibility.NOT_ELIGIBLE)
    class _FakeIdentity:
        def verify_eligibility(self, provider, sender_id, api_url_arg):
            return object()  # guaranteed not to be the singleton NOT_ELIGIBLE

    github_app.get_identity_provider = lambda: _FakeIdentity()

    # Spy for perform_auto_commands
    called = {}

    async def _fake_perform(conf, agent, body_arg, api_arg, log_ctx):
        called['performed'] = (conf, api_arg)
        return "ok"

    github_app._perform_auto_commands_github = _fake_perform

    # Call function
    body = {"before": "b", "after": "c"}
    result = asyncio.run(handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))

    # After execution, perform should have been called and finally block should notify and decrement
    assert 'performed' in called and called['performed'][0] == "push_commands"
    assert fake_cond.notify_called_with == 1
    # duplicate counter should go back to zero
    assert github_app._duplicate_push_triggers.get(api_url, 0) == 0


def test_waiting_task_round_041():
    """
    Covers the branch where current_active_tasks == 1 so the second task waits (lines ~189-196).
    The fake condition.wait returns immediately but records that wait was called.
    """
    _reset_module_state(github_app)

    pull = {"merge_commit_sha": None}
    api_url = "api://repo"
    github_app._check_pull_request_event = lambda action, body, log_context: (pull, api_url)
    github_app.apply_repo_settings = lambda api: None

    # settings: enable backlog so max_active_tasks == 2
    github_app.get_settings = lambda: _make_settings(handle_push_trigger=True, ignore_merge=False, backlog=True)

    # Prepare a fake condition object for this api_url
    fake_cond = _FakeCondition()
    github_app._pending_task_duplicate_push_conditions[api_url] = fake_cond

    # set an active task already present to trigger the waiting branch
    github_app._duplicate_push_triggers[api_url] = 1

    # identity provider -> eligible
    class _FakeIdentity2:
        def verify_eligibility(self, provider, sender_id, api_url_arg):
            return object()

    github_app.get_identity_provider = lambda: _FakeIdentity2()

    # Spy for perform_auto_commands
    called = {}

    async def _fake_perform2(conf, agent, body_arg, api_arg, log_ctx):
        called['performed'] = True
        return None

    github_app._perform_auto_commands_github = _fake_perform2

    body = {"before": "b", "after": "c"}
    result = asyncio.run(handle_push_trigger_for_new_commits(body, event="push", sender="u", sender_id="id", action="action", log_context={}, agent=None))

    # wait branch should have been entered
    assert fake_cond.wait_called is True
    # perform was still called
    assert called.get('performed', False) is True
    # finally block should notify and decrement back to original (1 -> 2 -> 1 after decrement)
    assert fake_cond.notify_called_with == 1
    assert github_app._duplicate_push_triggers.get(api_url, 0) == 1
