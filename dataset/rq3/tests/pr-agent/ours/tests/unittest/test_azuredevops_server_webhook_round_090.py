import pytest
from pr_agent.servers import azuredevops_server_webhook as module
from pr_agent.servers.azuredevops_server_webhook import handle_line_comment


class FakeLine:
    def __init__(self, line: int):
        self.line = line


class FakeThreadContext:
    def __init__(self, file_path, left_start=None, left_end=None, right_start=None, right_end=None):
        self.file_path = file_path
        self.left_file_start = left_start
        self.left_file_end = left_end
        self.right_file_start = right_start
        self.right_file_end = right_end


class FakeProvider:
    def __init__(self, mapping):
        # mapping: thread_id -> FakeThreadContext or None
        self._mapping = mapping

    def get_thread_context(self, thread_id):
        return self._mapping.get(thread_id)


def test_not_ask_round_090():
    # If the comment does not start with '/ask ' the original (stripped) body is returned
    res = handle_line_comment("  hello world  ", 1, None)
    assert res == "hello world"


def test_provider_no_context_round_090():
    # When provider returns falsy for thread context, return the stripped original body
    provider = FakeProvider({})
    # leading/trailing spaces are stripped first inside the function
    res = handle_line_comment("  /ask why?  ", 9, provider)
    assert res == "/ask why?"


def test_left_range_round_090():
    # When left file range is present, it should build the /ask_line command with side=left
    thread_id = 42
    ctx = FakeThreadContext(
        file_path="src/file_a.py",
        left_start=FakeLine(10),
        left_end=FakeLine(12),
        right_start=None,
        right_end=None,
    )
    provider = FakeProvider({thread_id: ctx})

    res = handle_line_comment("/ask explain this block", thread_id, provider)

    assert res.startswith("/ask_line ")
    # exact expected reconstructed command
    expected = (
        "/ask_line --line_start=10 --line_end=12 --side=left --file_name=src/file_a.py --comment_id=42 explain this block"
    )
    assert res == expected


def test_right_range_round_090():
    # When right file range is present (and left is not), it should build the /ask_line command with side=right
    thread_id = 7
    ctx = FakeThreadContext(
        file_path="other/file_b.py",
        left_start=None,
        left_end=None,
        right_start=FakeLine(101),
        right_end=FakeLine(105),
    )
    provider = FakeProvider({thread_id: ctx})

    res = handle_line_comment("/ask what changes?", thread_id, provider)

    expected = (
        "/ask_line --line_start=101 --line_end=105 --side=right --file_name=other/file_b.py --comment_id=7 what changes?"
    )
    assert res == expected


def test_no_range_logs_round_090(monkeypatch):
    # When no left/right ranges exist, function logs the situation and returns the body
    thread_id = 11
    ctx = FakeThreadContext(file_path="no_range.py")
    provider = FakeProvider({thread_id: ctx})

    class CapturingLogger:
        def __init__(self):
            self.calls = []

        def info(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    fake_logger = CapturingLogger()

    # Patch the get_logger symbol where the function under test resolves it
    monkeypatch.setattr(module, "get_logger", lambda: fake_logger)

    res = handle_line_comment("/ask nothing here", thread_id, provider)

    # The body should be returned unchanged (stripped)
    assert res == "/ask nothing here"

    # And the logger should have been called once with the expected message and artifact kwarg
    assert len(fake_logger.calls) == 1
    args, kwargs = fake_logger.calls[0]
    assert args[0] == "No line range found in thread context"
    # artifact should contain the same thread context object
    assert "artifact" in kwargs
    assert kwargs["artifact"]["thread_context"] is ctx
