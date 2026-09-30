import pytest
from aider import gui


class FakeCtx:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSt:
    def __init__(self):
        self.writes = []
        self.expanders = []
        self.popovers = []

    def expander(self, label, expanded=False):
        # record call and return a simple context manager
        self.expanders.append({"label": label, "expanded": expanded})
        return FakeCtx()

    def popover(self, label):
        # record call and return a simple context manager
        self.popovers.append({"label": label})
        return FakeCtx()

    def write(self, msg):
        # record written messages for assertions
        self.writes.append(msg)


def test_do_recommended_actions_round_172(monkeypatch):
    """
    Exercise GUI.do_recommended_actions without constructing a real GUI instance.
    - Patch aider.gui.st to a FakeSt that provides expander, popover, and write.
    - Patch aider.gui.urls.git to a deterministic URL string.
    - Patch aider.gui.random.random to return deterministic keys for the two button calls.
    - Call the unbound method with a dummy self that implements button(...).
    Assert that the expected text strings are written and that the dummy button recorded
    two calls with deterministic keys and help text.
    """

    fake_st = FakeSt()
    # Patch the module-level 'st' where the function resolves it
    monkeypatch.setattr(gui, "st", fake_st)

    # Ensure the urls.git used in text is deterministic
    monkeypatch.setattr(gui.urls, "git", "http://example.com/faq", raising=False)

    # Make random.random deterministic for the two calls in the method
    seq = iter([0.1, 0.2])

    def fake_random():
        return next(seq)

    monkeypatch.setattr(gui.random, "random", fake_random)

    # Create a dummy self that only implements the button interface used by the method
    class DummySelf:
        def __init__(self):
            self.button_calls = []

        def button(self, label, key=None, help=None):
            # record the exact kwargs the code passes
            self.button_calls.append({"label": label, "key": key, "help": help})

    dummy = DummySelf()

    # Call the unbound function with the dummy self
    gui.GUI.do_recommended_actions(dummy)

    # Build expected first text (concatenation in the function)
    expected_text = "Aider works best when your code is stored in a git repo.  \n"
    expected_text += f"[See the FAQ for more info](http://example.com/faq)"

    # Two writes are expected: one inside the first popover (text) and one in the second popover
    assert len(fake_st.writes) == 2, "expected two st.write calls"
    assert fake_st.writes[0] == expected_text
    assert fake_st.writes[1] == "It's best to keep aider's internal files out of your git repo."

    # Two button calls expected with deterministic keys and help equal to '?'
    assert len(dummy.button_calls) == 2

    first = dummy.button_calls[0]
    assert first["label"] == "Create git repo"
    assert first["key"] == 0.1
    assert first["help"] == "?"

    second = dummy.button_calls[1]
    assert second["label"] == "Add `.aider*` to `.gitignore`"
    assert second["key"] == 0.2
    assert second["help"] == "?"
