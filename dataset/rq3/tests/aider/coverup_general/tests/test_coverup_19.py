# file: aider/commands.py:1260-1308
# asked: {"lines": [1263, 1265, 1266, 1267, 1268, 1269, 1270, 1271, 1273, 1275, 1277, 1278, 1279, 1280, 1282, 1285, 1286, 1288, 1289, 1290, 1292, 1293, 1294, 1296, 1299, 1300, 1301, 1302, 1304, 1305, 1307, 1308], "branches": [[1266, 1267], [1266, 1299], [1267, 1268], [1267, 1275], [1270, 1271], [1270, 1273], [1288, 1289], [1288, 1292], [1300, 1301], [1300, 1304]]}
# gained: {"lines": [1263, 1265, 1266, 1267, 1268, 1269, 1270, 1271, 1273, 1277, 1278, 1279, 1280, 1282, 1285, 1286, 1288, 1289, 1290, 1292, 1293, 1294, 1296, 1299, 1300, 1301, 1302, 1304, 1305, 1307, 1308], "branches": [[1266, 1267], [1266, 1299], [1267, 1268], [1270, 1271], [1270, 1273], [1288, 1289], [1288, 1292], [1300, 1301], [1300, 1304]]}

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        # convert to str for consistent comparisons
        self.outputs.append(str(msg))

    def tool_error(self, msg):
        self.errors.append(str(msg))


class DummyCoder:
    def __init__(self, abs_fnames=None):
        # abs_fnames is a set of string paths
        self.abs_fnames = set(abs_fnames or [])
        self.checked = False

    def check_added_files(self):
        self.checked = True


def _cleanup_paths_from_coder(coder: DummyCoder):
    # Remove any files created by the cmd_paste tests
    for f in list(coder.abs_fnames):
        try:
            p = Path(f)
            if p.exists():
                p.unlink()
            parent = p.parent
            # only remove if it looks like a temp directory created by mkdtemp
            # be conservative: only remove if empty
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            # ignore cleanup errors
            pass


def test_cmd_paste_image_replaces_existing_and_adds(monkeypatch, tmp_path):
    """
    Test the branch where clipboard contains an image, args provide a filename with
    an allowed extension (.jpg), and an existing file with same basename exists in coder.abs_fnames.
    This should remove the existing entry, add the new absolute path, call check_added_files,
    and emit appropriate output messages.
    """
    # Prepare dummy image to return
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))

    # Monkeypatch ImageGrab.grabclipboard to return our image
    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", lambda: img)

    io = DummyIO()

    # Create a fake existing file path with same basename "pic.jpg"
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()
    existing_path = existing_dir / "pic.jpg"
    existing_path.write_text("old")  # create an actual file; not required but okay

    coder = DummyCoder(abs_fnames={str(existing_path)})

    cmds = Commands(io=io, coder=coder)

    # Call with args specifying same basename
    cmds.cmd_paste("pic.jpg")

    # The existing entry should have been removed
    assert str(existing_path) not in coder.abs_fnames

    # One new file should have been added with name pic.jpg
    assert any(Path(f).name == "pic.jpg" for f in coder.abs_fnames)

    # check_added_files should have been called
    assert coder.checked is True

    # Output should include a Replaced message and an Added message
    # Note: order matters: replaced first, then added
    assert any("Replaced existing image in the chat" in o for o in io.outputs)
    assert any("Added clipboard image to the chat" in o for o in io.outputs)

    # Cleanup files created by command
    _cleanup_paths_from_coder(coder)
    # Also remove the pre-existing file/directory we created
    try:
        if existing_path.exists():
            existing_path.unlink()
        if existing_dir.exists():
            existing_dir.rmdir()
    except Exception:
        pass


def test_cmd_paste_image_without_extension_adds_png(monkeypatch):
    """
    Test the branch where clipboard contains an image, args provide a filename without extension,
    so the code should append .png and save as PNG.
    """
    img = Image.new("RGB", (5, 5), color=(0, 255, 0))
    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", lambda: img)

    io = DummyIO()
    coder = DummyCoder()

    cmds = Commands(io=io, coder=coder)

    cmds.cmd_paste("customname")  # no extension provided

    # The added filename should end with customname.png
    added = [f for f in coder.abs_fnames if Path(f).name.startswith("customname")]
    assert added, "No file added to coder.abs_fnames"
    assert any(str(f).lower().endswith(".png") for f in added)

    # Output should indicate addition
    assert any("Added clipboard image to the chat" in o for o in io.outputs)

    # Ensure file exists on disk
    for f in added:
        p = Path(f)
        assert p.exists(), f"Expected saved image file to exist: {p}"

    # Cleanup created files
    _cleanup_paths_from_coder(coder)


def test_cmd_paste_text_from_clipboard(monkeypatch):
    """
    Test the branch where the clipboard has no image but contains text.
    The method should output and return the text.
    """
    # No image available
    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", lambda: None)
    # pyperclip.paste returns some text
    monkeypatch.setattr("aider.commands.pyperclip.paste", lambda: "hello from clipboard")

    io = DummyIO()
    coder = DummyCoder()
    cmds = Commands(io=io, coder=coder)

    result = cmds.cmd_paste("")  # args empty

    assert result == "hello from clipboard"
    assert io.outputs and io.outputs[-1] == "hello from clipboard"


def test_cmd_paste_no_content_reports_error(monkeypatch):
    """
    Test the branch where clipboard has neither image nor text, resulting in an error message.
    """
    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", lambda: None)
    monkeypatch.setattr("aider.commands.pyperclip.paste", lambda: "")

    io = DummyIO()
    coder = DummyCoder()
    cmds = Commands(io=io, coder=coder)

    result = cmds.cmd_paste("")

    assert result is None
    assert io.errors and "No image or text content found in clipboard." in io.errors[-1]


def test_cmd_paste_exception_handling(monkeypatch):
    """
    Force ImageGrab.grabclipboard to raise an exception to hit the exception handler.
    """
    def raise_exc():
        raise RuntimeError("boom")

    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", raise_exc)

    io = DummyIO()
    coder = DummyCoder()
    cmds = Commands(io=io, coder=coder)

    # Should not raise; should capture the error and call tool_error
    result = cmds.cmd_paste("anything")

    assert result is None
    assert io.errors, "Expected an error to be recorded"
    assert any("Error processing clipboard content: boom" in e for e in io.errors)
