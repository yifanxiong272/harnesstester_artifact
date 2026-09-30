# file: openhands/app_server/app_conversation/live_status_app_conversation_service.py:1524-1605
# asked: {"lines": [1544, 1546, 1548, 1551, 1552, 1553, 1555, 1556, 1557, 1558, 1559, 1563, 1564, 1567, 1568, 1570, 1571, 1572, 1576, 1577, 1579, 1581, 1582, 1583, 1584, 1585, 1586, 1588, 1589, 1591, 1592, 1593, 1594, 1597, 1598, 1599, 1602, 1603, 1604], "branches": [[1556, 1557], [1556, 1563], [1567, 1568], [1567, 1570], [1576, 1577], [1576, 1597]]}
# gained: {"lines": [1544, 1546, 1548, 1551, 1552, 1553, 1555, 1556, 1557, 1558, 1559, 1563, 1564, 1567, 1570, 1571, 1572, 1576, 1577, 1579, 1581, 1582, 1583, 1584, 1585, 1586, 1588, 1589, 1591, 1592, 1593, 1594, 1597, 1598, 1599, 1602, 1603, 1604], "branches": [[1556, 1557], [1556, 1563], [1567, 1570], [1576, 1577], [1576, 1597]]}

import asyncio
import uuid
import pytest

from uuid import UUID
from types import SimpleNamespace

from openhands.app_server.app_conversation.live_status_app_conversation_service import (
    LiveStatusAppConversationService,
)


class PendingMessageServiceStub:
    def __init__(self, update_return=0, pending_messages=None, delete_return=0):
        self.update_calls = []
        self.get_calls = []
        self.delete_calls = []
        self._update_return = update_return
        self._pending_messages = pending_messages or []
        self._delete_return = delete_return

    async def update_conversation_id(self, old_conversation_id: str, new_conversation_id: str):
        self.update_calls.append((old_conversation_id, new_conversation_id))
        return self._update_return

    async def get_pending_messages(self, conversation_id: str):
        self.get_calls.append(conversation_id)
        return self._pending_messages

    async def delete_messages_for_conversation(self, conversation_id: str):
        self.delete_calls.append(conversation_id)
        return self._delete_return


class ContentItem:
    def __init__(self, payload):
        self._payload = payload
        self.model_dump_calls = 0

    def model_dump(self):
        self.model_dump_calls += 1
        return self._payload


class MessageStub:
    def __init__(self, id_, role, content_items):
        self.id = id_
        self.role = role
        self.content = content_items


class ResponseOK:
    def __init__(self):
        self.raise_for_status_called = 0

    def raise_for_status(self):
        self.raise_for_status_called += 1
        return None


class ResponseError:
    def __init__(self, exc):
        self._exc = exc
        self.raise_for_status_called = 0

    def raise_for_status(self):
        self.raise_for_status_called += 1
        raise self._exc


class HttpxClientStub:
    def __init__(self, response):
        self._response = response
        self.posts = []

    async def post(self, url, json=None, headers=None, timeout=None):
        # record the call and return the provided response object
        self.posts.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return self._response


@pytest.mark.asyncio
async def test_process_pending_messages_successful_delivery():
    # Setup UUIDs
    task_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    agent_server_url = "http://agent.local"
    session_api_key = "secret-key"

    # Prepare the content item and message
    content_item = ContentItem({"text": "hello"})
    msg = MessageStub(id_="msg1", role="user", content_items=[content_item])

    # pending service will report 1 updated, return one pending message, and delete 1 message
    pending_service = PendingMessageServiceStub(update_return=1, pending_messages=[msg], delete_return=1)
    # successful response stub
    response = ResponseOK()
    httpx_client = HttpxClientStub(response)

    # Instantiate service with minimal required fields (others unused by this method)
    svc = LiveStatusAppConversationService(
        user_context=None,
        app_conversation_info_service=None,
        app_conversation_start_task_service=None,
        event_callback_service=None,
        event_service=None,
        sandbox_service=None,
        sandbox_spec_service=None,
        jwt_service=None,
        pending_message_service=pending_service,
        sandbox_startup_timeout=1,
        sandbox_startup_poll_frequency=1,
        max_num_conversations_per_sandbox=1,
        httpx_client=httpx_client,
        web_url=None,
        openhands_provider_base_url=None,
        access_token_hard_timeout=None,
        app_mode=None,
        tavily_api_key=None,
        init_git_in_empty_workspace=False,
    )

    # Call the method under test
    await svc._process_pending_messages(task_id, conversation_id, agent_server_url, session_api_key)

    # Assertions: update_conversation_id called with task-{task_id.hex} and str(conversation_id)
    expected_task_str = f"task-{task_id.hex}"
    expected_conversation_str = str(conversation_id)
    assert pending_service.update_calls == [(expected_task_str, expected_conversation_str)]

    # get_pending_messages should be called with conversation id string
    assert pending_service.get_calls == [expected_conversation_str]

    # httpx_client.post should have been called once with correct URL, headers and JSON payload
    assert len(httpx_client.posts) == 1
    post_call = httpx_client.posts[0]
    expected_url = f"{agent_server_url}/api/conversations/{expected_conversation_str}/events"
    assert post_call["url"] == expected_url
    assert post_call["headers"] == {"X-Session-API-Key": session_api_key}
    assert post_call["timeout"] == 30.0

    # Verify JSON payload content and role/run flag
    assert post_call["json"]["role"] == msg.role
    assert post_call["json"]["run"] is True
    # content should be list of model_dump outputs
    assert post_call["json"]["content"] == [{"text": "hello"}]
    # model_dump should have been called on the content item
    assert content_item.model_dump_calls == 1

    # delete_messages_for_conversation should have been called and returned value matches stub (we check call)
    assert pending_service.delete_calls == [expected_conversation_str]


@pytest.mark.asyncio
async def test_process_pending_messages_delivery_failure_still_deletes():
    # Setup UUIDs
    task_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    agent_server_url = "http://agent.local"
    session_api_key = "session-key-2"

    # Prepare the content item and message; here delivery will fail
    content_item = ContentItem({"text": "fail-case"})
    msg = MessageStub(id_="msg-fail", role="assistant", content_items=[content_item])

    # pending service will report 0 updated, return the pending message, and delete 2 messages (arbitrary)
    pending_service = PendingMessageServiceStub(update_return=0, pending_messages=[msg], delete_return=2)
    # response that raises on raise_for_status
    response = ResponseError(Exception("boom"))
    httpx_client = HttpxClientStub(response)

    svc = LiveStatusAppConversationService(
        user_context=None,
        app_conversation_info_service=None,
        app_conversation_start_task_service=None,
        event_callback_service=None,
        event_service=None,
        sandbox_service=None,
        sandbox_spec_service=None,
        jwt_service=None,
        pending_message_service=pending_service,
        sandbox_startup_timeout=1,
        sandbox_startup_poll_frequency=1,
        max_num_conversations_per_sandbox=1,
        httpx_client=httpx_client,
        web_url=None,
        openhands_provider_base_url=None,
        access_token_hard_timeout=None,
        app_mode=None,
        tavily_api_key=None,
        init_git_in_empty_workspace=False,
    )

    # Call the method under test: should catch the exception and continue to deletion
    await svc._process_pending_messages(task_id, conversation_id, agent_server_url, session_api_key)

    expected_task_str = f"task-{task_id.hex}"
    expected_conversation_str = str(conversation_id)

    # update_conversation_id was called (even if it returned 0)
    assert pending_service.update_calls == [(expected_task_str, expected_conversation_str)]
    # get_pending_messages called
    assert pending_service.get_calls == [expected_conversation_str]
    # httpx_client.post should have been called once despite error
    assert len(httpx_client.posts) == 1
    post_call = httpx_client.posts[0]
    expected_url = f"{agent_server_url}/api/conversations/{expected_conversation_str}/events"
    assert post_call["url"] == expected_url
    # ensure content was attempted to be serialized
    assert post_call["json"]["content"] == [{"text": "fail-case"}]
    # deletion still happens even if raise_for_status threw
    assert pending_service.delete_calls == [expected_conversation_str]
