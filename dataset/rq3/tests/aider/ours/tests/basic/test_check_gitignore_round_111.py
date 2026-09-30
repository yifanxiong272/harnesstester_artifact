import os
from pathlib import Path
import pytest

import aider.main as main


class FakeRepo:
    def __init__(self, ignored_map=None):
        # ignored_map: dict mapping pattern->bool
        self._ignored = ignored_map or {}

    def ignored(self, pattern):
        return bool(self._ignored.get(pattern, False))


class DummyIO:
    def __init__(self, *, read_text_fn=None, write_text_fn=None, confirm_value=True):
        self.read_text_fn = read_text_fn
        self.write_text_fn = write_text_fn
        self.confirm_value = confirm_value
        self.tool_output_calls = []
        self.tool_error_calls = []
        self.read_calls = []
        self.write_calls = []
        self.confirm_calls = []

    def read_text(self, path):
        self.read_calls.append(path)
        if self.read_text_fn is None:
            # default: read actual file
            return Path(path).read_text()
        return self.read_text_fn(path)

    def write_text(self, path, content):
        self.write_calls.append((path, content))
        if self.write_text_fn is None:
            Path(path).write_text(content)
        else:
            return self.write_text_fn(path, content)

    def tool_output(self, msg):
        self.tool_output_calls.append(msg)

    def tool_error(self, msg):
        self.tool_error_calls.append(msg)

    def confirm_ask(self, msg):
        self.confirm_calls.append(msg)
        return self.confirm_value


# All tests use deterministic behavior and patch main.git.Repo where the function resolves it.

def test_read_text_returns_none_round_111(tmp_path, monkeypatch):
    # Setup repo such that .aider is NOT ignored -> patterns_to_add = ['.aider*']
    monkeypatch.setattr(main, "git", type("G", (), {"Repo": lambda root: FakeRepo({".aider": False})}))

    git_root = tmp_path
    # create .gitignore file so code will call io.read_text
    gitignore = git_root / ".gitignore"
    gitignore.write_text("some content\n")

    # io.read_text returns None -> code should return early (line 178)
    io = DummyIO(read_text_fn=lambda p: None)

    # call
    main.check_gitignore(str(git_root), io, ask=False)

    # Assertions: read was attempted, but no write occurred and no tool_error/tool_output called
    assert io.read_calls, "read_text should have been called"
    assert not io.write_calls, "write_text should NOT have been called when read_text returns None"
    assert not io.tool_error_calls
    assert not io.tool_output_calls


def test_read_text_raises_oserror_round_111(tmp_path, monkeypatch):
    # Repo: .aider not ignored
    monkeypatch.setattr(main, "git", type("G", (), {"Repo": lambda root: FakeRepo({".aider": False})}))

    git_root = tmp_path
    gitignore = git_root / ".gitignore"
    gitignore.write_text("ignored content\n")

    # read_text raises OSError -> should call tool_error and return
    def raise_oserror(p):
        raise OSError("boom read")

    io = DummyIO(read_text_fn=raise_oserror)

    main.check_gitignore(str(git_root), io, ask=False)

    assert io.read_calls, "read_text should have been called"
    assert not io.write_calls, "write_text should NOT have been called when read_text raises"
    assert io.tool_error_calls, "tool_error should have been called when read_text raises OSError"
    # message should mention trying to read the .gitignore
    assert any("Error when trying to read" in msg for msg in io.tool_error_calls)


def test_confirm_ask_false_with_existing_gitignore_missing_newline_round_111(tmp_path, monkeypatch):
    # Repo: .aider not ignored
    monkeypatch.setattr(main, "git", type("G", (), {"Repo": lambda root: FakeRepo({".aider": False})}))

    git_root = tmp_path
    gitignore = git_root / ".gitignore"
    # existing content WITHOUT trailing newline to exercise the content.endswith branch
    gitignore.write_text("existingcontent")

    # read_text returns content missing newline; confirm_ask returns False
    io = DummyIO(read_text_fn=lambda p: "existingcontent", confirm_value=False)

    # ask=True to hit the confirm_ask branch
    main.check_gitignore(str(git_root), io, ask=True)

    # tool_output should have the skip message
    assert any("You can skip this check with --no-gitignore" in m for m in io.tool_output_calls)
    # confirm_ask should have been called with the patterns list
    assert io.confirm_calls, "confirm_ask should have been called"
    assert ".aider*" in io.confirm_calls[0]
    # No write should have occurred because confirm_ask returned False
    assert not io.write_calls


def test_write_text_raises_oserror_and_outputs_patterns_round_111(tmp_path, monkeypatch):
    # Repo: .aider not ignored
    monkeypatch.setattr(main, "git", type("G", (), {"Repo": lambda root: FakeRepo({".aider": False})}))

    git_root = tmp_path
    # Ensure .gitignore does NOT exist to exercise the else: content = "" path
    (git_root / ".gitignore").unlink(missing_ok=True)

    # write_text will raise OSError to trigger the write-exception branch
    def raise_on_write(p, c):
        raise OSError("boom write")

    io = DummyIO(write_text_fn=raise_on_write, confirm_value=True)

    # ask=True and confirm True to attempt write and trigger exception
    main.check_gitignore(str(git_root), io, ask=True)

    # write attempted
    assert io.write_calls, "write_text should have been attempted"
    # tool_error should have been called because write_text raised
    assert io.tool_error_calls, "tool_error should have been called when write_text raises OSError"
    assert any("Error when trying to write" in msg for msg in io.tool_error_calls)
    # After error, code outputs the 'Try running with appropriate permissions' message
    assert any("Try running with appropriate permissions" in msg for msg in io.tool_output_calls)
    # And it should output each pattern prefixed by two spaces
    assert any(msg.strip() == ".aider*" for msg in io.tool_output_calls), "pattern should be output after write error"
