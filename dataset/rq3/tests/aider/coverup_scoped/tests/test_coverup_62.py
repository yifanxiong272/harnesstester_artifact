# file: aider/waiting.py:207-217
# asked: {"lines": [208, 209, 210, 211, 212, 213, 214, 215, 217], "branches": [[210, 211], [210, 213]]}
# gained: {"lines": [208, 209, 210, 211, 212, 213, 214, 215, 217], "branches": [[210, 211], [210, 213]]}

import pytest
import importlib

def test_main_completes_calls_step_and_end(monkeypatch, capsys):
    # Import module under test
    waiting = importlib.import_module("aider.waiting")

    # Replace time.sleep to avoid delays
    monkeypatch.setattr(waiting.time, "sleep", lambda t: None)

    # Track calls to step and end
    step_calls = {"count": 0}
    end_called = {"called": False}

    def fake_step(self, text=None):
        # mimic signature; just count invocations
        step_calls["count"] += 1

    def fake_end(self):
        end_called["called"] = True

    # Patch Spinner.step and Spinner.end
    monkeypatch.setattr(waiting.Spinner, "step", fake_step, raising=True)
    monkeypatch.setattr(waiting.Spinner, "end", fake_end, raising=True)

    # Run main
    waiting.main()

    # Capture stdout and verify success message printed
    captured = capsys.readouterr()
    assert "Success!" in captured.out

    # Verify that step was called 100 times and end was called
    assert step_calls["count"] == 100
    assert end_called["called"] is True

def test_main_handles_keyboardinterrupt_and_calls_end(monkeypatch, capsys):
    # Import module under test
    waiting = importlib.import_module("aider.waiting")

    # Replace time.sleep to avoid delays
    monkeypatch.setattr(waiting.time, "sleep", lambda t: None)

    # Make step raise KeyboardInterrupt on first call
    end_called = {"called": False}
    step_called = {"count": 0}

    def raising_step(self, text=None):
        step_called["count"] += 1
        raise KeyboardInterrupt

    def fake_end(self):
        end_called["called"] = True

    # Patch Spinner.step and Spinner.end
    monkeypatch.setattr(waiting.Spinner, "step", raising_step, raising=True)
    monkeypatch.setattr(waiting.Spinner, "end", fake_end, raising=True)

    # Run main; it should handle KeyboardInterrupt and return normally
    waiting.main()

    # Capture stdout and verify interrupted message printed
    captured = capsys.readouterr()
    # The code prints a leading newline before the message
    assert "Interrupted by user." in captured.out

    # Verify that step was called at least once and end was called
    assert step_called["count"] >= 1
    assert end_called["called"] is True
