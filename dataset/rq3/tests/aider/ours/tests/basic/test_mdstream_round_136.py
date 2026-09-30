import types
import pytest

import aider.mdstream as mdstream


class FakeText:
    def __init__(self, s=""):
        # mimic rich.Text minimal behavior used by MarkdownStream
        self.s = s

    @classmethod
    def from_ansi(cls, s):
        return cls(s)

    def __repr__(self):
        return f"FakeText({self.s!r})"


class FakeConsole:
    def __init__(self):
        self.print_calls = []

    def print(self, obj):
        self.print_calls.append(obj)


class FakeLive:
    def __init__(self, text_obj, refresh_per_second=None):
        # record constructor inputs
        self.init_text = text_obj
        self.refresh_per_second = refresh_per_second
        self.console = FakeConsole()
        self.started = False
        self.stopped = False
        self.update_calls = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def update(self, obj):
        self.update_calls.append(obj)


class TimeStub:
    def __init__(self, values):
        # values is an iterable of floats returned sequentially
        self._values = list(values)
        self.last = self._values[-1] if self._values else 0.0

    def __call__(self):
        if self._values:
            self.last = self._values.pop(0)
        return self.last


def make_stream_instance():
    # Create bare instance without invoking __init__ to allow deterministic setup
    inst = mdstream.MarkdownStream.__new__(mdstream.MarkdownStream)
    # provide common attributes used by update
    inst.min_delay = 1.0
    inst.when = 0.0
    inst.printed = []
    inst.live_window = 2
    # don't set _live_started so the first update call will create the Live
    if hasattr(inst, "_live_started"):
        delattr(inst, "_live_started")
    inst.live = None
    return inst


def test_throttle_return_round_136(monkeypatch):
    """If updates are called too quickly (throttled), update returns early.

    Covers: first-call Live creation (167->172) and throttle early return (174->175).
    """
    inst = make_stream_instance()

    # Patch Live and Text before calling update so the ctor uses our fakes
    monkeypatch.setattr(mdstream, "Live", FakeLive)
    monkeypatch.setattr(mdstream, "Text", FakeText)

    # Ensure _render_markdown_to_lines would return something if called
    monkeypatch.setattr(mdstream.MarkdownStream, "_render_markdown_to_lines", lambda self, t: ["a\n"])

    # Make time() return a value such that now - when < min_delay
    # inst.when is 0.0; return 0.5 and min_delay is 1.0 -> 0.5 < 1.0 triggers return
    monkeypatch.setattr(mdstream.time, "time", TimeStub([0.5]))

    # Call update; since throttled, it should return early and not render or print
    result = inst.update("some markdown", final=False)

    # The call should have created a Live and started it (first-time path)
    assert isinstance(inst.live, FakeLive)
    assert inst.live.started is True

    # Because of throttle, no console.print or live.update should have been invoked
    assert inst.live.console.print_calls == []
    assert inst.live.update_calls == []

    # update returns None; ensure no exceptions and a None return
    assert result is None


def test_non_final_print_and_rest_update_round_136(monkeypatch):
    """Non-final updates print stable lines and update the live window with the rest.

    Covers: num_lines calculation with subtraction (190->191), printing branch (194->213),
    and the live.update of remaining lines (220->223).
    """
    inst = make_stream_instance()

    # Prepare fakes
    monkeypatch.setattr(mdstream, "Live", FakeLive)
    monkeypatch.setattr(mdstream, "Text", FakeText)

    # Render returns four lines (each element is the string form used by code)
    lines = ["line1\n", "line2\n", "line3\n", "line4\n"]
    monkeypatch.setattr(mdstream.MarkdownStream, "_render_markdown_to_lines", lambda self, t: list(lines))

    # Control time to simulate a small render time and to avoid throttle
    # Sequence of time.time() calls in update: now (172), start (179), end (181)
    # Provide values so now - when >= min_delay (when is 0.0)
    # and render_time = small positive -> min_delay gets adjusted but remains deterministic
    stub_times = TimeStub([1.1, 1.2, 1.25])
    monkeypatch.setattr(mdstream.time, "time", stub_times)

    # Initially no printed lines so printing should occur for the stable lines
    inst.printed = []
    inst.live_window = 2  # so num_lines = len(lines) - 2 = 2 stable lines

    # Call update non-final
    inst.update("ignored text chunk", final=False)

    # After update, printed should be the first num_lines lines
    assert inst.printed == lines[:2]

    # The console should have received the printed stable block joined
    assert len(inst.live.console.print_calls) == 1
    printed_obj = inst.live.console.print_calls[0]
    assert isinstance(printed_obj, FakeText)
    assert printed_obj.s == "".join(lines[:2])

    # The live.update should have been called with the remaining lines
    assert len(inst.live.update_calls) == 1
    updated_obj = inst.live.update_calls[0]
    assert isinstance(updated_obj, FakeText)
    assert updated_obj.s == "".join(lines[2:])

    # Live should still exist (not final cleanup)
    assert inst.live is not None


def test_final_cleanup_and_print_round_136(monkeypatch):
    """Final update prints any remaining stable lines then performs cleanup.

    Covers: printing in final case, final cleanup update/stop/live reset (213->220).
    """
    inst = make_stream_instance()

    monkeypatch.setattr(mdstream, "Live", FakeLive)
    monkeypatch.setattr(mdstream, "Text", FakeText)

    # four lines; because final=True, all lines are considered stable
    lines = ["L1\n", "L2\n", "L3\n", "L4\n"]
    monkeypatch.setattr(mdstream.MarkdownStream, "_render_markdown_to_lines", lambda self, t: list(lines))

    # Provide deterministic time sequence: now, start, end
    monkeypatch.setattr(mdstream.time, "time", TimeStub([2.0, 2.01, 2.02]))

    # Pretend we've already printed two lines previously
    inst.printed = lines[:2]
    inst.live_window = 2

    # Call update with final=True
    inst.update("final chunk", final=True)

    # printed should now equal all stable lines (all lines because final)
    assert inst.printed == lines[:len(lines)]

    # Console should have been called once with the new stable portion (L3+L4)
    assert len(inst.live.console.print_calls) == 1
    printed_obj = inst.live.console.print_calls[0]
    assert isinstance(printed_obj, FakeText)
    assert printed_obj.s == "".join(lines[2:4])

    # Final cleanup should call live.update with an empty Text and then stop
    # Our FakeLive records those calls
    # The last update call should be the empty string
    assert inst.live.update_calls[-1].s == ""
    assert inst.live.stopped is True

    # After cleanup the object sets live to None
    assert inst.live is None
