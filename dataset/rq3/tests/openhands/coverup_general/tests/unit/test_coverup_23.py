# file: openhands/runtime/action_execution_server.py:449-516
# asked: {"lines": [449, 450, 453, 454, 456, 457, 458, 459, 460, 461, 464, 465, 466, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 500, 502, 503, 504, 505, 506, 508, 509, 510, 511, 512, 515, 516], "branches": [[453, 454], [453, 456], [456, 457], [456, 472], [475, 476], [475, 485], [480, 481], [480, 482], [485, 486], [485, 491], [491, 492], [491, 502], [496, 497], [496, 498]]}
# gained: {"lines": [449, 450, 453, 454, 456, 457, 458, 459, 460, 461, 464, 465, 466, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 500, 502, 503, 504, 505, 506, 508, 509, 510, 511, 512, 515, 516], "branches": [[453, 454], [453, 456], [456, 457], [456, 472], [475, 476], [475, 485], [480, 481], [485, 486], [485, 491], [491, 492], [491, 502], [496, 497]]}

import asyncio
import base64
import os
from types import SimpleNamespace

import pytest

import openhands.runtime.action_execution_server as aes
from openhands.events.action.files import FileReadAction
from openhands.events.event import FileReadSource
from openhands.events.observation import FileReadObservation, ErrorObservation


def _contains_error_text(obs: ErrorObservation, text: str) -> bool:
    # Check multiple possible locations for the error text to be stored/represented
    if text in getattr(obs, "error_id", ""):
        return True
    if text in getattr(obs, "observation", ""):
        return True
    try:
        msg = getattr(obs, "message", None)
        if msg and text in msg:
            return True
    except Exception:
        pass
    # Fallback to string representation
    try:
        if text in str(obs):
            return True
    except Exception:
        pass
    return False


@pytest.mark.asyncio
async def test_read_binary_file(monkeypatch):
    # Make is_binary return True to trigger binary error branch
    monkeypatch.setattr(aes, "is_binary", lambda path: True)

    executor = aes.ActionExecutor.__new__(aes.ActionExecutor)
    executor.bash_session = SimpleNamespace(cwd=str(os.getcwd()))
    action = FileReadAction(path="some_binary_file")

    obs = await executor.read(action)
    assert isinstance(obs, ErrorObservation)
    assert _contains_error_text(obs, "ERROR_BINARY_FILE")


@pytest.mark.asyncio
async def test_read_oh_aci_invokes_editor(monkeypatch):
    # Ensure not binary
    monkeypatch.setattr(aes, "is_binary", lambda path: False)
    # Mock the internal editor executor
    monkeypatch.setattr(aes, "_execute_file_editor", lambda editor, command, path, view_range: ("editor-view", None))

    executor = aes.ActionExecutor.__new__(aes.ActionExecutor)
    executor.bash_session = SimpleNamespace(cwd=str(os.getcwd()))
    executor.file_editor = object()

    action = FileReadAction(path="irrelevant", impl_source=FileReadSource.OH_ACI, view_range=None)
    obs = await executor.read(action)
    assert isinstance(obs, FileReadObservation)
    assert obs.content == "editor-view"
    # impl_source may be set on the observation
    assert getattr(obs, "impl_source", FileReadSource.OH_ACI) == FileReadSource.OH_ACI


@pytest.mark.asyncio
async def test_read_image_pdf_video_and_text(tmp_path, monkeypatch):
    # Prepare files
    img_path = tmp_path / "pic.png"
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
    img_path.write_bytes(img_bytes)

    pdf_path = tmp_path / "doc.pdf"
    pdf_bytes = b"%PDF-1.4\n%EOF\n"
    pdf_path.write_bytes(pdf_bytes)

    vid_path = tmp_path / "movie.mp4"
    vid_bytes = b"\x00\x00\x00\x18ftypmp42"
    vid_path.write_bytes(vid_bytes)

    txt_path = tmp_path / "file.txt"
    txt_content = "line1\nline2\n"
    txt_path.write_text(txt_content, encoding="utf-8")

    # Not binary for all these tests
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    # IMAGE: force guess_type to return None to hit the default mime branch
    monkeypatch.setattr(aes.mimetypes, "guess_type", lambda p: (None, None))
    executor = aes.ActionExecutor.__new__(aes.ActionExecutor)
    executor.bash_session = SimpleNamespace(cwd=str(tmp_path))
    # resolve returns absolute path
    executor._resolve_path = lambda path, wd: str((tmp_path / path) if not os.path.isabs(path) else path)

    # Image test
    action_img = FileReadAction(path="pic.png")
    obs_img = await executor.read(action_img)
    assert isinstance(obs_img, FileReadObservation)
    assert obs_img.path.endswith("pic.png")
    assert obs_img.content.startswith("data:image/png;base64,")
    decoded_img = base64.b64decode(obs_img.content.split(",", 1)[1])
    assert decoded_img == img_bytes

    # PDF test
    monkeypatch.setattr(aes.mimetypes, "guess_type", lambda p: ("application/pdf", None))
    action_pdf = FileReadAction(path="doc.pdf")
    obs_pdf = await executor.read(action_pdf)
    assert isinstance(obs_pdf, FileReadObservation)
    assert obs_pdf.content.startswith("data:application/pdf;base64,")
    decoded_pdf = base64.b64decode(obs_pdf.content.split(",", 1)[1])
    assert decoded_pdf == pdf_bytes

    # VIDEO test: force guess_type None to hit default video mime branch
    monkeypatch.setattr(aes.mimetypes, "guess_type", lambda p: (None, None))
    action_vid = FileReadAction(path="movie.mp4")
    obs_vid = await executor.read(action_vid)
    assert isinstance(obs_vid, FileReadObservation)
    assert obs_vid.content.startswith("data:video/mp4;base64,")
    decoded_vid = base64.b64decode(obs_vid.content.split(",", 1)[1])
    assert decoded_vid == vid_bytes

    # TEXT test
    monkeypatch.setattr(aes.mimetypes, "guess_type", lambda p: ("text/plain", None))
    action_txt = FileReadAction(path="file.txt")
    obs_txt = await executor.read(action_txt)
    assert isinstance(obs_txt, FileReadObservation)
    assert obs_txt.content == txt_content


@pytest.mark.asyncio
async def test_file_not_found_unicode_error_and_is_directory(tmp_path, monkeypatch):
    # Ensure not binary
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    executor = aes.ActionExecutor.__new__(aes.ActionExecutor)
    executor.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # 1) FileNotFoundError: resolve to non-existent file
    def resolve_nonexistent(path, wd):
        return str(tmp_path / "does_not_exist.txt")

    executor._resolve_path = resolve_nonexistent
    action_nf = FileReadAction(path="does_not_exist.txt")
    obs_nf = await executor.read(action_nf)
    assert isinstance(obs_nf, ErrorObservation)
    assert _contains_error_text(obs_nf, "File not found:")
    assert _contains_error_text(obs_nf, str(tmp_path))

    # 2) UnicodeDecodeError: create a file with invalid utf-8 bytes
    bad_file = tmp_path / "bad.txt"
    bad_file.write_bytes(b"\xff\xfe\xff")
    executor._resolve_path = lambda path, wd: str(bad_file)
    action_bad = FileReadAction(path="bad.txt")
    obs_bad = await executor.read(action_bad)
    assert isinstance(obs_bad, ErrorObservation)
    assert _contains_error_text(obs_bad, "File could not be decoded as utf-8")

    # 3) IsADirectoryError: resolve to a directory
    dir_path = tmp_path / "somedir"
    dir_path.mkdir()
    executor._resolve_path = lambda path, wd: str(dir_path)
    action_dir = FileReadAction(path="somedir")
    obs_dir = await executor.read(action_dir)
    assert isinstance(obs_dir, ErrorObservation)
    assert _contains_error_text(obs_dir, "Path is a directory")
