import types
import pytest
from types import SimpleNamespace

import aider.coders.base_coder as base_coder

# Helpers used across tests
class DummyIO:
    def __init__(self):
        self.warn_calls = []

    def tool_warning(self, msg):
        self.warn_calls.append(msg)


class FakeSelf:
    def __init__(self):
        # state mutated by show_send_output_stream
        self.partial_response_function_call = {}
        self.got_reasoning_content = False
        self.reasoning_tag_name = "REASON"
        self.ended_reasoning_content = False
        self.partial_response_content = ""
        self.io = DummyIO()
        self._stop_called = False
        self._live_calls = []

    def _stop_waiting_spinner(self):
        self._stop_called = True

    def show_pretty(self):
        # default overridden by tests when needed
        return False

    def live_incremental_response(self, final):
        self._live_calls.append(final)


def make_chunk(**delta_attrs):
    """Create a chunk-like object with a single choice that exposes delta attrs."""
    delta = SimpleNamespace(**delta_attrs)
    choice = SimpleNamespace(delta=delta)
    chunk = SimpleNamespace(choices=[choice])
    return chunk


def test_finish_reason_length_round_054():
    """If a chunk choice has finish_reason == 'length', the method raises FinishReasonLength."""
    fake = FakeSelf()
    # Create a chunk whose first choice advertises finish_reason == 'length'
    choice = SimpleNamespace(finish_reason="length")
    chunk = SimpleNamespace(choices=[choice])

    # Calling the generator should raise the module's FinishReasonLength
    with pytest.raises(base_coder.FinishReasonLength):
        # show_send_output_stream is a generator; invoking and exhausting triggers loop.
        list(base_coder.Coder.show_send_output_stream(fake, [chunk]))


def test_function_call_merge_round_054():
    """When delta.function_call exists, keys are merged/concatenated into partial_response_function_call and spinner stopped."""
    fake = FakeSelf()
    fake.partial_response_function_call = {"a": "orig_"}

    # delta.function_call with a key that already exists and a new key
    chunk = make_chunk(function_call={"a": "new", "b": "bee"})

    # Run generator to completion (no content so nothing yielded)
    list(base_coder.Coder.show_send_output_stream(fake, [chunk]))

    # existing key should be concatenated
    assert fake.partial_response_function_call["a"] == "orig_new"
    # new key should be inserted
    assert fake.partial_response_function_call["b"] == "bee"
    # spinner should have been stopped because we received content (function call counts)
    assert fake._stop_called is True


def test_unicode_encode_error_and_yield_round_054(monkeypatch):
    """Test branch where content is written to stdout, write raises UnicodeEncodeError first, then safe write succeeds, and the generator yields the text."""
    fake = FakeSelf()
    # Simulate that we previously had reasoning content and haven't ended it yet
    fake.got_reasoning_content = True
    fake.ended_reasoning_content = False

    # The content that will be appended and eventually yielded
    content_text = "<<content>>"
    # This will force the codepath that appends the closing reasoning tag before content
    chunk = make_chunk(content=content_text)

    # Patch replace_reasoning_tags to be a visible identity function
    called = {}

    def fake_replace(text, tag_name):
        called['args'] = (text, tag_name)
        return text

    monkeypatch.setattr(base_coder, "replace_reasoning_tags", fake_replace)

    # Create a fake stdout object at the module level with controlled behavior
    class FakeStdout:
        def __init__(self):
            self.encoding = "utf-8"
            self.writes = []
            self.call_count = 0
            self.flushed = False

        def write(self, text):
            # On first call simulate a UnicodeEncodeError, then on second call succeed
            self.call_count += 1
            if self.call_count == 1:
                # Raise a realistic UnicodeEncodeError
                raise UnicodeEncodeError("utf-8", b"", 0, 1, "can't encode")
            self.writes.append(text)

        def flush(self):
            self.flushed = True

    fake_stdout = FakeStdout()
    # Patch the module's sys.stdout so the function under test uses our fake
    monkeypatch.setattr(base_coder.sys, "stdout", fake_stdout)

    # Run the generator and capture the first yielded item
    gen = base_coder.Coder.show_send_output_stream(fake, [chunk])
    yielded = next(gen)

    # The yielded value should match the (unmodified) text after replace_reasoning_tags
    # Because got_reasoning_content was True and ended_reasoning_content False, the code
    # prepends the closing reasoning tag followed by two newlines before content.
    expected_text = f"\n\n</{fake.reasoning_tag_name}>\n\n" + content_text
    assert yielded == expected_text

    # replace_reasoning_tags must have been called with the expected values
    assert called['args'][1] == fake.reasoning_tag_name

    # Ensure stdout saw a failed attempt then a successful write and flush
    assert fake_stdout.call_count >= 2
    assert fake_stdout.flushed is True

    # finish the generator to avoid warnings
    with pytest.raises(StopIteration):
        next(gen)


def test_empty_response_calls_tool_warning_round_054():
    """When no content is received at all, io.tool_warning is called with an informative message."""
    fake = FakeSelf()

    # Create a chunk where choices exists but delta has no attributes -> AttributeError branches hit
    chunk = make_chunk()

    # Exhaust the generator (it should yield nothing)
    list(base_coder.Coder.show_send_output_stream(fake, [chunk]))

    # After completion, since no content was received, tool_warning should have been called
    assert len(fake.io.warn_calls) == 1
    assert "Empty response received from LLM" in fake.io.warn_calls[0]
