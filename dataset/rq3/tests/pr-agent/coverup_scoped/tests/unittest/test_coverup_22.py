# file: pr_agent/servers/azuredevops_server_webhook.py:118-169
# asked: {"lines": [118, 119, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 144, 146, 148, 151, 153, 156, 157, 159, 160, 161, 162, 163, 165, 167, 168], "branches": [[119, 121], [119, 129], [129, 130], [129, 151], [131, 132], [131, 146], [132, 133], [132, 142]]}
# gained: {"lines": [118, 119, 121, 122, 123, 124, 125, 127, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 144, 146, 148, 151, 153, 156, 157, 159, 160, 161, 162, 163, 165, 167, 168], "branches": [[119, 121], [119, 129], [129, 130], [129, 151], [131, 132], [131, 146], [132, 133], [132, 142]]}

import json
import pytest
from types import SimpleNamespace

import pr_agent.servers.azuredevops_server_webhook as az


@pytest.mark.asyncio
async def test_pullrequest_created_calls_perform(monkeypatch):
    called = {}

    async def fake_perform_commands_azure(name, agent, pr_url, log_context):
        called['name'] = name
        called['agent_type'] = type(agent).__name__
        called['pr_url'] = pr_url
        called['log_context'] = dict(log_context)

    class DummyPRAgent:
        pass

    monkeypatch.setattr(az, "_perform_commands_azure", fake_perform_commands_azure)
    monkeypatch.setattr(az, "PRAgent", DummyPRAgent)

    href = "https://dev.azure.com/org/_apis/git/repositories/repoId"
    data = {"eventType": "git.pullrequest.created", "resource": {"_links": {"web": {"href": href}}}}
    log_context = {}

    resp = await az.handle_request_azure(data, log_context)

    assert called["name"] == "pr_commands"
    assert called["agent_type"] == "DummyPRAgent"
    # pr_url should be href with replacement of _apis/git/repositories -> _git
    assert "_git" in called["pr_url"]
    assert log_context["event"] == "git.pullrequest.created"
    assert log_context["api_url"] == called["pr_url"]

    assert hasattr(resp, "status_code")
    assert resp.status_code == 202
    body = json.loads(resp.body.decode())
    assert body["message"] == "webhook triggered successfully"


@pytest.mark.asyncio
async def test_comment_event_unsupported_command(monkeypatch):
    # available_commands_rgx.match should return None -> Unsupported command 400
    monkeypatch.setattr(az, "available_commands_rgx", SimpleNamespace(match=lambda s: None))

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resource": {
            "comment": {"content": "nope"},
        },
    }
    log_context = {}
    resp = await az.handle_request_azure(data, log_context)

    assert resp.status_code == 400
    # content was provided via json.dumps, ensure message present
    body_text = resp.body.decode()
    assert "Unsupported command" in body_text


@pytest.mark.asyncio
async def test_comment_event_version_1_returns_version_error_or_jsonresponse_tuple(monkeypatch):
    # available_commands_rgx.match should be truthy
    monkeypatch.setattr(az, "available_commands_rgx", SimpleNamespace(match=lambda s: object()))

    # Use resourceVersion 1.0 at top level to trigger version-not-supported branch
    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "1.0",
        "resource": {
            "comment": {"content": "/do-something", "_links": {"threads": {"href": "http://x/threads/10"}}, "id": "5"},
            # missing pullRequest info intentionally to mirror v1 behavior
        },
    }
    log_context = {}
    result = await az.handle_request_azure(data, log_context)

    # Some versions of the code might return the JSONResponse directly, others return a tuple
    if isinstance(result, tuple):
        resp = result[0]
    else:
        resp = result

    assert resp.status_code == 400
    body_text = resp.body.decode()
    assert "version 1.0 webhook for Azure Devops PR comment is not supported" in body_text


@pytest.mark.asyncio
async def test_comment_event_handle_request_comment_raises_and_logs(monkeypatch):
    # available_commands_rgx.match should be truthy
    monkeypatch.setattr(az, "available_commands_rgx", SimpleNamespace(match=lambda s: object()))

    # Spy logger
    log_calls = {}

    class FakeLogger:
        def error(self, msg):
            log_calls['err'] = msg

    monkeypatch.setattr(az, "get_logger", lambda: FakeLogger())

    # make handle_request_comment raise
    async def fake_handle_request_comment(pr_url, action, thread_id, comment_id, log_context):
        raise RuntimeError("boom")

    monkeypatch.setattr(az, "handle_request_comment", fake_handle_request_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {"content": "/do", "_links": {"threads": {"href": "http://x/threads/77"}}, "id": "88"},
            "pullRequest": {"repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo"}, "pullRequestId": 123},
        },
    }
    log_context = {}
    resp = await az.handle_request_azure(data, log_context)

    assert "Azure DevOps Trigger failed. Error:boom" in log_calls.get('err', "")
    assert resp.status_code == 500
    body_text = resp.body.decode()
    assert "Internal server error" in body_text


@pytest.mark.asyncio
async def test_comment_event_handle_request_comment_success_returns_202(monkeypatch):
    # available_commands_rgx.match should be truthy
    monkeypatch.setattr(az, "available_commands_rgx", SimpleNamespace(match=lambda s: object()))

    # make handle_request_comment succeed and capture inputs
    captured = {}

    async def fake_handle_request_comment(pr_url, action, thread_id, comment_id, log_context):
        captured['pr_url'] = pr_url
        captured['action'] = action
        captured['thread_id'] = thread_id
        captured['comment_id'] = comment_id
        captured['log_context'] = dict(log_context)

    monkeypatch.setattr(az, "handle_request_comment", fake_handle_request_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {"content": "/run", "_links": {"threads": {"href": "http://x/threads/9"}}, "id": "10"},
            "pullRequest": {"repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo"}, "pullRequestId": 77},
        },
    }
    log_context = {}
    resp = await az.handle_request_azure(data, log_context)

    assert captured['action'] == "/run"
    assert captured['thread_id'] == 9
    assert captured['comment_id'] == 10
    assert "api_url" in captured['log_context']
    assert resp.status_code == 202
    body = json.loads(resp.body.decode())
    assert body["message"] == "webhook triggered successfully"


@pytest.mark.asyncio
async def test_unsupported_event_returns_204(monkeypatch):
    data = {"eventType": "something.else", "resource": {}}
    log_context = {}
    resp = await az.handle_request_azure(data, log_context)

    assert resp.status_code == 204
    body_text = resp.body.decode()
    assert "Unsupported event" in body_text
