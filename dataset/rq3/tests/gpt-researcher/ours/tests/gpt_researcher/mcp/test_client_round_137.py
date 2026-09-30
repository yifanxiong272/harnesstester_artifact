import pytest

from gpt_researcher.mcp import client as client_mod
from gpt_researcher.mcp.client import MCPClientManager


class DummyLock:
    """A minimal async context manager used in place of an actual lock.

    Matches the protocol used by `async with self._client_lock:` in the
    implementation under test.
    """

    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        # Do not swallow exceptions; return False
        return False


class DummyLogger:
    def __init__(self, raise_on_debug: bool = False):
        self.raise_on_debug = raise_on_debug
        self.debug_called = False
        self.error_called = False
        self.last_error_msg = None

    def debug(self, *args, **kwargs):
        self.debug_called = True
        if self.raise_on_debug:
            # deterministically raise to exercise the except branch
            raise ValueError("debug failed")

    def error(self, *args, **kwargs):
        self.error_called = True
        if args:
            # capture the formatted message passed in the code under test
            self.last_error_msg = args[0]
        else:
            self.last_error_msg = None


@pytest.mark.asyncio
async def test_close_client_when_client_is_none_round_137(monkeypatch):
    """When _client is already None, close_client should not call logger.debug or logger.error
    and must leave _client as None.
    """
    mgr = object.__new__(MCPClientManager)
    # simulate state: no client present
    mgr._client = None
    mgr._client_lock = DummyLock()

    dummy_logger = DummyLogger()
    # patch the module-level logger where the implementation resolves it
    monkeypatch.setattr('gpt_researcher.mcp.client.logger', dummy_logger)

    # call the async method under test
    await mgr.close_client()

    # assertions: no debug/error called and _client remains None
    assert dummy_logger.debug_called is False
    assert dummy_logger.error_called is False
    assert mgr._client is None


@pytest.mark.asyncio
async def test_close_client_with_existing_client_invokes_debug_round_137(monkeypatch):
    """When _client is present and logger.debug does not raise, debug should be called
    and _client must be cleared to None in the finally block.
    """
    mgr = object.__new__(MCPClientManager)
    mgr._client = object()
    mgr._client_lock = DummyLock()

    dummy_logger = DummyLogger(raise_on_debug=False)
    monkeypatch.setattr('gpt_researcher.mcp.client.logger', dummy_logger)

    await mgr.close_client()

    assert dummy_logger.debug_called is True
    assert dummy_logger.error_called is False
    # finally must always clear the reference
    assert mgr._client is None


@pytest.mark.asyncio
async def test_close_client_logger_debug_raises_triggers_error_round_137(monkeypatch):
    """If logger.debug raises an exception, close_client should catch it, call logger.error
    with a message containing the original exception message, and still clear _client.
    """
    mgr = object.__new__(MCPClientManager)
    mgr._client = object()
    mgr._client_lock = DummyLock()

    # configure logger.debug to raise to exercise the except branch
    dummy_logger = DummyLogger(raise_on_debug=True)
    monkeypatch.setattr('gpt_researcher.mcp.client.logger', dummy_logger)

    await mgr.close_client()

    assert dummy_logger.debug_called is True
    # error must have been called with a message including the raised exception text
    assert dummy_logger.error_called is True
    assert dummy_logger.last_error_msg is not None
    assert 'debug failed' in dummy_logger.last_error_msg
    assert mgr._client is None
