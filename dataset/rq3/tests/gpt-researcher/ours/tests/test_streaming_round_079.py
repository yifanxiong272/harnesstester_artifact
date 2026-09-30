import asyncio
import logging
import types
import pytest
from gpt_researcher.mcp.streaming import MCPStreamer


def test_no_websocket_stream_log_sync_round_079(caplog):
    caplog.set_level(logging.INFO)
    s = MCPStreamer(websocket=None)
    s.stream_log_sync("hello-no-ws")

    # should always log the info message even when websocket is falsy
    assert any(r.levelno == logging.INFO and "hello-no-ws" in r.getMessage() for r in caplog.records)


def test_loop_is_running_creates_task_round_079(monkeypatch):
    calls = []

    # Fake event loop with is_running True
    class LoopLike:
        def is_running(self):
            return True

    def fake_get_event_loop():
        return LoopLike()

    def fake_create_task(coro):
        # coro is a coroutine object created from the bound async method
        # extract the passed arguments from the coroutine frame for deterministic checks
        msg = None
        data = None
        if hasattr(coro, 'cr_frame') and coro.cr_frame is not None:
            f_locals = coro.cr_frame.f_locals
            msg = f_locals.get('message')
            data = f_locals.get('data')
        calls.append((msg, data))
        # return a harmless dummy task-like object
        return types.SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: fake_get_event_loop())
    monkeypatch.setattr(asyncio, 'create_task', fake_create_task)

    s = MCPStreamer(websocket=True)

    # replace stream_log with a real coroutine function so a coroutine object is created
    async def fake_stream_log(message, data):
        # should not be executed by create_task mock, but exists to form the coroutine
        return (message, data)

    # bind the coroutine function to the instance
    s.stream_log = types.MethodType(fake_stream_log, s)

    s.stream_log_sync("running-msg", {"k": "v"})

    # verify create_task was called and received the correct coroutine arguments
    assert calls == [("running-msg", {"k": "v"})]


def test_loop_run_until_complete_round_079(monkeypatch):
    calls = []

    class LoopLike:
        def is_running(self):
            return False

        def run_until_complete(self, coro):
            # inspect the coroutine object for the passed args
            msg = None
            data = None
            if hasattr(coro, 'cr_frame') and coro.cr_frame is not None:
                f_locals = coro.cr_frame.f_locals
                msg = f_locals.get('message')
                data = f_locals.get('data')
            calls.append((msg, data))
            # don't actually run the coroutine
            return None

    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: LoopLike())

    s = MCPStreamer(websocket=True)

    async def fake_stream_log(message, data):
        # not executed by run_until_complete stub; present to construct coroutine
        return (message, data)

    s.stream_log = types.MethodType(fake_stream_log, s)

    s.stream_log_sync("sync-run", 123)

    assert calls == [("sync-run", 123)]


def test_runtimeerror_logged_round_079(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    def raise_runtime():
        raise RuntimeError("no loop")

    # Simulate get_event_loop raising RuntimeError -> inner except handles it
    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: (_ for _ in ()).throw(RuntimeError("no loop")))

    s = MCPStreamer(websocket=True)
    s.stream_log_sync("x")

    # inner except logs a debug message indicating no running event loop
    assert any("Could not stream log: no running event loop" in r.getMessage() and r.levelno == logging.DEBUG for r in caplog.records)


def test_other_exception_logs_error_round_079(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)

    # Simulate get_event_loop raising a non-RuntimeError which should be caught by outer except
    def raise_value_error():
        raise ValueError("boom")

    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: (_ for _ in ()).throw(ValueError("boom")))

    s = MCPStreamer(websocket=True)
    s.stream_log_sync("y")

    # outer except should log an error mentioning the original exception
    assert any(r.levelno == logging.ERROR and "Error in sync log streaming: boom" in r.getMessage() for r in caplog.records)
