import types
from types import SimpleNamespace
import pytest

from aider.coders import base_coder


def make_fake_io():
    calls = []
    class FakeIO:
        def tool_warning(self, msg):
            calls.append(msg)
    return FakeIO(), calls


def test_run_one_preproc_false_round_149():
    # Arrange: fake self with minimal attributes used by run_one
    fake = SimpleNamespace()
    fake.init_called = False

    def init_before_message():
        fake.init_called = True

    fake.init_before_message = init_before_message

    # preproc_user_input should NOT be called in this test
    fake.preproc_called = False

    def preproc_user_input(inp):
        fake.preproc_called = True
        return "processed"

    fake.preproc_user_input = preproc_user_input

    # send_message should capture the message and not set a reflection
    fake.sent = []

    def send_message(msg):
        # record and explicitly produce an iterable (empty) as the real method does
        fake.sent.append(msg)
        fake.reflected_message = None
        return []

    fake.send_message = send_message

    fake.io, io_calls = make_fake_io()
    # start counters
    fake.num_reflections = 0
    fake.max_reflections = 3
    fake.reflected_message = None

    # Act
    base_coder.Coder.run_one(fake, "user input", preproc=False)

    # Assert: preproc path not used, message used as-is, send_message invoked once
    assert fake.init_called is True
    assert fake.preproc_called is False
    assert fake.sent == ["user input"]
    # no reflections should have been counted
    assert fake.num_reflections == 0
    # no tool warnings
    assert io_calls == []


def test_run_one_preproc_true_reflection_round_149():
    # Arrange: preproc True path -> message comes from preproc_user_input
    fake = SimpleNamespace()
    fake.init_before_message = lambda: None

    def preproc_user_input(inp):
        return "first_msg"

    fake.preproc_user_input = preproc_user_input

    # send_message behaves differently on first vs subsequent calls:
    # first call sets a reflected message (to cause another loop), second clears it.
    fake.sent = []

    def send_message(msg):
        fake.sent.append(msg)
        # on first call, produce a reflection
        if len(fake.sent) == 1:
            fake.reflected_message = "second_msg"
        else:
            fake.reflected_message = None
        return []

    fake.send_message = send_message

    fake.io, io_calls = make_fake_io()
    fake.num_reflections = 0
    fake.max_reflections = 5
    fake.reflected_message = None

    # Act
    base_coder.Coder.run_one(fake, "original", preproc=True)

    # Assert: preproc was used to obtain the first message
    assert fake.sent == ["first_msg", "second_msg"]
    # After one reflection, num_reflections should have been incremented once
    assert fake.num_reflections == 1
    # No warnings should have been issued
    assert io_calls == []


def test_run_one_respects_max_reflections_round_149():
    # Arrange: force the condition where num_reflections >= max_reflections
    fake = SimpleNamespace()
    fake.init_before_message = lambda: None
    fake.preproc_user_input = lambda inp: inp

    fake.sent = []

    def send_message(msg):
        # Always produce a reflected message to trigger the max_reflections check
        fake.sent.append(msg)
        fake.reflected_message = "would_loop"
        return []

    fake.send_message = send_message

    fake.io, io_calls = make_fake_io()
    # set num_reflections equal to max_reflections to trigger the tool_warning path
    fake.num_reflections = 2
    fake.max_reflections = 2
    fake.reflected_message = None

    # Act
    result = base_coder.Coder.run_one(fake, "input", preproc=False)

    # Assert: send_message ran once and a tool warning was emitted with exact message
    assert fake.sent == ["input"]
    assert len(io_calls) == 1
    assert io_calls[0] == f"Only {fake.max_reflections} reflections allowed, stopping."
    # The function should have returned early; num_reflections must remain unchanged
    assert fake.num_reflections == 2
    assert result is None
