import pytest

import pr_agent.servers.github_app as github_app


class DummySettings:
    def __init__(self, mapping=None):
        self._m = mapping or {}

    def get(self, key, default=None):
        return self._m.get(key, default)


class DummyLogger:
    def debug(self, *_, **__):
        pass

    def info(self, *_, **__):
        pass

    def error(self, *_, **__):
        pass


@pytest.mark.asyncio
async def test_no_action_round_032(monkeypatch):
    """When body has no 'action' expect early return {}"""
    # Patch logger so debug calls are harmless
    monkeypatch.setattr(github_app, 'get_logger', lambda: DummyLogger())

    body = {"some": "payload"}
    res = await github_app.handle_request(body, event="pull_request")
    assert res == {}


@pytest.mark.asyncio
async def test_bot_user_ignored_round_032(monkeypatch):
    """If is_bot_user returns True and no 'check_run' in body, handle_request returns {}"""
    monkeypatch.setattr(github_app, 'get_logger', lambda: DummyLogger())

    # Ensure PRAgent construction does not require heavy deps
    class DummyAgent:
        pass

    monkeypatch.setattr(github_app, 'PRAgent', DummyAgent)

    # get_log_context still must return 4 values
    monkeypatch.setattr(github_app, 'get_log_context', lambda body, event, action, build_number: ({}, 'bot-name', 'id-bot', 'Bot'))

    # Simulate bot detection
    monkeypatch.setattr(github_app, 'is_bot_user', lambda sender, sender_type: True)

    body = {"action": "opened"}
    res = await github_app.handle_request(body, event="pull_request")
    assert res == {}


@pytest.mark.asyncio
async def test_pr_logic_filtered_round_032(monkeypatch):
    """When action != 'created' and should_process_pr_logic returns False, expect early return {}"""
    monkeypatch.setattr(github_app, 'get_logger', lambda: DummyLogger())

    class DummyAgent:
        pass

    monkeypatch.setattr(github_app, 'PRAgent', DummyAgent)
    monkeypatch.setattr(github_app, 'get_log_context', lambda body, event, action, build_number: ({}, 'alice', 'id1', 'User'))
    monkeypatch.setattr(github_app, 'is_bot_user', lambda sender, sender_type: False)
    monkeypatch.setattr(github_app, 'should_process_pr_logic', lambda body: False)

    body = {"action": "edited"}
    res = await github_app.handle_request(body, event="pull_request")
    assert res == {}


@pytest.mark.asyncio
async def test_handle_comments_created_round_032(monkeypatch):
    """When action == 'created' expect handle_comments_on_pr to be awaited with preserved payload shape"""
    monkeypatch.setattr(github_app, 'get_logger', lambda: DummyLogger())

    class DummyAgent:
        pass

    monkeypatch.setattr(github_app, 'PRAgent', DummyAgent)
    monkeypatch.setattr(github_app, 'get_log_context', lambda body, event, action, build_number: ({'ctx': True}, 'commenter', 'cid', 'User'))
    monkeypatch.setattr(github_app, 'is_bot_user', lambda sender, sender_type: False)

    called = {}

    async def fake_handle_comments_on_pr(body, event, sender, sender_id, action, log_context, agent):
        # preserve payload shapes and record call
        called['args'] = (body, event, sender, sender_id, action, log_context, isinstance(agent, DummyAgent))
        return {"ok": True}

    monkeypatch.setattr(github_app, 'handle_comments_on_pr', fake_handle_comments_on_pr)

    body = {"action": "created", "comment": {"body": "Looks good"}}
    res = await github_app.handle_request(body, event="issue_comment")
    assert res == {}
    assert 'args' in called
    recorded = called['args']
    assert recorded[0] is body
    assert recorded[1] == "issue_comment"
    assert recorded[4] == "created"
    assert recorded[5] == {'ctx': True}
    assert recorded[6] is True


@pytest.mark.asyncio
async def test_new_pr_opened_and_push_sync_and_closed_round_032(monkeypatch):
    """
    Multiple validations:
    - event 'pull_request' and action 'opened' should await handle_new_pr_opened
    - event 'pull_request' and action 'synchronize' should await handle_push_trigger_for_new_commits
    - event 'pull_request' and action 'closed' should call handle_closed_pr when analytics folder set
    """
    monkeypatch.setattr(github_app, 'get_logger', lambda: DummyLogger())

    class DummyAgent:
        pass

    monkeypatch.setattr(github_app, 'PRAgent', DummyAgent)
    monkeypatch.setattr(github_app, 'get_log_context', lambda body, event, action, build_number: ({'ctx': True}, 'sender', 'sid', 'User'))
    monkeypatch.setattr(github_app, 'is_bot_user', lambda sender, sender_type: False)
    # allow PR logic to pass for opened/synchronize/closed
    monkeypatch.setattr(github_app, 'should_process_pr_logic', lambda body: True)

    calls = {}

    async def fake_new_pr(body, event, sender, sender_id, action, log_context, agent):
        calls['new_pr'] = (body, event, sender, sender_id, action, log_context, isinstance(agent, DummyAgent))

    async def fake_push_trigger(body, event, sender, sender_id, action, log_context, agent):
        calls['push_trigger'] = (body, event, sender, sender_id, action, log_context, isinstance(agent, DummyAgent))

    def fake_handle_closed_pr(body, event, action, log_context):
        calls['closed'] = (body, event, action, log_context)

    monkeypatch.setattr(github_app, 'handle_new_pr_opened', fake_new_pr)
    monkeypatch.setattr(github_app, 'handle_push_trigger_for_new_commits', fake_push_trigger)
    monkeypatch.setattr(github_app, 'handle_closed_pr', fake_handle_closed_pr)

    # Ensure get_settings().get("CONFIG.ANALYTICS_FOLDER", "") returns non-empty when needed
    monkeypatch.setattr(github_app, 'get_settings', lambda: DummySettings({"CONFIG.ANALYTICS_FOLDER": "/tmp/analytics"}))

    # 1) opened
    body_opened = {"action": "opened"}
    res1 = await github_app.handle_request(body_opened, event="pull_request")
    assert res1 == {}
    assert 'new_pr' in calls
    assert calls['new_pr'][1] == 'pull_request'
    assert calls['new_pr'][4] == 'opened'

    # 2) synchronize
    body_sync = {"action": "synchronize"}
    res2 = await github_app.handle_request(body_sync, event="pull_request")
    assert res2 == {}
    assert 'push_trigger' in calls
    assert calls['push_trigger'][4] == 'synchronize'

    # 3) closed triggers handle_closed_pr when analytics folder is present
    body_closed = {"action": "closed"}
    res3 = await github_app.handle_request(body_closed, event="pull_request")
    assert res3 == {}
    assert 'closed' in calls
    assert calls['closed'][2] == 'closed'
