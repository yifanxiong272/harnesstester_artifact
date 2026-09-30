# file: pr_agent/servers/github_app.py:312-358
# asked: {"lines": [320, 321, 322, 323, 324, 325, 326, 329, 330, 331, 332, 333, 334, 335, 337, 339, 341, 342, 343, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 357, 358], "branches": [[322, 323], [322, 325], [329, 330], [329, 332], [332, 333], [332, 337], [333, 334], [333, 337], [337, 339], [337, 341], [341, 342], [341, 345], [345, 346], [345, 348], [348, 349], [348, 351], [351, 352], [351, 353], [353, 354], [353, 357], [354, 355], [354, 358]]}
# gained: {"lines": [320, 321, 322, 323, 324, 325, 326, 329, 330, 331, 332, 333, 334, 335, 337, 339, 341, 342, 343, 345, 346, 347, 348, 351, 352, 353, 354, 355, 358], "branches": [[322, 323], [322, 325], [329, 330], [329, 332], [332, 333], [332, 337], [333, 334], [333, 337], [337, 339], [337, 341], [341, 342], [341, 345], [345, 346], [345, 348], [348, 351], [351, 352], [351, 353], [353, 354], [354, 355], [354, 358]]}

import pytest
import asyncio

MODULE = "pr_agent.servers.github_app"


class FakeLogger:
    def __init__(self):
        self.debug_calls = []
        self.info_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))


class FakePRAgent:
    def __init__(self, *args, **kwargs):
        self.created = True


@pytest.mark.asyncio
async def test_handle_request_no_action(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)

    from pr_agent.servers import github_app
    result = await github_app.handle_request({}, event="pull_request")

    assert result == {}
    assert any("No action found in request body" in args[0] for args, _ in fake_logger.debug_calls)


@pytest.mark.asyncio
async def test_handle_request_ignored_bot_user(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "bot"}, 123, "Bot")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)

    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: True)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    from pr_agent.servers import github_app
    body = {"action": "opened"}
    result = await github_app.handle_request(body, event="pull_request")

    assert result == {}
    assert any("bot user detected" in args[0] for args, _ in fake_logger.debug_calls)


@pytest.mark.asyncio
async def test_handle_request_filtered_by_pr_logic(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "human"}, 456, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)

    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: False)

    from pr_agent.servers import github_app
    body = {"action": "synchronize"}
    result = await github_app.handle_request(body, event="pull_request")

    assert result == {}
    assert any("PR logic filtering" in args[0] for args, _ in fake_logger.debug_calls)


@pytest.mark.asyncio
async def test_handle_request_check_run_branch(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "human"}, 1, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)
    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    from pr_agent.servers import github_app
    body = {"action": "completed", "check_run": {"status": "completed"}}
    result = await github_app.handle_request(body, event="pull_request")
    assert result == {}
    assert any("Handling request with event" in args[0] for args, _ in fake_logger.debug_calls)


@pytest.mark.asyncio
async def test_handle_request_created_calls_handle_comments_on_pr(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    stub_calls = {}

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "alice"}, 77, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)
    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    async def fake_handle_comments_on_pr(body, event, sender, sender_id, action, log_context, agent):
        stub_calls['called'] = ("comments", body, event, sender, sender_id, action, log_context)
    monkeypatch.setattr(f"{MODULE}.handle_comments_on_pr", fake_handle_comments_on_pr)

    from pr_agent.servers import github_app
    body = {"action": "created"}
    result = await github_app.handle_request(body, event="issue_comment")
    assert result == {}
    assert stub_calls.get('called') is not None
    assert stub_calls['called'][0] == "comments"
    assert stub_calls['called'][5] == "created"


@pytest.mark.asyncio
async def test_handle_request_new_pr_opened(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    called = {}

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "bob"}, 88, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)
    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    async def fake_handle_new_pr_opened(body, event, sender, sender_id, action, log_context, agent):
        called['new_pr'] = (body, event, sender, sender_id, action)

    monkeypatch.setattr(f"{MODULE}.handle_new_pr_opened", fake_handle_new_pr_opened)

    from pr_agent.servers import github_app
    body = {"action": "opened"}
    result = await github_app.handle_request(body, event="pull_request")
    assert result == {}
    assert 'new_pr' in called
    assert called['new_pr'][4] == "opened"


@pytest.mark.asyncio
async def test_handle_request_synchronize_calls_push_trigger(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    called = {}

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "carl"}, 99, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)
    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    async def fake_handle_push_trigger_for_new_commits(body, event, sender, sender_id, action, log_context, agent):
        called['push'] = (body, event, sender, sender_id, action)

    monkeypatch.setattr(f"{MODULE}.handle_push_trigger_for_new_commits", fake_handle_push_trigger_for_new_commits)

    from pr_agent.servers import github_app
    body = {"action": "synchronize"}
    result = await github_app.handle_request(body, event="pull_request")
    assert result == {}
    assert 'push' in called
    assert called['push'][4] == "synchronize"


@pytest.mark.asyncio
async def test_handle_request_closed_with_and_without_analytics(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(f"{MODULE}.get_logger", lambda: fake_logger)
    monkeypatch.setattr(f"{MODULE}.PRAgent", FakePRAgent)

    def fake_get_log_context(body, event, action, build_number):
        return ({"ctx": True}, {"login": "dana"}, 101, "User")
    monkeypatch.setattr(f"{MODULE}.get_log_context", fake_get_log_context)
    monkeypatch.setattr(f"{MODULE}.is_bot_user", lambda sender, sender_type: False)
    monkeypatch.setattr(f"{MODULE}.should_process_pr_logic", lambda body: True)

    closed_called = {}

    def fake_handle_closed_pr(body, event, action, log_context):
        closed_called['called'] = (body, event, action, log_context)
    monkeypatch.setattr(f"{MODULE}.handle_closed_pr", fake_handle_closed_pr)

    class FakeSettings1(dict):
        def get(self, k, default=None):
            if k == "CONFIG.ANALYTICS_FOLDER":
                return "some/path"
            return super().get(k, default)
    monkeypatch.setattr(f"{MODULE}.get_settings", lambda: FakeSettings1())

    from pr_agent.servers import github_app
    body = {"action": "closed"}
    result = await github_app.handle_request(body, event="pull_request")
    assert result == {}
    assert 'called' in closed_called
    assert closed_called['called'][2] == "closed"

    closed_called.clear()
    class FakeSettings2(dict):
        def get(self, k, default=None):
            if k == "CONFIG.ANALYTICS_FOLDER":
                return ""
            return super().get(k, default)
    monkeypatch.setattr(f"{MODULE}.get_settings", lambda: FakeSettings2())

    monkeypatch.setattr(f"{MODULE}.handle_closed_pr", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Should not call handle_closed_pr")))

    result = await github_app.handle_request(body, event="pull_request")
    assert result == {}
