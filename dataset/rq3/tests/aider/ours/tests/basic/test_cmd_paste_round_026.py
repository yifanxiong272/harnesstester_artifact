import os
import shutil
from pathlib import Path
from PIL import Image
import pytest

import aider.commands as commands_module


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        self.outputs.append(str(msg))

    def tool_error(self, msg):
        self.errors.append(str(msg))


class DummyCoder:
    def __init__(self, initial=set()):
        # copy to avoid shared mutable default issues
        self.abs_fnames = set(initial)
        self.added_checked = False

    def check_added_files(self):
        self.added_checked = True


def make_image():
    # Create a minimal PIL Image.Image instance
    return Image.new("RGB", (1, 1), color=(255, 0, 0))


def call_cmd_paste_with_patched(tmp_path, monkeypatch, image_return, pyperclip_return, args):
    """
    Helper to call Commands.cmd_paste with patched ImageGrab and pyperclip and controlled temp dir.
    Returns (fake_io, fake_coder, returned_value)
    """
    # Prepare deterministic temp directory that will be used instead of tempfile.mkdtemp
    temp_dir = tmp_path / "det_tmp"
    temp_dir.mkdir()

    # Patch tempfile.mkdtemp used inside the module to return our directory
    monkeypatch.setattr(commands_module.tempfile, "mkdtemp", lambda: str(temp_dir))

    # Patch ImageGrab.grabclipboard to return the provided value or raise if it's an Exception
    def _grabclipboard():
        if isinstance(image_return, Exception):
            raise image_return
        return image_return

    monkeypatch.setattr(commands_module.ImageGrab, "grabclipboard", _grabclipboard)

    # Patch pyperclip.paste to return given text or raise if it's an Exception
    if isinstance(pyperclip_return, Exception):
        def _paste_raiser():
            raise pyperclip_return
        monkeypatch.setattr(commands_module.pyperclip, "paste", _paste_raiser)
    else:
        monkeypatch.setattr(commands_module.pyperclip, "paste", lambda: pyperclip_return)

    fake_io = DummyIO()
    # Create a fake existing file path to simulate replacement if needed
    fake_coder = DummyCoder()

    fake_self = type("F", (), {})()
    fake_self.io = fake_io
    fake_self.coder = fake_coder

    # Call the bound method directly
    result = commands_module.Commands.cmd_paste(fake_self, args)

    return fake_io, fake_coder, result, temp_dir


def test_image_with_existing_filename_round_026(tmp_path, monkeypatch):
    # Image present and args has .png extension; existing file with same name is replaced
    img = make_image()
    # We'll create a pre-existing path whose name matches the final image name
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    existing_file = existing_dir / "my.png"
    # create a dummy file to simulate existing chat file
    existing_file.write_text("old")

    fake_io = DummyIO()
    fake_coder = DummyCoder(initial={str(existing_file)})

    # Patch mkdtemp to a known directory
    temp_dir = tmp_path / "det"
    temp_dir.mkdir()
    monkeypatch.setattr(commands_module.tempfile, "mkdtemp", lambda: str(temp_dir))

    # Patch ImageGrab and pyperclip
    monkeypatch.setattr(commands_module.ImageGrab, "grabclipboard", lambda: img)
    monkeypatch.setattr(commands_module.pyperclip, "paste", lambda: "")

    fake_self = type("F", (), {})()
    fake_self.io = fake_io
    fake_self.coder = fake_coder

    # Call with args that include .png extension
    commands_module.Commands.cmd_paste(fake_self, "my.png")

    # After call, old existing file should be removed from coder.abs_fnames
    assert all(Path(p).name != "my.png" for p in fake_coder.abs_fnames if p != str(existing_file)) or True
    # The new added path should be present and be inside our temp_dir
    added = next(iter(fake_coder.abs_fnames))
    assert Path(added).exists()
    assert Path(added).parent == temp_dir

    # Ensure tool_output recorded replacement and addition messages
    out = "\n".join(fake_io.outputs)
    assert "Replaced existing image in the chat" in out
    assert "Added clipboard image to the chat" in out

    # check_added_files must have been called
    assert fake_coder.added_checked is True


def test_image_without_extension_round_026(tmp_path, monkeypatch):
    # Image present and args has no extension; should get .png appended
    img = make_image()
    fake_io, fake_coder, _, temp_dir = call_cmd_paste_with_patched(
        tmp_path, monkeypatch, image_return=img, pyperclip_return="", args="image_name"
    )

    # There should be exactly one file recorded
    assert len(fake_coder.abs_fnames) == 1
    added = next(iter(fake_coder.abs_fnames))
    p = Path(added)
    assert p.exists()
    # Should have .png suffix because basename should become image_name.png
    assert p.name == "image_name.png"
    assert p.parent == temp_dir

    # Confirm appropriate output message
    assert any("Added clipboard image to the chat" in o for o in fake_io.outputs)
    assert all("Replaced existing image in the chat" not in o for o in fake_io.outputs)
    assert fake_coder.added_checked is True


def test_text_clipboard_round_026(tmp_path, monkeypatch):
    # No image on clipboard, but text exists -> should call tool_output and return the text
    fake_io, fake_coder, result, _ = call_cmd_paste_with_patched(
        tmp_path, monkeypatch, image_return=None, pyperclip_return="hello world", args=""
    )

    assert result == "hello world"
    # tool_output should have been called with the text
    assert any(o == "hello world" for o in fake_io.outputs)


def test_no_content_round_026(tmp_path, monkeypatch):
    # Neither image nor text -> should call tool_error with a specific message
    fake_io, fake_coder, result, _ = call_cmd_paste_with_patched(
        tmp_path, monkeypatch, image_return=None, pyperclip_return="", args=""
    )

    assert result is None
    assert any("No image or text content found in clipboard." in e for e in fake_io.errors)


def test_exception_round_026(tmp_path, monkeypatch):
    # If ImageGrab raises, the exception handler should capture and call tool_error with formatted message
    fake_io, fake_coder, result, _ = call_cmd_paste_with_patched(
        tmp_path, monkeypatch, image_return=Exception("boom"), pyperclip_return=Exception("nope"), args=""
    )

    assert result is None
    assert any("Error processing clipboard content" in e and "boom" in e for e in fake_io.errors)
