import pytest

from types import SimpleNamespace

from aider.io import InputOutput


class _Watcher:
    def __init__(self, process_return=None):
        self.process_return = process_return
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def process_changes(self):
        return self.process_return


def test_get_input_file_watcher_interrupted_round_003():
    io = InputOutput()

    # Build a prompt_session that sets interrupted on the io instance and returns empty line
    class PromptSessionStub:
        def prompt(self, show, **kwargs):
            # Simulate an external file change notification occurring during prompt
            io.interrupted = True
            return ""

    io.prompt_session = PromptSessionStub()
    io.placeholder = None

    # Provide watchers that will be started/stopped and will return a command when processed
    fw = _Watcher(process_return="RELOAD_CMD")
    cw = _Watcher(process_return=None)
    io.file_watcher = fw
    io.clipboard_watcher = cw

    # Call get_input and assert we receive the file_watcher's process_changes return value
    result = io.get_input(root="/", rel_fnames=[], addable_rel_fnames=[], commands=[])

    assert result == "RELOAD_CMD"
    # start/stop should have been invoked for both watchers
    assert fw.started is True and fw.stopped is True
    assert cw.started is True and cw.stopped is True


def test_get_input_multiline_tag_round_003():
    io = InputOutput()

    # Create a prompt_session that returns a tag opener, a content line, then the closing tag
    responses = ["{tag", "hello world", "tag}"]

    class PromptSessionSeq:
        def __init__(self, seq):
            self._seq = list(seq)

        def prompt(self, show, **kwargs):
            return self._seq.pop(0)

    seq = PromptSessionSeq(responses)
    io.prompt_session = seq
    io.placeholder = None

    captured = {}

    def fake_user_input(val):
        captured['last'] = val

    io.user_input = fake_user_input

    # Execute get_input; should return the content collected between tag and tag}
    result = io.get_input(root="/", rel_fnames=[], addable_rel_fnames=[], commands=[])

    assert result == "hello world\n"
    # Also ensure user_input was called with same content
    assert captured.get('last') == "hello world\n"


def test_get_input_brace_not_tag_round_003():
    io = InputOutput()

    # If the input starts with '{' but contains non-alphanumeric after the tag,
    # the code should treat the whole line as a single-line input and return it.
    class PromptOnce:
        def prompt(self, show, **kwargs):
            return "{bad!"

    io.prompt_session = PromptOnce()
    io.placeholder = None

    result = io.get_input(root="/", rel_fnames=[], addable_rel_fnames=[], commands=[])

    assert result == "{bad!"


def test_get_input_prompt_exception_round_003():
    io = InputOutput()

    # Make prompt raise a generic exception. The function should catch it, call tool_error twice,
    # and return an empty string.
    class PromptExplode:
        def prompt(self, show, **kwargs):
            raise ValueError("boom")

    io.prompt_session = PromptExplode()
    io.placeholder = None

    errors = []

    def fake_tool_error(msg, strip=True):
        errors.append(str(msg))

    io.tool_error = fake_tool_error

    result = io.get_input(root="/", rel_fnames=[], addable_rel_fnames=[], commands=[])

    assert result == ""
    # tool_error should have been called at least twice (message and traceback)
    assert len(errors) >= 2
    assert any("boom" in e for e in errors)


def test_get_input_eof_round_003():
    io = InputOutput()

    # If prompt raises EOFError, get_input should propagate it up
    class PromptEOF:
        def prompt(self, show, **kwargs):
            raise EOFError("no more input")

    io.prompt_session = PromptEOF()
    io.placeholder = None

    with pytest.raises(EOFError):
        io.get_input(root="/", rel_fnames=[], addable_rel_fnames=[], commands=[])
