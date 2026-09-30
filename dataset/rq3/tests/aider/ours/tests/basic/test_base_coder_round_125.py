import types
import pytest

import aider.coders.base_coder as base_coder


class DummyIO:
    def __init__(self, placeholder=False):
        self.placeholder = placeholder
        self.user_inputs = []

    def user_input(self, msg):
        # record that user_input was called with the message
        self.user_inputs.append(msg)


class DummyCoder:
    def __init__(self):
        # attributes referenced by Coder.run
        self.io = DummyIO()
        self.partial_response_content = None
        self.copy_context_called = False
        self.run_one_calls = []
        self.show_undo_hint_called = False
        self.keyboard_interrupt_called = False

    def run_one(self, user_message, preproc=True):
        # record the call
        self.run_one_calls.append((user_message, preproc))

    def copy_context(self):
        self.copy_context_called = True

    def show_undo_hint(self):
        self.show_undo_hint_called = True

    def keyboard_interrupt(self):
        self.keyboard_interrupt_called = True


def make_get_input(sequence):
    """Return a get_input callable that iterates through sequence.

    sequence items:
      - a string to return
      - 'KB' to raise KeyboardInterrupt
      - 'EOF' to raise EOFError
    """
    seq = list(sequence)

    def get_input():
        if not seq:
            # default to EOF to allow run to exit deterministically
            raise EOFError
        v = seq.pop(0)
        if v == "KB":
            raise KeyboardInterrupt
        if v == "EOF":
            raise EOFError
        return v

    return get_input


def test_with_message_round_125():
    """When with_message is provided, run should call io.user_input and run_one,
    then return partial_response_content (branch 878->882).
    """
    dummy = DummyCoder()
    dummy.io = DummyIO(placeholder=True)
    dummy.partial_response_content = "PARTIAL"

    # track that run_one is invoked with the provided message and preproc flag
    called = []

    def run_one(user_message, preproc=True):
        called.append((user_message, preproc))

    dummy.run_one = run_one

    # Call the unbound function Coder.run with our dummy instance
    result = base_coder.Coder.run(dummy, with_message="hello", preproc=False)

    assert result == "PARTIAL"
    # ensure io.user_input recorded the provided message
    assert dummy.io.user_inputs == ["hello"]
    # ensure run_one was called with same message and preproc=False
    assert called == [("hello", False)]


def test_loop_copy_context_and_eof_round_125():
    """Test loop path where io.placeholder is False so copy_context() is called
    and then EOFError ends the loop (covers branch 884->885 leading to EOF handling).
    """
    dummy = DummyCoder()
    # placeholder False -> copy_context should be invoked
    dummy.io = DummyIO(placeholder=False)
    # set get_input to immediately raise EOFError so run exits after copy_context
    dummy.get_input = make_get_input(["EOF"])

    # Ensure run_one won't be called (get_input raises EOF before run_one)
    dummy.run_one = lambda *a, **k: (_ for _ in ()).throw(AssertionError("run_one should not be called"))

    # Calling the method should exit by returning None (EOFError handled)
    result = base_coder.Coder.run(dummy, with_message=None, preproc=True)

    assert result is None
    assert dummy.copy_context_called is True
    # keyboard_interrupt should not have been invoked in this path
    assert dummy.keyboard_interrupt_called is False


def test_loop_skip_copy_context_and_keyboard_interrupt_round_125():
    """Test loop path where io.placeholder is True (skip copy_context), then
    get_input raises KeyboardInterrupt once (triggering keyboard_interrupt()),
    then EOFError to exit the outer try (covers branches 884->886 and KeyboardInterrupt path).
    """
    dummy = DummyCoder()
    dummy.io = DummyIO(placeholder=True)

    # First call -> KeyboardInterrupt, second call -> EOFError to exit loop
    dummy.get_input = make_get_input(["KB", "EOF"])

    # run_one should never be reached in this scenario
    dummy.run_one = lambda *a, **k: (_ for _ in ()).throw(AssertionError("run_one should not be called"))

    result = base_coder.Coder.run(dummy, with_message=None, preproc=True)

    assert result is None
    # since placeholder True, copy_context should not have been invoked
    assert dummy.copy_context_called is False
    # keyboard_interrupt should have been called once
    assert dummy.keyboard_interrupt_called is True
