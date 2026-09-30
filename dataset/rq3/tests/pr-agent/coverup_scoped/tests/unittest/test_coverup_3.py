# file: pr_agent/servers/gitlab_webhook.py:170-276
# asked: {"lines": [172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 200, 201, 202, 203, 204, 205, 207, 208, 209, 212, 213, 215, 216, 218, 219, 220, 221, 222, 223, 224, 225, 226, 228, 231, 232, 233, 234, 235, 236, 239, 241, 242, 243, 244, 245, 246, 248, 249, 252, 253, 254, 257, 259, 260, 261, 262, 263, 264, 266, 267, 268, 269, 271, 273, 274, 275, 276], "branches": [[179, 180], [179, 194], [182, 183], [182, 186], [194, 195], [194, 200], [196, 197], [196, 202], [203, 204], [203, 207], [212, 213], [212, 215], [216, 218], [216, 259], [218, 219], [218, 220], [221, 222], [221, 231], [224, 225], [224, 228], [231, 232], [231, 252], [234, 235], [234, 239], [243, 244], [243, 248], [252, 0], [252, 253], [259, 0], [259, 260], [260, 0], [260, 261], [268, 269], [268, 271]]}
# gained: {"lines": [172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 202, 203, 207, 208, 209, 212, 215, 216, 259, 260, 261, 262, 263, 264, 266, 267, 268, 269, 271, 273, 274, 275, 276], "branches": [[179, 180], [182, 183], [182, 186], [203, 207], [212, 215], [216, 259], [259, 260], [260, 261], [268, 269]]}

import asyncio
import json
import pytest

from types import SimpleNamespace

import pr_agent.servers.gitlab_webhook as gw


class DummyRequest:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}

    async def json(self):
        return self._payload


class DummyBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, coro_func, *args, **kwargs):
        # Schedule the coroutine to run on the event loop immediately
        task = asyncio.create_task(coro_func(*args, **kwargs))
        self.tasks.append(task)


@pytest.mark.asyncio
async def test_note_comment_with_diffnote_ask_triggers_notify_and_add_eyes(monkeypatch):
    called = {}

    # Provide a simple context dict to replace starlette_context.context
    monkeypatch.setattr(gw, "context", {})

    # Provide a simple global_settings object with .gitlab.personal_access_token attribute
    monkeypatch.setattr(gw, "global_settings", SimpleNamespace(gitlab=SimpleNamespace(personal_access_token=None)))

    # Mock secret_provider to return a valid JSON secret
    class SecretProvider:
        def get_secret(self, token):
            return json.dumps({"gitlab_token": "fake_token", "token_name": "tn"})

    monkeypatch.setattr(gw, "secret_provider", SecretProvider())

    # get_settings should return a mapping with PERSONAL_ACCESS_TOKEN present
    monkeypatch.setattr(gw, "get_settings", lambda: {"GITLAB.PERSONAL_ACCESS_TOKEN": "personal", "gitlab.push_commands": {}, "gitlab.handle_push_trigger": False})

    # Mock is_bot_user to ensure we do not exit early
    monkeypatch.setattr(gw, "is_bot_user", lambda data: False)

    # Mock logger so calls are no-ops
    class DummyLogger:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass

    monkeypatch.setattr(gw, "get_logger", lambda: DummyLogger())

    # Provider that records add_eyes_reaction calls
    class Provider:
        def __init__(self):
            self.added = []

        def add_eyes_reaction(self, comment_id):
            self.added.append(comment_id)

    provider = Provider()
    monkeypatch.setattr(gw, "get_git_provider_with_context", lambda pr_url=None: provider)

    # handle_ask_line should transform the body (simulate being called)
    monkeypatch.setattr(gw, "handle_ask_line", lambda body, data: body.replace("/ask", "").strip())

    # handle_request should be awaited; it should call notify
    async def fake_handle_request(url, body, log_context, sender_id, notify=None):
        called["handle_request_args"] = {"url": url, "body": body, "sender_id": sender_id}
        # call notify to trigger provider.add_eyes_reaction
        if notify:
            notify()
        return "handled"

    monkeypatch.setattr(gw, "handle_request", fake_handle_request)

    # build payload for a note on a merge request, DiffNote with '/ask' in body
    payload = {
        "object_kind": "note",
        "event_type": "note",
        "user": {"username": "alice", "id": 123},
        "merge_request": {"url": "http://gitlab/mr/1"},
        "object_attributes": {"id": 999, "note": "Please /ask this line", "type": "DiffNote"},
    }

    req = DummyRequest(payload, headers={"X-Gitlab-Token": "sometoken"})
    bg = DummyBackgroundTasks()

    resp = await gw.gitlab_webhook(bg, req)

    # outer response should be 200 OK
    assert resp.status_code == 200

    # wait for background tasks to finish
    assert bg.tasks, "Expected background task to be scheduled"
    results = await asyncio.gather(*bg.tasks)

    # Confirm provider.added was called with the comment id
    assert provider.added == [999]
    # Confirm handle_request was called with expected transformed body
    assert called["handle_request_args"]["url"] == "http://gitlab/mr/1"
    assert "Please" in called["handle_request_args"]["body"]


@pytest.mark.asyncio
async def test_secret_provider_returns_none_results_in_unauthorized_background_response(monkeypatch):
    # Provide a simple context dict to replace starlette_context.context
    monkeypatch.setattr(gw, "context", {})

    # Provide a simple global_settings object
    monkeypatch.setattr(gw, "global_settings", SimpleNamespace(gitlab=SimpleNamespace(personal_access_token=None)))

    # secret_provider exists but returns None (empty secret)
    class SecretProviderNone:
        def get_secret(self, token):
            return None

    monkeypatch.setattr(gw, "secret_provider", SecretProviderNone())

    # Ensure get_settings still has PERSONAL_ACCESS_TOKEN (not reached), but present to avoid other branches
    monkeypatch.setattr(gw, "get_settings", lambda: {"GITLAB.PERSONAL_ACCESS_TOKEN": "personal"})

    # logger no-op
    class DummyLogger:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass

    monkeypatch.setattr(gw, "get_logger", lambda: DummyLogger())

    # is_bot_user should not be called but set to False to be safe
    monkeypatch.setattr(gw, "is_bot_user", lambda data: False)

    payload = {"some": "data"}

    req = DummyRequest(payload, headers={"X-Gitlab-Token": "token-id"})
    bg = DummyBackgroundTasks()

    resp = await gw.gitlab_webhook(bg, req)

    # outer response still 200
    assert resp.status_code == 200

    # background task should have been scheduled and when awaited, should return a JSONResponse with 401
    assert bg.tasks, "Expected background task to be scheduled"
    results = await asyncio.gather(*bg.tasks)

    # The inner returned a JSONResponse with 401 Unauthorized
    inner_result = results[0]
    assert hasattr(inner_result, "status_code")
    assert inner_result.status_code == 401
