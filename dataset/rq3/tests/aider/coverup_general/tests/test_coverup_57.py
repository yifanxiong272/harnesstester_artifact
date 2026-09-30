# file: aider/coders/base_coder.py:2244-2267
# asked: {"lines": [2246, 2255, 2256, 2257, 2258, 2259, 2260, 2262, 2263, 2265, 2266, 2267], "branches": [[2245, 2246], [2252, 2255], [2256, 2257], [2256, 2262], [2257, 2258], [2257, 2259], [2262, 2263], [2262, 2265]]}
# gained: {"lines": [2246, 2255, 2256, 2257, 2259, 2260, 2262, 2265, 2266, 2267], "branches": [[2245, 2246], [2252, 2255], [2256, 2257], [2256, 2262], [2257, 2259], [2262, 2265]]}

import pytest

from aider import urls
from aider.coders.base_coder import Coder


class DummyIO:
    def __init__(self, read_text_return="content"):
        self.read_calls = []
        self.warnings = []
        self._read_text_return = read_text_return

    def read_text(self, fname):
        self.read_calls.append(fname)
        return self._read_text_return

    def tool_warning(self, msg):
        self.warnings.append(msg)


class DummyModel:
    def __init__(self, per_call_tokens):
        # per_call_tokens can be a number or an iterable to return different values
        if hasattr(per_call_tokens, "__iter__") and not isinstance(per_call_tokens, (str, bytes)):
            self._iter = iter(per_call_tokens)
            self._fixed = None
        else:
            self._iter = None
            self._fixed = per_call_tokens
        self.calls = []

    def token_count(self, content):
        self.calls.append(content)
        if self._iter is not None:
            return next(self._iter)
        return self._fixed


def make_coder_instance():
    # Create instance without running __init__
    coder = Coder.__new__(Coder)
    return coder


def test_check_added_files_triggers_warning():
    """
    Exercise the branch where:
    - number of files >= warn_number_of_files
    - token total >= warn_number_of_tokens
    Expect two warnings and warning_given set to True.
    """
    coder = make_coder_instance()

    # Prepare 4 non-image files to meet warn_number_of_files (which is 4)
    # Use .py extensions so is_image_file returns False.
    coder.abs_fnames = ["f1.py", "f2.py", "f3.py", "f4.py"]

    # IO that records reads and warnings
    io = DummyIO(read_text_return="dummy")
    coder.io = io

    # main_model returns 6000 tokens per file -> total 24000 >= 20480
    coder.main_model = DummyModel(6000)

    coder.warning_given = False

    coder.check_added_files()

    # After call, tool_warning should have been called twice with specific messages
    assert len(io.warnings) == 2
    assert io.warnings[0] == "Warning: it's best to only add files that need changes to the chat."
    assert io.warnings[1] == urls.edit_errors

    # read_text should have been called for each non-image file
    assert io.read_calls == ["f1.py", "f2.py", "f3.py", "f4.py"]

    # main_model.token_count should have been called once per file (with the content returned)
    assert len(coder.main_model.calls) == 4
    assert all(call == "dummy" for call in coder.main_model.calls)

    # warning flag set
    assert coder.warning_given is True


def test_check_added_files_early_return_when_already_warned():
    """
    If warning_given is already True, function should return immediately and not call IO.
    """
    coder = make_coder_instance()

    coder.abs_fnames = ["should_not_be_read.py", "also_not_read.py", "img.png", "extra.py"]
    # IO that would record any calls; its tool_warning will raise if called
    class FailIO(DummyIO):
        def tool_warning(self, msg):
            raise AssertionError("tool_warning should not be called when warning_given is True")

        def read_text(self, fname):
            raise AssertionError("read_text should not be called when warning_given is True")

    io = FailIO()
    coder.io = io

    coder.main_model = DummyModel(1000000)  # If called, would produce large tokens

    coder.warning_given = True

    # Should not raise
    coder.check_added_files()

    # Ensure no reads or warnings occurred
    assert io.read_calls == []
    assert io.warnings == []
    assert coder.warning_given is True
