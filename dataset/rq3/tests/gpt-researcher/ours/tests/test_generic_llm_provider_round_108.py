import asyncio
from types import SimpleNamespace

from gpt_researcher.llm_provider.generic.base import GenericLLMProvider


def test_non_stream_no_chat_logger_round_108():
    # Arrange: create provider and replace hooks with test doubles
    provider = GenericLLMProvider(llm=None, chat_log=None, verbose=False)

    # Track calls to reset and capture
    provider._reset_called = False

    def fake_reset():
        provider._reset_called = True

    captured = {}

    def fake_capture(output):
        # capture the exact object passed in for assertion
        captured['output'] = output

    # Prepare a fake LLM with an async ainvoke returning an object with a content attribute
    async def fake_ainvoke(messages, **kwargs):
        # include an extra attribute to ensure _capture_response_metadata receives it intact
        return SimpleNamespace(content="hello-no-chat", info={"src": "test"})

    # Inject fakes
    provider._reset_last_response_metadata = fake_reset
    provider._capture_response_metadata = fake_capture
    provider.llm = SimpleNamespace(ainvoke=fake_ainvoke)
    provider.chat_logger = None

    # Act
    result = asyncio.run(provider.get_chat_response(messages=[{"role": "user", "content": "x"}], stream=False))

    # Assert
    assert result == "hello-no-chat"
    # reset was called before any further processing
    assert provider._reset_called is True
    # capture received the exact object returned by fake_ainvoke
    assert 'output' in captured and getattr(captured['output'], 'content') == "hello-no-chat"


def test_non_stream_with_chat_logger_round_108():
    # Arrange
    provider = GenericLLMProvider(llm=None, chat_log=None, verbose=False)

    called = {}

    async def fake_ainvoke(messages, **kwargs):
        return SimpleNamespace(content="hello-with-chat", meta={"ok": True})

    async def fake_log_request(messages, response):
        # record the arguments to assert later
        called['messages'] = messages
        called['response'] = response

    # Provide synchronous reset and capture hooks (the code under test calls them synchronously)
    def fake_reset():
        called['reset'] = True

    def fake_capture(output):
        called['captured_output'] = output

    provider._reset_last_response_metadata = fake_reset
    provider._capture_response_metadata = fake_capture
    provider.llm = SimpleNamespace(ainvoke=fake_ainvoke)

    # chat_logger must expose async log_request
    provider.chat_logger = SimpleNamespace(log_request=fake_log_request)

    # Act
    result = asyncio.run(provider.get_chat_response(messages=[{"role": "user", "content": "y"}], stream=False))

    # Assert
    assert result == "hello-with-chat"
    # metadata capture was invoked with the object returned by the fake LLM
    assert 'captured_output' in called and getattr(called['captured_output'], 'content') == "hello-with-chat"
    # the chat logger was awaited with the original messages and the resolved content
    assert called.get('messages') == [{"role": "user", "content": "y"}]
    assert called.get('response') == "hello-with-chat"
    # reset hook was invoked
    assert called.get('reset') is True


def test_stream_true_uses_stream_response_round_108():
    # Arrange
    provider = GenericLLMProvider(llm=None, chat_log=None, verbose=False)

    calls = {}

    async def fake_stream_response(messages, websocket, **kwargs):
        # record call args and return a distinctive string
        calls['messages'] = messages
        calls['websocket'] = websocket
        calls['kwargs'] = kwargs
        return "streamed-output"

    async def fake_log_request(messages, response):
        calls['logged_messages'] = messages
        calls['logged_response'] = response

    # Replace methods on the provider
    provider.stream_response = fake_stream_response
    provider.chat_logger = SimpleNamespace(log_request=fake_log_request)

    # Act
    result = asyncio.run(provider.get_chat_response(messages=[{"role": "user", "content": "stream?"}], stream=True, websocket="ws-1"))

    # Assert
    assert result == "streamed-output"
    assert calls['messages'] == [{"role": "user", "content": "stream?"}]
    assert calls['websocket'] == "ws-1"
    # chat_logger must have been invoked with the same content returned from stream_response
    assert calls.get('logged_response') == "streamed-output"
    assert calls.get('logged_messages') == [{"role": "user", "content": "stream?"}]
