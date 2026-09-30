# file: pr_agent/servers/github_app.py:145-206
# asked: {"lines": [152, 153, 154, 156, 157, 158, 161, 162, 163, 164, 165, 166, 167, 175, 176, 177, 179, 180, 182, 184, 185, 187, 188, 189, 191, 192, 194, 195, 197, 198, 199, 200, 204, 205, 206], "branches": [[153, 154], [153, 156], [157, 158], [157, 161], [164, 165], [164, 166], [166, 167], [166, 175], [177, 179], [177, 184], [189, 191], [189, 197], [198, 199], [198, 204]]}
# gained: {"lines": [152, 153, 156, 157, 161, 162, 163, 164, 166, 175, 176, 177, 179, 180, 182, 188, 189, 191, 192, 194, 195, 197, 198, 199, 200, 204, 205, 206], "branches": [[153, 156], [157, 161], [164, 166], [166, 175], [177, 179], [189, 191], [189, 197], [198, 199], [198, 204]]}

import asyncio
from types import SimpleNamespace

import pytest

import pr_agent.servers.github_app as github_app
from pr_agent.identity_providers.identity_provider import Eligibility


@pytest.mark.asyncio
async def test_handle_push_trigger_performs_commands_and_restores_counters(monkeypatch):
    # Prepare environment and backups
    orig_get_settings = github_app.get_settings
    orig_apply_repo_settings = github_app.apply_repo_settings
    orig_check = github_app._check_pull_request_event
    orig_get_identity_provider = github_app.get_identity_provider
    orig_perform = getattr(github_app, "_perform_auto_commands_github", None)
    orig_duplicate = github_app._duplicate_push_triggers.copy()
    orig_pending = github_app._pending_task_duplicate_push_conditions.copy()

    api_url = "https://api.test/repo"
    # Configure settings: enable push trigger handling and backlog enabled
    monkeypatch.setattr(
        github_app,
        "get_settings",
        lambda: SimpleNamespace(
            github_app=SimpleNamespace(
                handle_push_trigger=True,
                push_trigger_ignore_merge_commits=False,
                push_trigger_pending_tasks_backlog=True,
            )
        ),
    )
    # No-op apply_repo_settings
    monkeypatch.setattr(github_app, "apply_repo_settings", lambda url: None)

    # _check_pull_request_event must return a PR dict and api_url
    pull_request = {"merge_commit_sha": "deadbeef"}
    monkeypatch.setattr(github_app, "_check_pull_request_event", lambda action, body, ctx: (pull_request, api_url))

    # Provide a fake condition that does not block on wait (so the flow continues)
    class FakeCondition:
        def __init__(self):
            self.notified = 0
            self.entered = False

        async def __aenter__(self):
            self.entered = True
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self.entered = False

        async def wait(self):
            # return immediately to simulate being released by another task
            return

        def notify(self, n=1):
            self.notified += n

    fake_cond = FakeCondition()
    # Set initial duplicate active tasks to 1 to exercise the "waiting" branch
    github_app._duplicate_push_triggers[api_url] = 1
    github_app._pending_task_duplicate_push_conditions[api_url] = fake_cond

    # Identity provider: eligible
    class FakeIdentityProvider:
        def verify_eligibility(self, provider, sender_id, url):
            assert provider == "github"
            assert url == api_url
            return Eligibility.ELIGIBLE

    monkeypatch.setattr(github_app, "get_identity_provider", lambda: FakeIdentityProvider())

    # Track if perform_auto_commands called with expected args
    called = []

    async def fake_perform_auto_commands_github(commands_name, agent, body, url, log_context):
        called.append((commands_name, url, body, log_context))
        return {"result": "ok"}

    monkeypatch.setattr(github_app, "_perform_auto_commands_github", fake_perform_auto_commands_github)

    # Build body with before != after and after != merge_commit_sha
    body = {"before": "aaaa", "after": "bbbb"}
    agent = SimpleNamespace()  # dummy agent
    log_context = {}

    # Run the function
    result = await github_app.handle_push_trigger_for_new_commits(body, event="push", sender="bot", sender_id="42", action="synchronize", log_context=log_context, agent=agent)

    # Assertions: perform_auto_commands should have been called once with expected parameters
    assert len(called) == 1
    assert called[0][0] == "push_commands"
    assert called[0][1] == api_url
    assert called[0][2] == body
    assert result in ({}, None) or result == {} or result is None  # function returns {} on many branches; accept None or {}

    # After execution, duplicate counters should be restored to initial value (1)
    assert github_app._duplicate_push_triggers.get(api_url) == 1
    # Fake condition should have been notified in finally block
    assert fake_cond.notified >= 1

    # Cleanup / restore
    monkeypatch.setattr(github_app, "get_settings", orig_get_settings)
    monkeypatch.setattr(github_app, "apply_repo_settings", orig_apply_repo_settings)
    monkeypatch.setattr(github_app, "_check_pull_request_event", orig_check)
    monkeypatch.setattr(github_app, "get_identity_provider", orig_get_identity_provider)
    if orig_perform is not None:
        monkeypatch.setattr(github_app, "_perform_auto_commands_github", orig_perform)
    else:
        delattr(github_app, "_perform_auto_commands_github")
    github_app._duplicate_push_triggers.clear()
    github_app._duplicate_push_triggers.update(orig_duplicate)
    github_app._pending_task_duplicate_push_conditions.clear()
    github_app._pending_task_duplicate_push_conditions.update(orig_pending)


@pytest.mark.asyncio
async def test_handle_push_trigger_skipped_when_not_eligible(monkeypatch):
    # Prepare environment and backups
    orig_get_settings = github_app.get_settings
    orig_apply_repo_settings = github_app.apply_repo_settings
    orig_check = github_app._check_pull_request_event
    orig_get_identity_provider = github_app.get_identity_provider
    orig_perform = getattr(github_app, "_perform_auto_commands_github", None)
    orig_duplicate = github_app._duplicate_push_triggers.copy()
    orig_pending = github_app._pending_task_duplicate_push_conditions.copy()

    api_url = "https://api.test/otherrepo"
    # Configure settings: enable push trigger handling, backlog disabled
    monkeypatch.setattr(
        github_app,
        "get_settings",
        lambda: SimpleNamespace(
            github_app=SimpleNamespace(
                handle_push_trigger=True,
                push_trigger_ignore_merge_commits=False,
                push_trigger_pending_tasks_backlog=False,
            )
        ),
    )
    # No-op apply_repo_settings
    monkeypatch.setattr(github_app, "apply_repo_settings", lambda url: None)

    # _check_pull_request_event must return a PR dict and api_url
    pull_request = {"merge_commit_sha": "deadbeef"}
    monkeypatch.setattr(github_app, "_check_pull_request_event", lambda action, body, ctx: (pull_request, api_url))

    # Provide a fake condition that does nothing
    class FakeCondition2:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return

        async def wait(self):
            return

        def notify(self, n=1):
            return

    fake_cond = FakeCondition2()
    # Ensure no active tasks initially
    github_app._duplicate_push_triggers.pop(api_url, None)
    github_app._pending_task_duplicate_push_conditions[api_url] = fake_cond

    # Identity provider: NOT_ELIGIBLE
    class FakeIdentityProvider2:
        def verify_eligibility(self, provider, sender_id, url):
            return Eligibility.NOT_ELIGIBLE

    monkeypatch.setattr(github_app, "get_identity_provider", lambda: FakeIdentityProvider2())

    # Track if perform_auto_commands called
    called = []

    async def fake_perform_auto_commands_github(commands_name, agent, body, url, log_context):
        called.append((commands_name, url, body, log_context))
        return {"result": "ok"}

    monkeypatch.setattr(github_app, "_perform_auto_commands_github", fake_perform_auto_commands_github)

    # Build body with before != after and after != merge_commit_sha
    body = {"before": "1111", "after": "2222"}
    agent = SimpleNamespace()  # dummy agent
    log_context = {}

    # Run the function
    result = await github_app.handle_push_trigger_for_new_commits(body, event="push", sender="bot", sender_id="100", action="synchronize", log_context=log_context, agent=agent)

    # Since eligibility is NOT_ELIGIBLE, perform_auto_commands should NOT have been called
    assert called == []
    # Duplicate counter should have been restored to 0 / not present
    assert github_app._duplicate_push_triggers.get(api_url, 0) == 0

    # Cleanup / restore
    monkeypatch.setattr(github_app, "get_settings", orig_get_settings)
    monkeypatch.setattr(github_app, "apply_repo_settings", orig_apply_repo_settings)
    monkeypatch.setattr(github_app, "_check_pull_request_event", orig_check)
    monkeypatch.setattr(github_app, "get_identity_provider", orig_get_identity_provider)
    if orig_perform is not None:
        monkeypatch.setattr(github_app, "_perform_auto_commands_github", orig_perform)
    else:
        delattr(github_app, "_perform_auto_commands_github")
    github_app._duplicate_push_triggers.clear()
    github_app._duplicate_push_triggers.update(orig_duplicate)
    github_app._pending_task_duplicate_push_conditions.clear()
    github_app._pending_task_duplicate_push_conditions.update(orig_pending)
