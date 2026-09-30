# file: pr_agent/servers/azuredevops_server_webhook.py:118-169
# asked: {"lines": [118, 119, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 144, 146, 148, 151, 153, 156, 157, 159, 160, 161, 162, 163, 165, 167, 168], "branches": [[119, 121], [119, 129], [129, 130], [129, 151], [131, 132], [131, 146], [132, 133], [132, 142]]}
# gained: {"lines": [118, 119, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 144, 146, 148, 151, 153, 156, 157, 159, 160, 161, 162, 163, 165, 167, 168], "branches": [[119, 121], [119, 129], [129, 130], [129, 151], [131, 132], [131, 146], [132, 133], [132, 142]]}

import asyncio
import json

import pytest

from pr_agent.servers import azuredevops_server_webhook as webhook


def _normalize_response(resp):
    # Some branches in the source return a tuple containing the JSONResponse.
    if isinstance(resp, tuple):
        return resp[0]
    return resp


def _parse_response_body(resp):
    raw = resp.body.decode()
    parsed = json.loads(raw)
    # Some branches double-encode with json.dumps before passing to JSONResponse,
    # which results in a JSON string inside the response body. Handle that.
    if isinstance(parsed, str):
        parsed = json.loads(parsed)
    return parsed


@pytest.mark.asyncio
async def test_pullrequest_created_triggers_perform_commands(monkeypatch):
    called = {}

    async def fake_perform_commands_azure(name, pr_agent, pr_url, log_context):
        called['args'] = (name, pr_agent, pr_url, dict(log_context))
        # simulate some async work
        await asyncio.sleep(0)

    monkeypatch.setattr(webhook, "_perform_commands_azure", fake_perform_commands_azure)

    data = {
        "eventType": "git.pullrequest.created",
        "resource": {
            "_links": {
                "web": {"href": "https://dev.azure.com/org/_apis/git/repositories/repoId"}
            }
        },
    }
    log_context = {}

    resp = await webhook.handle_request_azure(data, log_context)
    resp = _normalize_response(resp)

    assert resp.status_code == 202
    body = _parse_response_body(resp)
    assert body["message"] == "webhook triggered successfully"
    # ensure perform commands was called and pr_url was transformed
    assert "args" in called
    name, pr_agent, pr_url, lc = called["args"]
    assert name == "pr_commands"
    assert "_git" in pr_url  # replaced _apis/... with _git
    assert lc["event"] == "git.pullrequest.created"
    assert lc["api_url"] == pr_url


@pytest.mark.asyncio
async def test_comment_event_version_2_calls_handle_request_comment(monkeypatch):
    # prepare match object
    class MatchAll:
        def match(self, _):
            return True

    monkeypatch.setattr(webhook, "available_commands_rgx", MatchAll())

    called = {}

    async def fake_handle_request_comment(pr_url, action, thread_id, comment_id, log_context):
        called['args'] = (pr_url, action, thread_id, comment_id, dict(log_context))
        await asyncio.sleep(0)

    monkeypatch.setattr(webhook, "handle_request_comment", fake_handle_request_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "/run-tests",
                "id": "123",
                "_links": {"threads": {"href": "https://dev.azure.com/.../threads/42"}},
            },
            "pullRequest": {
                "pullRequestId": 7,
                "repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo"},
            },
        },
    }
    log_context = {}

    resp = await webhook.handle_request_azure(data, log_context)
    resp = _normalize_response(resp)

    assert resp.status_code == 202
    body = _parse_response_body(resp)
    assert body["message"] == "webhook triggered successfully"

    assert "args" in called
    pr_url, action, thread_id, comment_id, lc = called["args"]
    assert pr_url.endswith("/pullrequest/7")
    assert action == "/run-tests"
    assert thread_id == 42
    assert comment_id == 123
    assert lc["event"] == data["eventType"]
    assert lc["api_url"] == pr_url


@pytest.mark.asyncio
async def test_comment_event_handle_request_comment_exception_returns_500_and_logs(monkeypatch):
    class MatchAll:
        def match(self, _):
            return True

    monkeypatch.setattr(webhook, "available_commands_rgx", MatchAll())

    async def fake_handle_request_comment(pr_url, action, thread_id, comment_id, log_context):
        raise RuntimeError("boom")

    monkeypatch.setattr(webhook, "handle_request_comment", fake_handle_request_comment)

    logged = {}

    class FakeLogger:
        def error(self, msg):
            logged['error'] = msg

    monkeypatch.setattr(webhook, "get_logger", lambda: FakeLogger())

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "/do-something",
                "id": "9",
                "_links": {"threads": {"href": "https://dev.azure.com/.../threads/5"}},
            },
            "pullRequest": {
                "pullRequestId": 33,
                "repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo2"},
            },
        },
    }
    log_context = {}

    resp = await webhook.handle_request_azure(data, log_context)
    resp = _normalize_response(resp)

    assert resp.status_code == 500
    body = _parse_response_body(resp)
    assert body["message"] == "Internal server error"
    assert "Azure DevOps Trigger failed. Error:boom" in logged.get('error', '')


@pytest.mark.asyncio
async def test_comment_event_version_1_returns_400_and_unsupported_command_and_unsupported_event(monkeypatch):
    # Case: version 1 should return the version-not-supported message when command matches
    class MatchAll:
        def match(self, _):
            return True

    monkeypatch.setattr(webhook, "available_commands_rgx", MatchAll())

    data_v1 = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "1.0",
        "resource": {
            "comment": {
                "content": "/anything",
                "id": "1",
                "_links": {"threads": {"href": "https://dev.azure.com/.../threads/1"}},
            },
            "pullRequest": {
                "pullRequestId": 1,
                "repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo"},
            },
        },
    }
    resp = await webhook.handle_request_azure(data_v1, {})
    resp = _normalize_response(resp)
    assert resp.status_code == 400
    body = _parse_response_body(resp)
    assert "version 1.0 webhook for Azure Devops PR comment is not supported" in body["message"]

    # Case: command not supported should return Unsupported command
    class MatchNone:
        def match(self, _):
            return False

    monkeypatch.setattr(webhook, "available_commands_rgx", MatchNone())

    data_bad_command = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "/unknown-command",
                "id": "2",
                "_links": {"threads": {"href": "https://dev.azure.com/.../threads/2"}},
            },
        },
    }
    resp2 = await webhook.handle_request_azure(data_bad_command, {})
    resp2 = _normalize_response(resp2)
    assert resp2.status_code == 400
    body2 = _parse_response_body(resp2)
    assert "Unsupported command" in body2["message"]

    # Case: unsupported event returns 204
    data_unsupported = {"eventType": "something.else", "resource": {}}
    resp3 = await webhook.handle_request_azure(data_unsupported, {})
    resp3 = _normalize_response(resp3)
    assert resp3.status_code == 204
    body3 = _parse_response_body(resp3)
    assert "Unsupported event" in body3["message"]
