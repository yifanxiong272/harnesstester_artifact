import asyncio
import base64
import os
from types import SimpleNamespace
import pathlib
import builtins

import pytest

import openhands.runtime.action_execution_server as aes
from openhands.events.event import FileReadSource
from openhands.events.observation import FileReadObservation, ErrorObservation


def _make_executor(tmp_path):
    # Create an instance without running __init__ and set required attributes
    executor = aes.ActionExecutor.__new__(aes.ActionExecutor)
    # Simulate a bash session with cwd
    executor.bash_session = SimpleNamespace(cwd=str(tmp_path))
    executor.file_editor = None

    # _resolve_path should mirror how the real function would resolve; here keep simple
    def _resolve_path(path, working_dir):
        p = pathlib.Path(path)
        if p.is_absolute():
            return str(p)
        return str(pathlib.Path(working_dir) / path)

    executor._resolve_path = _resolve_path
    return executor


def test_read_binary_round_046(tmp_path, monkeypatch):
    # Simulate a binary file detection causing early ErrorObservation
    monkeypatch.setattr(aes, 'is_binary', lambda path: True)

    executor = _make_executor(tmp_path)

    action = SimpleNamespace(path=str(tmp_path / "some.bin"), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, ErrorObservation)
    assert 'ERROR_BINARY_FILE' in str(obs)


def test_read_image_fallback_round_046(tmp_path, monkeypatch):
    # Image file where mimetypes cannot determine type -> fallback to image/png
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda p: (None, None))

    image_path = tmp_path / "pic.PNG"  # case-insensitive match
    image_bytes = b"\x89PNG\r\n\x1a\nabc"
    image_path.write_bytes(image_bytes)

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(image_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, FileReadObservation)
    assert obs.path == str(image_path)
    assert obs.content.startswith('data:image/png;base64,')
    # verify base64 payload decodes back to original bytes
    payload = obs.content.split(',', 1)[1]
    assert base64.b64decode(payload) == image_bytes


def test_read_image_with_mime_round_046(tmp_path, monkeypatch):
    # Image file where mimetypes returns a specific type (image/jpeg)
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda p: ('image/jpeg', None))

    image_path = tmp_path / "photo.jpg"
    image_bytes = b"JPEGDATA"
    image_path.write_bytes(image_bytes)

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(image_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, FileReadObservation)
    assert obs.path == str(image_path)
    assert obs.content.startswith('data:image/jpeg;base64,')
    payload = obs.content.split(',', 1)[1]
    assert base64.b64decode(payload) == image_bytes


def test_read_pdf_round_046(tmp_path, monkeypatch):
    # PDF branch should return application/pdf data URI
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    pdf_path = tmp_path / "doc.PDF"
    pdf_bytes = b"%PDF-1.4\n%EOF"
    pdf_path.write_bytes(pdf_bytes)

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(pdf_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, FileReadObservation)
    assert obs.path == str(pdf_path)
    assert obs.content.startswith('data:application/pdf;base64,')
    payload = obs.content.split(',', 1)[1]
    assert base64.b64decode(payload) == pdf_bytes


def test_read_video_fallback_round_046(tmp_path, monkeypatch):
    # Video branch with unknown mimetype should fallback to video/mp4
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda p: (None, None))

    vid_path = tmp_path / "movie.MP4"
    video_bytes = b"VIDEODATA"
    vid_path.write_bytes(video_bytes)

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(vid_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, FileReadObservation)
    assert obs.path == str(vid_path)
    assert obs.content.startswith('data:video/mp4;base64,')
    payload = obs.content.split(',', 1)[1]
    assert base64.b64decode(payload) == video_bytes


def test_read_text_lines_round_046(tmp_path, monkeypatch):
    # Read a text file and ensure read_lines usage returns joined content
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    txt_path = tmp_path / "file.txt"
    txt_path.write_text('line1\nline2\nline3\n')

    executor = _make_executor(tmp_path)
    # ask to read only a slice via start/end to exercise read_lines trimming
    action = SimpleNamespace(path=str(txt_path), impl_source=None, view_range=None, start=1, end=2)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, FileReadObservation)
    # read_lines returns the selected lines joined
    assert obs.content == 'line2\n'


def test_read_file_not_found_round_046(tmp_path, monkeypatch):
    # _resolve_path returns a non-existent path -> FileNotFoundError branch
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    executor = _make_executor(tmp_path)

    # Make resolve path point to a missing file
    executor._resolve_path = lambda path, cwd: str(tmp_path / "does_not_exist.txt")

    action = SimpleNamespace(path='does_not_exist.txt', impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, ErrorObservation)
    assert 'File not found:' in str(obs)
    assert str(tmp_path) in str(obs)


def test_read_unicode_decode_error_round_046(tmp_path, monkeypatch):
    # Create a file that will raise UnicodeDecodeError when opened in 'r' encoding='utf-8'
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    bad_path = tmp_path / "bad.txt"
    # write bytes that are invalid UTF-8 sequence
    bad_path.write_bytes(b"\xff\xff\xff")

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(bad_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, ErrorObservation)
    assert 'could not be decoded as utf-8' in str(obs).lower()


def test_read_is_directory_round_046(tmp_path, monkeypatch):
    # If path resolves to a directory, open(..., 'r') raises IsADirectoryError
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    dir_path = tmp_path / "somedir"
    dir_path.mkdir()

    executor = _make_executor(tmp_path)
    action = SimpleNamespace(path=str(dir_path), impl_source=None, view_range=None, start=None, end=None)

    obs = asyncio.run(executor.read(action))
    assert isinstance(obs, ErrorObservation)
    assert 'path is a directory' in str(obs).lower()
