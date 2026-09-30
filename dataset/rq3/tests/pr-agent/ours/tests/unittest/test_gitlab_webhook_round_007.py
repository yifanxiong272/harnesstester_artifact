import asyncio
import copy
import json
import pytest

import pr_agent.servers.gitlab_webhook as gw


class DummySecretProvider:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_secret(self, token):
        return self.mapping.get(token)


class DummyBackgroundTasks:
    def __init__(self):
        self.added = []

    def add_task(self, func, *args, **kwargs):
        # store the callable and the args so tests can invoke it
        self.added.append((func, args, kwargs))


class FakeRequest:
    def __init__(self, json_obj, headers=None):
        self._json = json_obj
        self.headers = headers or {}

    async def json(self):
        return copy.deepcopy(self._json)


class DummyPRAgent:
    pass


@pytest.mark.asyncio
async def test_open_merge_request_round_007(monkeypatch):
    # Patch context to avoid dependency on starlette_context middleware
    monkeypatch.setattr(gw, "context", {})

    # Prepare: ensure module-level collaborators are patched
    # Provide a secret provider that returns a secret JSON containing gitlab_token
    monkeypatch.setattr(gw, "secret_provider", DummySecretProvider({"tok-A": json.dumps({"gitlab_token": "x", "token_name": "tname"})}))

    # Ensure get_settings includes a personal access token so flow continues
    monkeypatch.setattr(gw, "get_settings", lambda: {"GITLAB.PERSONAL_ACCESS_TOKEN": "pat-value"})

    # Replace PRAgent so we can identify it
    monkeypatch.setattr(gw, "PRAgent", DummyPRAgent)

    # Track calls to _perform_commands_gitlab
    called = {}

    async def fake_perform(commands_conf, agent, api_url, log_context, data):
        called['args'] = (commands_conf, type(agent), api_url, log_context, data)

    monkeypatch.setattr(gw, "_perform_commands_gitlab", fake_perform)

    # Replace log and helper predicates to deterministic values
    monkeypatch.setattr(gw, "get_logger", lambda: type("L", (), {"debug": lambda *a, **k: None, "info": lambda *a, **k: None, "warning": lambda *a, **k: None, "error": lambda *a, **k: None}))
    monkeypatch.setattr(gw, "is_bot_user", lambda data: False)
    monkeypatch.setattr(gw, "should_process_pr_logic", lambda data: True)
    monkeypatch.setattr(gw, "is_draft", lambda data: False)

    # Create an open merge request payload
    payload = {
        "object_kind": "merge_request",
        "user": {"username": "alice", "id": 1},
        "object_attributes": {"action": "open", "url": "http://gitlab/mr/1"}
    }

    req = FakeRequest(payload, headers={"X-Gitlab-Token": "tok-A"})
    bg = DummyBackgroundTasks()

    # Call the outer webhook handler which should register the inner task
    response = await gw.gitlab_webhook(bg, req)

    # Outer call always returns 200 success
    assert response.status_code == 200
    assert response.body is not None

    # There should be one background task registered: the inner
    assert len(bg.added) == 1
    inner_func, (inner_data,), _ = bg.added[0]

    # Call inner directly and await its execution
    result = await inner_func(inner_data)

    # For an open MR (not draft) _perform_commands_gitlab should have been invoked
    assert 'args' in called
    commands_conf, agent_type, api_url, log_ctx, passed_data = called['args']
    assert commands_conf == "pr_commands"
    # agent instance should be of our DummyPRAgent type
    assert agent_type is DummyPRAgent
    assert api_url == "http://gitlab/mr/1"
    assert passed_data["object_attributes"]["action"] == "open"


@pytest.mark.asyncio
async def test_update_push_disabled_round_007(monkeypatch):
    # Patch context to avoid dependency on starlette_context middleware
    monkeypatch.setattr(gw, "context", {})

    # Test the branch where an update event with oldrev exists but push handling is disabled
    monkeypatch.setattr(gw, "secret_provider", DummySecretProvider({"tok-B": json.dumps({"gitlab_token": "x"})}))
    # Provide settings that include PAT but have no push commands or handle_push_trigger False
    monkeypatch.setattr(gw, "get_settings", lambda: {"GITLAB.PERSONAL_ACCESS_TOKEN": "pat-value", "gitlab.push_commands": {}, "gitlab.handle_push_trigger": False})

    monkeypatch.setattr(gw, "get_logger", lambda: type("L", (), {"debug": lambda *a, **k: None, "info": lambda *a, **k: None, "warning": lambda *a, **k: None, "error": lambda *a, **k: None}))
    monkeypatch.setattr(gw, "is_bot_user", lambda data: False)
    monkeypatch.setattr(gw, "is_draft", lambda data: False)

    called = {"performed": False}

    async def fake_perform(*args, **kwargs):
        called["performed"] = True

    monkeypatch.setattr(gw, "_perform_commands_gitlab", fake_perform)

    payload = {
        "object_kind": "merge_request",
        "user": {"username": "bob", "id": 2},
        "object_attributes": {"action": "update", "oldrev": "abc123", "url": "http://gitlab/mr/2"}
    }

    req = FakeRequest(payload, headers={"X-Gitlab-Token": "tok-B"})
    bg = DummyBackgroundTasks()

    response = await gw.gitlab_webhook(bg, req)
    assert response.status_code == 200

    assert len(bg.added) == 1
    inner_func, (inner_data,), _ = bg.added[0]
    inner_response = await inner_func(inner_data)

    # When push handling is disabled, code returns a JSONResponse with success
    assert inner_response is not None
    assert getattr(inner_response, "status_code", 200) == 200
    # Ensure _perform_commands_gitlab was not invoked for push commands
    assert called["performed"] is False


@pytest.mark.asyncio
async def test_note_diff_ask_round_007(monkeypatch):
    # Patch context to avoid dependency on starlette_context middleware
    monkeypatch.setattr(gw, "context", {})

    # Test note event branch where a DiffNote containing '/ask' triggers handle_ask_line and handle_request
    monkeypatch.setattr(gw, "secret_provider", DummySecretProvider({"tok-C": json.dumps({"gitlab_token": "x"})}))

    # Ensure PAT exists
    monkeypatch.setattr(gw, "get_settings", lambda: {"GITLAB.PERSONAL_ACCESS_TOKEN": "pat-value"})

    # Provide a provider with side-effect for add_eyes_reaction
    class DummyProvider:
        def __init__(self):
            self.eyes = []

        def add_eyes_reaction(self, comment_id):
            self.eyes.append(comment_id)

    dummy_provider = DummyProvider()
    monkeypatch.setattr(gw, "get_git_provider_with_context", lambda pr_url: dummy_provider)

    # Replace handle_ask_line to modify the body predictably
    monkeypatch.setattr(gw, "handle_ask_line", lambda body, data: body.replace("/ask", "[ASK]"))

    # Track calls to handle_request and ensure notify lambda is exercised
    called = {}

    async def fake_handle_request(api_url, body, log_context, sender_id, notify=None):
        called['api_url'] = api_url
        called['body'] = body
        called['sender_id'] = sender_id
        # call notify to exercise the provider reaction path
        if notify:
            notify()

    monkeypatch.setattr(gw, "handle_request", fake_handle_request)

    monkeypatch.setattr(gw, "get_logger", lambda: type("L", (), {"debug": lambda *a, **k: None, "info": lambda *a, **k: None, "warning": lambda *a, **k: None, "error": lambda *a, **k: None}))
    monkeypatch.setattr(gw, "is_bot_user", lambda data: False)

    payload = {
        "object_kind": "note",
        "event_type": "note",
        "user": {"username": "carol", "id": 3},
        "merge_request": {"url": "http://gitlab/mr/3"},
        "object_attributes": {"id": 55, "type": "DiffNote", "note": "please /ask something"}
    }

    req = FakeRequest(payload, headers={"X-Gitlab-Token": "tok-C"})
    bg = DummyBackgroundTasks()

    response = await gw.gitlab_webhook(bg, req)
    assert response.status_code == 200

    assert len(bg.added) == 1
    inner_func, (inner_data,), _ = bg.added[0]
    inner_result = await inner_func(inner_data)

    # After invoking inner, our fake_handle_request should have been called with modified body;
    assert called.get('api_url') == "http://gitlab/mr/3"
    assert "[ASK]" in called.get('body')
    assert called.get('sender_id') == 3

    # Our dummy provider should have recorded the add_eyes_reaction call with comment id 55
    assert 55 in dummy_provider.eyes
