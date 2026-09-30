import os
import shutil
import tempfile
from pathlib import Path
import pytest
from PIL import Image
import aider.commands as commands


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        self.outputs.append(str(msg))

    def tool_error(self, msg):
        self.errors.append(str(msg))


class DummyCoder:
    def __init__(self, initial=None):
        # abs_fnames behaves like a set in the real code
        self.abs_fnames = set(initial or [])
        self.added_files_checked = False

    def check_added_files(self):
        # no-op for tests, but record it was called
        self.added_files_checked = True


def make_commands(io=None, coder=None):
    io = io or DummyIO()
    coder = coder or DummyCoder()
    # Commands.__init__(self, io, coder, voice_language, voice_input_device,
    # voice_format, verify_ssl, args, parser, verbose, editor,
    # original_read_only_fnames)
    return commands.Commands(io, coder, None, None, None, False, None, None, False, None, None)


def _get_only_path_from_coder(coder):
    assert len(coder.abs_fnames) == 1
    return next(iter(coder.abs_fnames))


def test_paste_image_with_ext_round_027(monkeypatch, tmp_path):
    # Image present, filename with .jpg extension should be kept as-is
    image = Image.new("RGB", (1, 1), "white")
    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", lambda: image)

    io = DummyIO()
    coder = DummyCoder()
    cmd = make_commands(io=io, coder=coder)

    # call with a named file that includes .jpg extension
    cmd.cmd_paste("my_pic.jpg")

    # One file added and check message
    added = _get_only_path_from_coder(coder)
    assert added.endswith("my_pic.jpg")
    assert any("Added clipboard image to the chat:" in o for o in io.outputs)

    # file was saved on disk; cleanup
    p = Path(added)
    try:
        assert p.exists()
    finally:
        # remove file and its temp dir
        shutil.rmtree(p.parent)


def test_paste_image_without_ext_round_027(monkeypatch, tmp_path):
    # Image present, filename without extension should get .png appended
    image = Image.new("RGB", (1, 1), "white")
    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", lambda: image)

    io = DummyIO()
    coder = DummyCoder()
    cmd = make_commands(io=io, coder=coder)

    cmd.cmd_paste("simple_name")

    added = _get_only_path_from_coder(coder)
    assert added.endswith("simple_name.png")
    assert any("Added clipboard image to the chat:" in o for o in io.outputs)

    p = Path(added)
    try:
        assert p.exists()
    finally:
        shutil.rmtree(p.parent)


def test_paste_image_replace_existing_round_027(monkeypatch, tmp_path):
    # If an existing file with the same name is in coder.abs_fnames, it should be removed
    image = Image.new("RGB", (1, 1), "white")
    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", lambda: image)

    # create a temp dir and an existing file named clipboard_image.png
    temp_dir = tempfile.mkdtemp()
    existing_path = os.path.join(temp_dir, "clipboard_image.png")
    # create the file so Path(...).name matches
    Image.new("RGB", (1, 1), "white").save(existing_path, "PNG")

    io = DummyIO()
    coder = DummyCoder(initial={os.path.abspath(existing_path)})
    cmd = make_commands(io=io, coder=coder)

    try:
        cmd.cmd_paste("")  # empty args -> basename = clipboard_image.png

        # the existing path should have been removed and a new path added
        assert all(existing_path not in coder.abs_fnames for existing_path in [os.path.abspath(existing_path)])
        assert any("Replaced existing image in the chat:" in o for o in io.outputs)
        assert any("Added clipboard image to the chat:" in o for o in io.outputs)

        # there should still be exactly one file in abs_fnames (the new one)
        assert len(coder.abs_fnames) == 1
        new_path = _get_only_path_from_coder(coder)
        assert Path(new_path).name == "clipboard_image.png"
        assert Path(new_path).exists()
    finally:
        # cleanup both temp dirs: original and new
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        # try to remove new path if present
        if 'new_path' in locals():
            try:
                shutil.rmtree(Path(new_path).parent)
            except Exception:
                pass


def test_paste_text_round_027(monkeypatch):
    # No image, but text present should be output and returned
    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", lambda: None)
    monkeypatch.setattr(commands.pyperclip, "paste", lambda: "hello from clipboard")

    io = DummyIO()
    coder = DummyCoder()
    cmd = make_commands(io=io, coder=coder)

    ret = cmd.cmd_paste("   \t \n   ")  # whitespace args, but irrelevant for text branch
    assert ret == "hello from clipboard"
    assert any("hello from clipboard" in o for o in io.outputs)


def test_paste_no_content_round_027(monkeypatch):
    # Neither image nor text -> tool_error called with specific message
    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", lambda: None)
    monkeypatch.setattr(commands.pyperclip, "paste", lambda: "")

    io = DummyIO()
    coder = DummyCoder()
    cmd = make_commands(io=io, coder=coder)

    ret = cmd.cmd_paste("")
    assert ret is None
    assert any("No image or text content found in clipboard." in e for e in io.errors)


def test_paste_exception_round_027(monkeypatch):
    # If ImageGrab or processing raises, the error is reported through tool_error
    def raise_error():
        raise ValueError("boom")

    monkeypatch.setattr(commands.ImageGrab, "grabclipboard", raise_error)

    io = DummyIO()
    coder = DummyCoder()
    cmd = make_commands(io=io, coder=coder)

    ret = cmd.cmd_paste("anything")
    assert ret is None
    # Ensure the error message includes the exception text
    assert any("Error processing clipboard content: boom" in e for e in io.errors)
