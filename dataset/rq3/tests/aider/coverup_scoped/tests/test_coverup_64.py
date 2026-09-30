# file: aider/coders/base_coder.py:986-1000
# asked: {"lines": [988, 990, 992, 993, 994, 995, 996, 998, 1000], "branches": [[993, 994], [993, 998]]}
# gained: {"lines": [988, 990, 992, 993, 994, 995, 996, 998, 1000], "branches": [[993, 994], [993, 998]]}

import pytest
from types import SimpleNamespace

from aider.coders.base_coder import Coder


def make_io():
    class IO:
        def __init__(self):
            self.warnings = []
            self.pretty = False
            self.encoding = "utf-8"

        def tool_warning(self, msg):
            self.warnings.append(msg)

    return IO()


def make_main_model():
    # Provide the minimal attributes/methods Coder.__init__ expects.
    return SimpleNamespace(
        reasoning_tag=None,
        streaming=False,
        cache_control=False,
        info={},
        weak_model=None,
        max_chat_history_tokens=0,
        commit_message_models=lambda: [],
    )


def make_coder(use_git=False):
    io = make_io()
    main_model = make_main_model()
    # provide a trivial summarizer so ChatSummary is not constructed
    summarizer = object()
    coder = Coder(main_model, io, use_git=use_git, summarizer=summarizer)
    return coder, io


def test_keyboard_interrupt_first_time_sets_timestamp_and_warns(monkeypatch):
    coder, io = make_coder(use_git=False)

    # Ensure no previous keyboard interrupt
    coder.last_keyboard_interrupt = None

    # Control time to a fixed value
    monkeypatch.setattr("aider.coders.base_coder.time.time", lambda: 1_000.0)
    # Avoid real terminal cursor manipulation
    monkeypatch.setattr("aider.coders.base_coder.Console.show_cursor", lambda self, v: None)

    # Act
    coder.keyboard_interrupt()

    # Assert: warning shown for first-time interrupt and timestamp set
    assert io.warnings == ["\n\n^C again to exit"]
    assert coder.last_keyboard_interrupt == 1_000.0


def test_keyboard_interrupt_second_time_exits_and_warns_and_events(monkeypatch):
    coder, io = make_coder(use_git=False)

    # record events
    events = []

    def record_event(*args, **kwargs):
        events.append((args, kwargs))

    coder.event = record_event

    # Set previous interrupt so that now - last < 2
    coder.last_keyboard_interrupt = 999.5

    # Control time to a fixed value (difference 0.5 < thresh 2)
    monkeypatch.setattr("aider.coders.base_coder.time.time", lambda: 1_000.0)
    # Avoid real terminal cursor manipulation
    monkeypatch.setattr("aider.coders.base_coder.Console.show_cursor", lambda self, v: None)

    # Act & Assert: expect SystemExit
    with pytest.raises(SystemExit):
        coder.keyboard_interrupt()

    # Assert: appropriate warning and event called, and last_keyboard_interrupt unchanged
    assert io.warnings == ["\n\n^C KeyboardInterrupt"]
    assert events == [(("exit",), {"reason": "Control-C"})]
    assert coder.last_keyboard_interrupt == 999.5
