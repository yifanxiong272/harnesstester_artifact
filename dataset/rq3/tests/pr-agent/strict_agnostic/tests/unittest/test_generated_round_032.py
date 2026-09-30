import pytest
import types

import pr_agent.servers.github_app as ga

class DummyAgent:
    pass

class DummyLogger:
    def __init__(self):
        self.last_debug = None
        self.last_info = None
        self.debug_calls = []
        self.info_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))
        self.last_debug = args

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))
        self.last_info = args


@pytest.mark.asyncio
async def test_no_action_round_032(monkeypatch):
    # No action in body -> early return {} (cover 320-325)
    body = {}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 1, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    # Make sure other handlers would error if called - to ensure they are not called
    async def fail_if_called(*a, **k):
        raise AssertionError("handler should not be called")
    monkeypatch.setattr(ga, "handle_comments_on_pr", fail_if_called)
    monkeypatch.setattr(ga, "handle_new_pr_opened", fail_if_called)
    monkeypatch.setattr(ga, "handle_push_trigger_for_new_commits", fail_if_called)
    monkeypatch.setattr(ga, "handle_closed_pr", lambda *a, **k: (_ for _ in ()).throw(AssertionError("closed handler called")))

    res = await ga.handle_request(body, "pull_request")
    assert res == {}


@pytest.mark.asyncio
async def test_bot_user_ignored_round_032(monkeypatch):
    # is_bot_user True and no 'check_run' in body -> ignored
    body = {"action": "opened"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "bot", 2, "Bot"))
    monkeypatch.setattr(ga, "is_bot_user", lambda sender, sender_type: True)

    called = {}
    async def fail_if_called(*a, **k):
        called['error'] = True
        raise AssertionError("should not call handlers for bot user")

    monkeypatch.setattr(ga, "handle_comments_on_pr", fail_if_called)
    monkeypatch.setattr(ga, "handle_new_pr_opened", fail_if_called)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert 'error' not in called


@pytest.mark.asyncio
async def test_should_process_pr_logic_filtered_round_032(monkeypatch):
    # action != 'created' and should_process_pr_logic returns False -> ignored
    body = {"action": "opened"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 3, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: False)

    # handlers should not be invoked
    called = {"h": False}
    async def mark_called(*a, **k):
        called['h'] = True

    monkeypatch.setattr(ga, "handle_new_pr_opened", mark_called)
    monkeypatch.setattr(ga, "handle_comments_on_pr", mark_called)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert called['h'] is False


@pytest.mark.asyncio
async def test_check_run_present_round_032(monkeypatch):
    # 'check_run' in body should follow check_run branch (line 337->339 pass) and return {}
    body = {"action": "any", "check_run": {"status": "failure"}}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 4, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)

    called = {"called": False}
    async def fail_if_called(*a, **k):
        called['called'] = True
        raise AssertionError("No handlers should be invoked for check_run branch in this test")

    monkeypatch.setattr(ga, "handle_comments_on_pr", fail_if_called)
    monkeypatch.setattr(ga, "handle_new_pr_opened", fail_if_called)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert called['called'] is False


@pytest.mark.asyncio
async def test_handle_comments_created_round_032(monkeypatch):
    # action == 'created' -> should call handle_comments_on_pr
    body = {"action": "created"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 5, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)

    called = {}
    async def fake_comments(body_arg, event, sender, sender_id, action, log_context, agent):
        called['args'] = (body_arg.get('action'), event, sender, sender_id, action)

    monkeypatch.setattr(ga, "handle_comments_on_pr", fake_comments)

    res = await ga.handle_request(body, "issue_comment")
    assert res == {}
    # ensure handle_comments_on_pr was awaited and called with action 'created'
    assert called.get('args')[0] == 'created'


@pytest.mark.asyncio
async def test_new_pr_opened_round_032(monkeypatch):
    # event == 'pull_request' and action opened (not synchronize/closed) -> handle_new_pr_opened called
    body = {"action": "opened"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 6, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: True)

    called = {}
    async def fake_new_pr(body_arg, event, sender, sender_id, action, log_context, agent):
        called['called'] = (event, action)

    monkeypatch.setattr(ga, "handle_new_pr_opened", fake_new_pr)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert called.get('called') == ("pull_request", "opened")


@pytest.mark.asyncio
async def test_issue_comment_edited_round_032(monkeypatch):
    # event == 'issue_comment' and 'edited' in action -> triggers that branch (lines 348-349 pass)
    body = {"action": "something_edited"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 7, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: True)

    # Nothing should be called; ensure no unexpected handler called
    called = {}
    async def fail_if_called(*a, **k):
        called['err'] = True
        raise AssertionError("handler should not be called for edited issue_comment pass branch")

    monkeypatch.setattr(ga, "handle_comments_on_pr", fail_if_called)
    monkeypatch.setattr(ga, "handle_new_pr_opened", fail_if_called)

    res = await ga.handle_request(body, "issue_comment")
    assert res == {}
    assert 'err' not in called


@pytest.mark.asyncio
async def test_pull_request_synchronize_round_032(monkeypatch):
    # event == 'pull_request' and action == 'synchronize' -> handle_push_trigger_for_new_commits called
    body = {"action": "synchronize"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 8, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: True)

    called = {}
    async def fake_push(body_arg, event, sender, sender_id, action, log_context, agent):
        called['called'] = (event, action)

    monkeypatch.setattr(ga, "handle_push_trigger_for_new_commits", fake_push)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert called.get('called') == ("pull_request", "synchronize")


@pytest.mark.asyncio
async def test_pull_request_closed_with_analytics_round_032(monkeypatch):
    # event == 'pull_request' and action == 'closed' and get_settings().get("CONFIG.ANALYTICS_FOLDER") is truthy -> handle_closed_pr called
    body = {"action": "closed"}
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 9, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: True)

    class SettingsObj(dict):
        def get(self, k, default=None):
            if k == "CONFIG.ANALYTICS_FOLDER":
                return "/tmp"
            return super().get(k, default)

    monkeypatch.setattr(ga, "get_settings", lambda: SettingsObj())

    called = {}
    def fake_closed(body_arg, event, action, log_context):
        called['closed'] = (event, action)

    monkeypatch.setattr(ga, "handle_closed_pr", fake_closed)

    res = await ga.handle_request(body, "pull_request")
    assert res == {}
    assert called.get('closed') == ("pull_request", "closed")


@pytest.mark.asyncio
async def test_unhandled_event_round_032(monkeypatch):
    # An event/action that falls into the final else -> logs info and returns {}
    body = {"action": "some_other_action"}
    logger = DummyLogger()
    monkeypatch.setattr(ga, "PRAgent", lambda: DummyAgent())
    monkeypatch.setattr(ga, "get_log_context", lambda *a, **k: ({}, "sender", 10, "User"))
    monkeypatch.setattr(ga, "is_bot_user", lambda *a, **k: False)
    monkeypatch.setattr(ga, "should_process_pr_logic", lambda b: True)
    monkeypatch.setattr(ga, "get_logger", lambda: logger)

    res = await ga.handle_request(body, "fork")
    assert res == {}
    # ensure info was called at least once indicating the else branch
    assert len(logger.info_calls) >= 1
