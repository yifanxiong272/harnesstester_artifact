# file: openhands/runtime/action_execution_server.py:449-516
# asked: {"lines": [449, 450, 453, 454, 456, 457, 458, 459, 460, 461, 464, 465, 466, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 500, 502, 503, 504, 505, 506, 508, 509, 510, 511, 512, 515, 516], "branches": [[453, 454], [453, 456], [456, 457], [456, 472], [475, 476], [475, 485], [480, 481], [480, 482], [485, 486], [485, 491], [491, 492], [491, 502], [496, 497], [496, 498]]}
# gained: {"lines": [449, 450, 453, 454, 456, 457, 458, 459, 460, 461, 464, 465, 466, 472, 473, 474, 475, 476, 477, 478, 479, 480, 482, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 498, 500, 502, 503, 504, 505, 506, 508, 509, 510, 511, 512, 515, 516], "branches": [[453, 454], [453, 456], [456, 457], [456, 472], [475, 476], [475, 485], [480, 482], [485, 486], [485, 491], [491, 492], [491, 502], [496, 498]]}

import asyncio
import base64
import mimetypes
from types import SimpleNamespace

import pytest
from pathlib import Path

import openhands.runtime.action_execution_server as aes
from openhands.events.action.files import FileReadAction
from openhands.events.event import FileReadSource
from openhands.events.observation import ErrorObservation, FileReadObservation


@pytest.mark.asyncio
async def test_read_binary_file(monkeypatch):
    # arrange: monkeypatch is_binary to return True
    monkeypatch.setattr(aes, "is_binary", lambda path: True)

    fake = SimpleNamespace()
    fake.bash_session = SimpleNamespace(cwd="/tmp")
    action = FileReadAction(path="some.bin")

    # act
    obs = await aes.ActionExecutor.read(fake, action)

    # assert
    assert isinstance(obs, ErrorObservation)
    assert "ERROR_BINARY_FILE" in str(obs)


@pytest.mark.asyncio
async def test_read_impl_source_oh_aci(monkeypatch):
    # arrange
    monkeypatch.setattr(aes, "is_binary", lambda path: False)
    # make _execute_file_editor return expected tuple
    monkeypatch.setattr(aes, "_execute_file_editor", lambda editor, **kwargs: ("VIEW_CONTENT", None))

    fake = SimpleNamespace()
    fake.bash_session = SimpleNamespace(cwd="/tmp")
    fake.file_editor = object()  # arbitrary
    action = FileReadAction(path="any.txt", impl_source=FileReadSource.OH_ACI)

    # act
    obs = await aes.ActionExecutor.read(fake, action)

    # assert
    assert isinstance(obs, FileReadObservation)
    assert obs.content == "VIEW_CONTENT"
    assert obs.path == action.path
    assert obs.impl_source == FileReadSource.OH_ACI


@pytest.mark.asyncio
async def test_read_image_pdf_video_and_text_branches(tmp_path, monkeypatch):
    # arrange common
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    fake = SimpleNamespace()
    fake.bash_session = SimpleNamespace(cwd=str(tmp_path))

    def resolve(path, working_dir):
        return str(Path(working_dir) / path)

    fake._resolve_path = resolve

    # prepare image file (.png)
    img_path = tmp_path / "img.PNG"  # uppercase to also test lower() usage
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00"
    img_path.write_bytes(img_bytes)

    action_img = FileReadAction(path="img.PNG")
    obs_img = await aes.ActionExecutor.read(fake, action_img)
    assert isinstance(obs_img, FileReadObservation)
    # check base64 encoding and mime
    expected_img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    mime_img, _ = mimetypes.guess_type(str(img_path))
    if mime_img is None:
        mime_img = "image/png"
    assert obs_img.content == f"data:{mime_img};base64,{expected_img_b64}"
    assert obs_img.path == str(img_path)

    # prepare pdf file
    pdf_path = tmp_path / "doc.pdf"
    pdf_bytes = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
    pdf_path.write_bytes(pdf_bytes)

    action_pdf = FileReadAction(path="doc.pdf")
    obs_pdf = await aes.ActionExecutor.read(fake, action_pdf)
    assert isinstance(obs_pdf, FileReadObservation)
    expected_pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    assert obs_pdf.content == f"data:application/pdf;base64,{expected_pdf_b64}"
    assert obs_pdf.path == str(pdf_path)

    # prepare video file (.mp4)
    video_path = tmp_path / "movie.mp4"
    video_bytes = b"\x00\x00\x00\x20ftypisom"
    video_path.write_bytes(video_bytes)

    action_vid = FileReadAction(path="movie.mp4")
    obs_vid = await aes.ActionExecutor.read(fake, action_vid)
    assert isinstance(obs_vid, FileReadObservation)
    expected_vid_b64 = base64.b64encode(video_bytes).decode("utf-8")
    mime_vid, _ = mimetypes.guess_type(str(video_path))
    if mime_vid is None:
        mime_vid = "video/mp4"
    assert obs_vid.content == f"data:{mime_vid};base64,{expected_vid_b64}"
    assert obs_vid.path == str(video_path)

    # prepare plain text file and test slicing via start/end
    text_path = tmp_path / "notes.txt"
    text_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

    action_text = FileReadAction(path="notes.txt", start=1, end=2)
    obs_text = await aes.ActionExecutor.read(fake, action_text)
    assert isinstance(obs_text, FileReadObservation)
    # only the second line should be returned (index 1 up to 2)
    assert obs_text.content == "line2\n"
    assert obs_text.path == str(text_path)


@pytest.mark.asyncio
async def test_file_not_found_unicode_error_and_is_a_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    fake = SimpleNamespace()
    fake.bash_session = SimpleNamespace(cwd=str(tmp_path))

    def resolve(path, working_dir):
        return str(Path(working_dir) / path)

    fake._resolve_path = resolve

    # 1) FileNotFoundError
    action_missing = FileReadAction(path="does_not_exist.txt")
    obs_missing = await aes.ActionExecutor.read(fake, action_missing)
    assert isinstance(obs_missing, ErrorObservation)
    assert "File not found" in str(obs_missing)
    assert str(tmp_path) in str(obs_missing)

    # 2) UnicodeDecodeError: create a file with invalid utf-8 bytes and try to read as text
    bad_path = tmp_path / "bad.txt"
    bad_path.write_bytes(b"\xff\xff\xff")
    action_bad = FileReadAction(path="bad.txt")
    obs_bad = await aes.ActionExecutor.read(fake, action_bad)
    assert isinstance(obs_bad, ErrorObservation)
    assert "could not be decoded as utf-8" in str(obs_bad).lower()

    # 3) IsADirectoryError: point to a directory
    dir_path = tmp_path / "somedir"
    dir_path.mkdir()
    action_dir = FileReadAction(path="somedir")
    obs_dir = await aes.ActionExecutor.read(fake, action_dir)
    assert isinstance(obs_dir, ErrorObservation)
    assert "is a directory" in str(obs_dir).lower()
