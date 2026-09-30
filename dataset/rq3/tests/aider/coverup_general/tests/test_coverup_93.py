# file: aider/coders/base_coder.py:924-944
# asked: {"lines": [930, 939, 940, 941, 943, 944], "branches": [[927, 930], [932, 0], [936, 939], [939, 940], [939, 943]]}
# gained: {"lines": [930, 939, 940, 941, 943, 944], "branches": [[927, 930], [936, 939], [939, 940], [939, 943]]}

import pytest
from types import SimpleNamespace
from aider.coders.base_coder import Coder

class DummyIO:
    def __init__(self):
        self.warnings = []
    def tool_warning(self, msg):
        self.warnings.append(msg)

def make_coder_subclass(send_message_fn=None, preproc_fn=None):
    """
    Helper to create a concrete Coder subclass that uses the provided
    send_message_fn and preproc_fn. send_message_fn should be a function
    with signature (self, message) -> iterable. preproc_fn should be
    (self, user_message) -> processed_message.
    """
    class TestCoder(Coder):
        def __init__(self):
            # Do not call super().__init__ to avoid side effects; set minimal attrs used by run_one
            # Provide defaults if Coder expects them
            self.io = DummyIO()
            # Ensure num_reflections and max_reflections exist
            self.num_reflections = 0
            self.max_reflections = 5
            self._init_called = False
            self.sent_messages = []

        def init_before_message(self):
            self._init_called = True

        if preproc_fn is not None:
            def preproc_user_input(self, user_message):
                return preproc_fn(self, user_message)

        if send_message_fn is not None:
            def send_message(self, message):
                # record what we were asked to send
                self.sent_messages.append(message)
                return send_message_fn(self, message)

    return TestCoder

def test_run_one_no_preproc_breaks_and_uses_user_message():
    # send_message sets reflected_message to None so loop breaks immediately
    def send_msg(self, message):
        # set reflected to None to trigger break
        self.reflected_message = None
        # simulate generator output
        yield "sent"

    TestCoder = make_coder_subclass(send_message_fn=send_msg)
    coder = TestCoder()
    # ensure preproc_user_input is not present / not called by setting an attribute that would raise if used
    if hasattr(coder, "preproc_user_input"):
        # Replace it to ensure failure if erroneously called
        def _bad_preproc(self, _):
            raise RuntimeError("preproc should not be called")
        coder.preproc_user_input = _bad_preproc.__get__(coder, coder.__class__)

    # ensure default state
    coder.num_reflections = 0
    coder.max_reflections = 3

    coder.run_one("raw message", preproc=False)

    # postconditions
    assert coder._init_called is True
    # message sent should be exactly the user_message (line 930 path)
    assert coder.sent_messages == ["raw message"]
    # should have set reflected_message to None by our send_message
    assert coder.reflected_message is None
    # num_reflections should remain 0 (no increments)
    assert coder.num_reflections == 0
    # no warnings issued
    assert coder.io.warnings == []

def test_run_one_reflection_hits_max_and_issues_warning():
    # send_message sets reflected_message to some value to request a reflection
    def send_msg(self, message):
        self.reflected_message = "reflect-this"
        yield "sent"

    TestCoder = make_coder_subclass(send_message_fn=send_msg)
    coder = TestCoder()
    # Set num_reflections equal to max_reflections to trigger the warning return branch
    coder.num_reflections = 2
    coder.max_reflections = 2

    coder.run_one("start", preproc=False)

    # Should have attempted to reflect once (so send_message called)
    assert coder.sent_messages == ["start"]
    # Because num_reflections >= max_reflections, tool_warning should have been called and method returned early
    assert len(coder.io.warnings) == 1
    assert coder.io.warnings[0] == f"Only {coder.max_reflections} reflections allowed, stopping."
    # num_reflections should remain unchanged (no increment after hitting limit)
    assert coder.num_reflections == 2

def test_run_one_reflection_increments_and_continues_then_stops():
    # This send_message will, on first call, request a reflection, and on second call stop it.
    def send_msg(self, message):
        # Use an attribute to track calls
        call = getattr(self, "_send_call_count", 0)
        self._send_call_count = call + 1
        if call == 0:
            # first call: request a reflection
            self.reflected_message = "second-message"
            yield "first-sent"
        else:
            # second call: no further reflection -> end loop
            self.reflected_message = None
            yield "second-sent"

    TestCoder = make_coder_subclass(send_message_fn=send_msg)
    coder = TestCoder()
    coder.num_reflections = 0
    coder.max_reflections = 5

    coder.run_one("first-message", preproc=False)

    # send_message should have been called twice: first with the original, then with the reflected message
    assert coder.sent_messages == ["first-message", "second-message"]
    # num_reflections should have been incremented exactly once
    assert coder.num_reflections == 1
    # final reflected_message should be None (loop ended)
    assert coder.reflected_message is None
    # no warnings should be issued in this path
    assert coder.io.warnings == []
