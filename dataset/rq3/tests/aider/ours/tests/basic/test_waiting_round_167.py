import types
import pytest
from aider import waiting


class DummySpinner:
    """A deterministic stand-in for aider.waiting.Spinner.

    Records calls so tests can assert behavior without relying on real
    console output or threading.
    """

    instances = []

    def __init__(self, text):
        self.text = text
        self.step_count = 0
        self.end_called = False
        DummySpinner.instances.append(self)

    def step(self):
        # deterministic, fast increment
        self.step_count += 1

    def end(self):
        self.end_called = True


def test_main_completes_round_167(monkeypatch, capsys):
    """Verify the normal completion path: all steps run and Success! is printed.

    - Patch Spinner to DummySpinner to capture step/end calls.
    - Patch time.sleep to a no-op to avoid real delays.
    - After main(), assert step_count == 100, end() called, and stdout contains Success!
    """
    # Prepare dummy spinner tracking
    DummySpinner.instances.clear()
    monkeypatch.setattr(waiting, "Spinner", DummySpinner)

    # Patch time.sleep in the module to avoid sleeping
    monkeypatch.setattr(waiting.time, "sleep", lambda _secs: None)

    # Execute
    waiting.main()

    # There should be exactly one spinner instance created by main()
    assert len(DummySpinner.instances) == 1
    spinner = DummySpinner.instances[0]

    # main() should have called step() 100 times and always called end()
    assert spinner.step_count == 100
    assert spinner.end_called is True

    # And main should have printed a Success! message
    captured = capsys.readouterr()
    assert "Success!" in captured.out


def test_main_keyboard_interrupt_round_167(monkeypatch, capsys):
    """Verify KeyboardInterrupt branch and finally behavior.

    - Patch Spinner to DummySpinner so we can observe end() being called.
    - Patch time.sleep to raise KeyboardInterrupt immediately to trigger the except branch.
    - Assert spinner.step() was not called, spinner.end() was called, and the interrupt message was printed.
    """
    DummySpinner.instances.clear()
    monkeypatch.setattr(waiting, "Spinner", DummySpinner)

    # Make time.sleep raise KeyboardInterrupt immediately on first call
    def raise_interrupt(_secs):
        raise KeyboardInterrupt

    monkeypatch.setattr(waiting.time, "sleep", raise_interrupt)

    # Execute
    waiting.main()

    # Validate spinner was created and ended, but didn't step
    assert len(DummySpinner.instances) == 1
    spinner = DummySpinner.instances[0]
    assert spinner.step_count == 0
    assert spinner.end_called is True

    # The except clause prints an interrupt message that includes 'Interrupted by user.'
    captured = capsys.readouterr()
    assert "Interrupted by user." in captured.out
