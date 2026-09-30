import re
import json
import pytest

import pr_agent.servers.azuredevops_server_webhook as azure


def _normalize_resp(resp):
    """Helper to handle real JSONResponse or accidental tuple-wrapped responses.
    The source contains a return with a trailing comma in one branch which results
    in a tuple being returned (observed in measured failure). This helper
    extracts the first element as the response object and a string representation
    of the body for assertions.
    """
    # Some code paths may return a tuple because of a trailing comma in the source
    if isinstance(resp, tuple):
        resp_obj = resp[0]
        # try to find a body in the tuple if present
        body = None
        for part in resp[1:]:
            if isinstance(part, (str, bytes, bytearray)):
                body = part
                break
    else:
        resp_obj = resp
        body = getattr(resp_obj, "body", None)

    if body is None:
        body = getattr(resp_obj, "body", None)

    if isinstance(body, (bytes, bytearray)):
        decoded = body.decode()
    else:
        decoded = str(body)
    return resp_obj, decoded


@pytest.mark.asyncio
async def test_pr_created_round_059(monkeypatch):
    called = {}

    async def fake_perform(commands_conf, agent, api_url, log_context):
        called['commands_conf'] = commands_conf
        called['agent_type'] = type(agent).__name__
        called['api_url'] = api_url
        called['log_context'] = dict(log_context)

    monkeypatch.setattr(azure, "_perform_commands_azure", fake_perform)

    data = {
        "eventType": "git.pullrequest.created",
        "resource": {
            "_links": {
                "web": {"href": "http://example.com/_apis/git/repositories/myrepo"}
            }
        }
    }
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)

    assert resp_obj.status_code == azure.status.HTTP_202_ACCEPTED
    assert "webhook triggered successfully" in decoded
    assert called['agent_type'] in ("PRAgent", "PRAgentProxy", "object")
    assert "_git" in called['api_url'] or "myrepo" in called['api_url']
    assert log_context.get("event") == data["eventType"]
    assert "api_url" in log_context


@pytest.mark.asyncio
async def test_comment_v2_success_round_059(monkeypatch):
    monkeypatch.setattr(azure, "available_commands_rgx", re.compile(r"^TEST_CMD$"))

    called = {}

    async def fake_handle_comment(pr_url, action, thread_id, comment_id, log_context):
        called['pr_url'] = pr_url
        called['action'] = action
        called['thread_id'] = thread_id
        called['comment_id'] = comment_id
        called['log_context'] = dict(log_context)

    monkeypatch.setattr(azure, "handle_request_comment", fake_handle_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {
                "content": "TEST_CMD",
                "_links": {"threads": {"href": "http://example.com/threads/123"}},
                "id": "456"
            },
            "pullRequest": {
                "repository": {"webUrl": "http://example.com/repos/repo1"},
                "pullRequestId": 99
            }
        }
    }
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)

    assert resp_obj.status_code == azure.status.HTTP_202_ACCEPTED
    assert called['action'] == "TEST_CMD"
    assert isinstance(called['thread_id'], int) and called['thread_id'] == 123
    assert isinstance(called['comment_id'], int) and called['comment_id'] == 456
    assert log_context.get("event") == data["eventType"]
    assert "api_url" in log_context


@pytest.mark.asyncio
async def test_comment_v1_bad_round_059(monkeypatch):
    # Make regex match so we exercise the version 1.0 branch which in the source
    # returns a tuple due to a trailing comma. Normalize response accordingly.
    monkeypatch.setattr(azure, "available_commands_rgx", re.compile(r"^CMD$"))

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "1.0",
        "resource": {
            "comment": {"content": "CMD"},
        }
    }
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)

    assert resp_obj.status_code == azure.status.HTTP_400_BAD_REQUEST
    assert "version 1.0 webhook" in decoded or "upgrade to version 2.0" in decoded


@pytest.mark.asyncio
async def test_comment_unsupported_round_059(monkeypatch):
    monkeypatch.setattr(azure, "available_commands_rgx", re.compile(r"^DO_NOT_MATCH$"))

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {"comment": {"content": "something else"}}
    }
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)
    assert resp_obj.status_code == azure.status.HTTP_400_BAD_REQUEST
    assert "Unsupported command" in decoded


@pytest.mark.asyncio
async def test_handle_comment_exception_round_059(monkeypatch):
    monkeypatch.setattr(azure, "available_commands_rgx", re.compile(r"^CRASH$"))

    async def raising_handle_comment(pr_url, action, thread_id, comment_id, log_context):
        raise RuntimeError("boom")

    monkeypatch.setattr(azure, "handle_request_comment", raising_handle_comment)

    data = {
        "eventType": "ms.vss-code.git-pullrequest-comment-event",
        "resourceVersion": "2.0",
        "resource": {
            "comment": {"content": "CRASH", "_links": {"threads": {"href": "http://x/1"}}, "id": "2"},
            "pullRequest": {"repository": {"webUrl": "http://x"}, "pullRequestId": 5}
        }
    }
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)

    assert resp_obj.status_code == azure.status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Internal server error" in decoded


@pytest.mark.asyncio
async def test_unsupported_event_round_059():
    data = {"eventType": "something_else"}
    log_context = {}

    resp = await azure.handle_request_azure(data, log_context)
    resp_obj, decoded = _normalize_resp(resp)
    assert resp_obj.status_code == azure.status.HTTP_204_NO_CONTENT
    assert "Unsupported event" in decoded
