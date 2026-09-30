import asyncio
import json
import types
import pytest

import importlib

azure = importlib.import_module("pr_agent.servers.azuredevops_server_webhook")
from starlette.responses import JSONResponse

# All test functions/classes must end with _round_059

@pytest.mark.asyncio
async def test_pullrequest_created_round_059(monkeypatch):
    called = {}

    async def fake_perform_commands_azure(commands_conf, agent, api_url, log_context):
        # record the call for assertions
        called["args"] = (commands_conf, agent, api_url, dict(log_context))

    class FakePRAgent:
        def __init__(self):
            self.created = True

    # Patch the collaborators used by the code under test
    monkeypatch.setattr(azure, "_perform_commands_azure", fake_perform_commands_azure)
    monkeypatch.setattr(azure, "PRAgent", FakePRAgent)

    # Build input data matching the code's expectations for PR creation
    data = {
        "eventType": "git.pullrequest.created",
        "resource": {
            "_links": {
                "web": {
                    # include the substring that will be replaced by .replace in code
                    "href": "https://dev.azure.com/org/project/_apis/git/repositories/repo"
                }
            }
        }
    }
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    # Assert the patched command performer was invoked with expected args
    assert "args" in called, "_perform_commands_azure was not called"
    commands_conf, agent, api_url, recorded_log_ctx = called["args"]
    assert commands_conf == "pr_commands"
    assert isinstance(agent, FakePRAgent)
    # The module replaces '_apis/git/repositories' with '_git'
    assert "_git" in api_url and "_apis/git/repositories" not in api_url

    # log_context should have been populated
    assert log_context.get("event") == "git.pullrequest.created"
    assert log_context.get("api_url") == api_url

    # Response should be an accepted JSONResponse with success message
    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    body = response.body.decode() if isinstance(response.body, (bytes, bytearray)) else str(response.body)
    assert "webhook triggered successfully" in body


@pytest.mark.asyncio
async def test_comment_unsupported_command_round_059(monkeypatch):
    # Simulate comment event where available_commands_rgx.match returns falsy
    class DummyRegex:
        def match(self, _):
            return None

    monkeypatch.setattr(azure, "available_commands_rgx", DummyRegex())

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resource": {
            "comment": {"content": "not-a-command"}
        }
    }
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    # Unsupported command branch returns 400
    # Some versions of the code may return a JSONResponse or a tuple-wrapped JSONResponse; handle both
    if isinstance(response, tuple):
        resp = response[0]
    else:
        resp = response
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400
    body = resp.body.decode() if isinstance(resp.body, (bytes, bytearray)) else str(resp.body)
    assert "Unsupported command" in body


@pytest.mark.asyncio
async def test_comment_version1_round_059(monkeypatch):
    # available_commands_rgx.match returns truthy to reach version handling
    class TruthyRegex:
        def match(self, _):
            return True

    monkeypatch.setattr(azure, "available_commands_rgx", TruthyRegex())

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "1.0",
        "resource": {"comment": {"content": "/run"}}
    }
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    # The code returns a version-not-supported JSONResponse (might be wrapped)
    if isinstance(response, tuple):
        resp = response[0]
    else:
        resp = response
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400
    body = resp.body.decode() if isinstance(resp.body, (bytes, bytearray)) else str(resp.body)
    assert "version 1.0 webhook for Azure Devops PR comment is not supported" in body


@pytest.mark.asyncio
async def test_comment_v2_success_round_059(monkeypatch):
    # available_commands_rgx.match returns truthy and handle_request_comment succeeds
    class TruthyRegex:
        def match(self, _):
            return True

    recorded = {}

    async def fake_handle_request_comment(url, action, thread_id, comment_id, log_context):
        recorded["args"] = (url, action, thread_id, comment_id, dict(log_context))

    monkeypatch.setattr(azure, "available_commands_rgx", TruthyRegex())
    monkeypatch.setattr(azure, "handle_request_comment", fake_handle_request_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "/run",
                "_links": {"threads": {"href": "https://dev.azure.com/org/_apis/threads/777"}},
                "id": "55"
            },
            "pullRequest": {"repository": {"webUrl": "https://dev.azure.com/org/project"}, "pullRequestId": "42"}
        }
    }
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    # Ensure handle_request_comment was called with parsed ints and pr url
    assert "args" in recorded
    url, action, thread_id, comment_id, recorded_log_ctx = recorded["args"]
    assert action == "/run"
    assert thread_id == 777
    assert comment_id == 55
    # pr_url formation uses f'{repo}/pullrequest/{pullRequestId}'
    assert url.endswith("/pullrequest/42")

    # log_context should have event and api_url set by the function
    assert log_context.get("event") == "ms.vss-code.git-pullrequest-comment-event"
    assert log_context.get("api_url") == url

    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    body = response.body.decode() if isinstance(response.body, (bytes, bytearray)) else str(response.body)
    assert "webhook triggered successfully" in body


@pytest.mark.asyncio
async def test_comment_v2_exception_round_059(monkeypatch):
    # available_commands_rgx.match returns truthy and handle_request_comment raises -> 500
    class TruthyRegex:
        def match(self, _):
            return True

    async def raising_handle_request_comment(*args, **kwargs):
        raise RuntimeError("boom")

    logged = {}

    class FakeLogger:
        def error(self, msg):
            logged["msg"] = msg

    monkeypatch.setattr(azure, "available_commands_rgx", TruthyRegex())
    monkeypatch.setattr(azure, "handle_request_comment", raising_handle_request_comment)
    monkeypatch.setattr(azure, "get_logger", lambda: FakeLogger())

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "/run",
                "_links": {"threads": {"href": "https://dev.azure.com/org/_apis/threads/9"}},
                "id": "7"
            },
            "pullRequest": {"repository": {"webUrl": "https://dev.azure.com/org/project"}, "pullRequestId": "99"}
        }
    }
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    # The handler logs an error and returns a 500 JSONResponse
    assert "msg" in logged and "Azure DevOps Trigger failed. Error:" in logged["msg"]
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    body = response.body.decode() if isinstance(response.body, (bytes, bytearray)) else str(response.body)
    assert "Internal server error" in body


@pytest.mark.asyncio
async def test_unsupported_event_round_059(monkeypatch):
    # Event type that is not handled should return 204
    data = {"eventType": "something.else"}
    log_context = {}

    response = await azure.handle_request_azure(data, log_context)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 204
    body = response.body.decode() if isinstance(response.body, (bytes, bytearray)) else str(response.body)
    assert "Unsupported event" in body
