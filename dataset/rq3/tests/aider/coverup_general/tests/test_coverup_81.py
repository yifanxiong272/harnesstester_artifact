# file: aider/mdstream.py:149-223
# asked: {"lines": [175, 191, 201, 220, 221, 222, 223], "branches": [[167, 172], [174, 175], [190, 191], [194, 213], [200, 201], [213, 220]]}
# gained: {"lines": [175, 191, 201, 220, 221, 222, 223], "branches": [[167, 172], [174, 175], [190, 191], [200, 201], [213, 220]]}

import time
import pytest
import types

import aider.mdstream as mdstream


class FakeConsole:
    def __init__(self, parent):
        self.parent = parent
        self.prints = []

    def print(self, payload):
        # record a string representation for assertions
        try:
            # Text objects from rich have __str__ and .plain; str(payload) is fine
            self.prints.append(str(payload))
        except Exception:
            self.prints.append(repr(payload))


class FakeLive:
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False
        self.console = FakeConsole(self)
        self.updates = []
        # capture init args for potential assertions
        self.init_args = args
        self.init_kwargs = kwargs

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def update(self, payload):
        # record a string representation for assertions
        try:
            self.updates.append(str(payload))
        except Exception:
            self.updates.append(repr(payload))


def _make_lines(n):
    return [f"line{i}\n" for i in range(n)]


def test_live_start_and_throttle_return(monkeypatch):
    """
    Test that on the first update the Live renderer is started and that if the
    throttle condition holds the update returns early (line 175).
    Covers branches: 167->172 and 175.
    """
    # Patch Live to our FakeLive
    monkeypatch.setattr(mdstream, "Live", FakeLive)

    ms = mdstream.MarkdownStream()
    # ensure not started
    assert not getattr(ms, "_live_started", False)
    # make render function return nothing (so no further printing would occur)
    monkeypatch.setattr(ms, "_render_markdown_to_lines", lambda text: [])
    # set when to now so that now - when < min_delay -> throttle triggers
    ms.when = time.time()
    ms.min_delay = 10.0  # large to ensure throttle

    # Call update; should start Live and then return early due to throttle
    res = ms.update("initial chunk", final=False)

    # After update, _live_started should be True and live should be FakeLive instance
    assert ms._live_started is True
    assert isinstance(ms.live, FakeLive)
    # start should have been called
    assert ms.live.started is True
    # Because update returned early, nothing was printed and printed list remains empty
    assert ms.printed == []
    # Ensure function returned None (no exceptions thrown)
    assert res is None


def test_nonfinal_print_and_rest_update(monkeypatch):
    """
    Test a non-final update that produces printed lines and updates the live window
    with the remaining lines (covers lines 190-201 printing and 220-223 rest update).
    """
    # Patch Live to our FakeLive
    monkeypatch.setattr(mdstream, "Live", FakeLive)

    ms = mdstream.MarkdownStream()
    # set up a FakeLive instance as the current live to avoid triggering the start branch
    fake = FakeLive()
    ms.live = fake
    ms._live_started = True

    # Create 10 lines of rendered markdown
    lines = _make_lines(10)
    monkeypatch.setattr(ms, "_render_markdown_to_lines", lambda text: lines)

    # Ensure no throttle: set when far in the past and small min_delay
    ms.when = time.time() - 100.0
    ms.min_delay = 0.0
    ms.live_window = 3  # last 3 lines remain in live window

    # No printed lines yet
    assert ms.printed == []

    ms.update("some streaming content", final=False)

    # num_lines = len(lines) - live_window = 7, so printed should now be first 7 lines
    assert ms.printed == lines[:7]

    # The FakeLive.console.print should have been called once with the joined first 7 lines
    assert len(fake.console.prints) >= 1
    printed_text = fake.console.prints[-1]
    for i in range(7):
        assert f"line{i}" in printed_text

    # The live.update should have been called with the remaining 3 lines (line7, line8, line9)
    assert len(fake.updates) >= 1
    last_update = fake.updates[-1]
    # Check that the rest (line7..line9) are present in the last update string
    for i in range(7, 10):
        assert f"line{i}" in last_update


def test_show_le_zero_return_when_no_new_lines(monkeypatch):
    """
    Test branch where there are no new stable lines to print (show <= 0), which should
    cause an early return (line 201).
    """
    monkeypatch.setattr(mdstream, "Live", FakeLive)

    ms = mdstream.MarkdownStream()
    fake = FakeLive()
    ms.live = fake
    ms._live_started = True

    # Create 5 lines of rendered markdown
    lines = _make_lines(5)
    monkeypatch.setattr(ms, "_render_markdown_to_lines", lambda text: lines)

    ms.when = time.time() - 100.0
    ms.min_delay = 0.0
    ms.live_window = 2  # num_lines = 5 - 2 = 3

    # Pretend we've already printed the first 3 lines
    ms.printed = lines[:3]

    # Call update - since show = num_lines - num_printed = 3 - 3 = 0, should return early
    res = ms.update("more stuff", final=False)

    # No new console.print should have occurred, and no live.update for rest
    assert fake.console.prints == []
    assert fake.updates == []
    assert res is None
    # printed should remain unchanged
    assert ms.printed == lines[:3]


def test_final_cleanup_calls_update_and_stop(monkeypatch):
    """
    Test that a final update triggers cleanup: live.update(Text("")), live.stop(), and live set to None.
    Covers lines 213.
    """
    monkeypatch.setattr(mdstream, "Live", FakeLive)

    ms = mdstream.MarkdownStream()
    fake = FakeLive()
    ms.live = fake
    ms._live_started = True

    # Render a couple of lines
    lines = _make_lines(2)
    monkeypatch.setattr(ms, "_render_markdown_to_lines", lambda text: lines)

    ms.when = time.time() - 100.0
    ms.min_delay = 0.0

    # Keep a local reference to fake to inspect updates after ms.live is cleared
    ms.printed = []  # ensure printed may be updated then cleaned up

    ms.update("final chunk", final=True)

    # After final update, ms.live should be set to None
    assert ms.live is None

    # The FakeLive instance should have stop called
    assert fake.stopped is True

    # The last update recorded should be the empty Text("") from the final cleanup.
    # Because other updates may have occurred earlier, ensure the final recorded update is empty string
    assert fake.updates, "Expected at least one update call on FakeLive"
    # The final update should be the last entry
    assert fake.updates[-1] == "" or fake.updates[-1] == "Text('')"
