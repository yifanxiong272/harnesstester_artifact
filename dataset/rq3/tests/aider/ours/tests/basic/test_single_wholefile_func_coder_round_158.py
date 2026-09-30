import importlib
from types import SimpleNamespace, MethodType


def test_get_edits_no_args_round_158(monkeypatch):
    """When parse_partial_args() is falsy, get_edits should return [] and should not call dump."""
    mod = importlib.import_module("aider.coders.single_wholefile_func_coder")

    recorded = []

    def fake_dump(arg):
        # If called, record so the test can detect it. Should not be called in this case.
        recorded.append(arg)

    # Patch the module-level dump that get_edits uses
    monkeypatch.setattr(mod, "dump", fake_dump)

    # Build a minimal self for calling the unbound method: it only needs the two methods referenced
    fake_self = SimpleNamespace()
    fake_self.get_inchat_relative_files = lambda: ["file.py"]
    fake_self.parse_partial_args = lambda: {}

    # Bind and call the method without instantiating the real class (avoids __init__ side effects)
    bound = MethodType(mod.SingleWholeFileFunctionCoder.get_edits, fake_self)
    result = bound()

    assert result == []
    # dump must not have been called
    assert recorded == []


def test_get_edits_with_args_round_158(monkeypatch):
    """When parse_partial_args() returns a content, get_edits should pair the single chat_file with that content and call dump with the tuple."""
    mod = importlib.import_module("aider.coders.single_wholefile_func_coder")

    recorded = []

    def fake_dump(arg):
        recorded.append(arg)

    monkeypatch.setattr(mod, "dump", fake_dump)

    fake_self = SimpleNamespace()
    fake_self.get_inchat_relative_files = lambda: ["file.py"]
    fake_self.parse_partial_args = lambda: {"content": "new content"}

    bound = MethodType(mod.SingleWholeFileFunctionCoder.get_edits, fake_self)
    result = bound()

    expected_tuple = ("file.py", "new content")
    assert result == [expected_tuple]
    # dump should have been called exactly once with the returned tuple
    assert recorded == [expected_tuple]
