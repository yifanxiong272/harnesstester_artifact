import asyncio
import base64
import importlib
import os
import tempfile
import types
import builtins
import mimetypes

import pytest

module = importlib.import_module('openhands.runtime.action_execution_server')
from openhands.events.event import FileReadSource
from openhands.events.observation import FileReadObservation, ErrorObservation

# A minimal dummy executor instance that has the attributes used by ActionExecutor.read
class DummyExecutor:
    def __init__(self, cwd, resolve_map=None, file_editor=None):
        self.bash_session = types.SimpleNamespace(cwd=cwd)
        self.file_editor = file_editor
        # resolve_map: mapping from requested action.path -> actual filesystem path
        self._resolve_map = resolve_map or {}

    def _resolve_path(self, path, working_dir):
        # mimic resolution: prefer explicit mapping else join with cwd
        if path in self._resolve_map:
            return self._resolve_map[path]
        return os.path.join(working_dir, path)


@pytest.mark.asyncio
async def test_read_binary_round_046(monkeypatch, tmp_path):
    """
    Cover binary-file early return branch (line ~453-454).
    Oracle: returns an ErrorObservation containing the string 'ERROR_BINARY_FILE'.
    """
    # Ensure is_binary returns True for this path
    monkeypatch.setattr(module, 'is_binary', lambda p: True)

    ex = DummyExecutor(str(tmp_path))
    action = types.SimpleNamespace(path='some.bin', impl_source=None, view_range=None, start=None, end=None)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, ErrorObservation)
    # Ensure the message passed into the observation contains the error string
    assert any('ERROR_BINARY_FILE' == v or ('ERROR_BINARY_FILE' in str(v)) for v in vars(obs).values())


@pytest.mark.asyncio
async def test_read_oh_aci_round_046(monkeypatch, tmp_path):
    """
    Cover the OH_ACI path that calls _execute_file_editor (lines ~456-468).
    Oracle: returns a FileReadObservation with content equal to the editor result string.
    """
    # monkeypatch the module-level _execute_file_editor to return deterministic content
    monkeypatch.setattr(module, '_execute_file_editor', lambda editor, command, path, view_range: ('EDITOR_CONTENT', None))

    ex = DummyExecutor(str(tmp_path), file_editor=object())
    action = types.SimpleNamespace(path='ignored', impl_source=FileReadSource.OH_ACI, view_range=(1, 2), start=None, end=None)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, FileReadObservation)
    assert getattr(obs, 'content', None) == 'EDITOR_CONTENT'
    assert getattr(obs, 'path', None) == action.path


@pytest.mark.asyncio
async def test_read_image_default_mime_round_046(monkeypatch, tmp_path):
    """
    Cover image branch where mimetypes.guess_type returns None so default image/png is used
    (lines ~475-484). Assert returned data URL decodes back to original bytes.
    """
    # create a small binary image-like payload
    img_bytes = b'PNG_BYTES_EXAMPLE'
    img_path = tmp_path / 'pic.jpg'
    img_path.write_bytes(img_bytes)

    # Ensure is_binary returns False so code proceeds to file checks
    monkeypatch.setattr(module, 'is_binary', lambda p: False)
    # Force mimetypes.guess_type to return (None, None) to hit default mime branch
    monkeypatch.setattr(mimetypes, 'guess_type', lambda p: (None, None))

    ex = DummyExecutor(str(tmp_path), resolve_map={'pic.jpg': str(img_path)})
    action = types.SimpleNamespace(path='pic.jpg', impl_source=None, view_range=None, start=None, end=None)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, FileReadObservation)
    content = getattr(obs, 'content', '')
    assert content.startswith('data:image/png;base64,')
    payload = content.split(',', 1)[1]
    assert base64.b64decode(payload.encode('utf-8')) == img_bytes


@pytest.mark.asyncio
async def test_read_pdf_round_046(monkeypatch, tmp_path):
    """
    Cover PDF branch (lines ~485-490). Assert returned data URL and payload matches file bytes.
    """
    pdf_bytes = b'%PDF-1.4\n%EOF'
    pdf_path = tmp_path / 'doc.pdf'
    pdf_path.write_bytes(pdf_bytes)

    monkeypatch.setattr(module, 'is_binary', lambda p: False)

    ex = DummyExecutor(str(tmp_path), resolve_map={'doc.pdf': str(pdf_path)})
    action = types.SimpleNamespace(path='doc.pdf', impl_source=None, view_range=None, start=None, end=None)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, FileReadObservation)
    content = getattr(obs, 'content', '')
    assert content.startswith('data:application/pdf;base64,')
    payload = content.split(',', 1)[1]
    assert base64.b64decode(payload.encode('utf-8')) == pdf_bytes


@pytest.mark.asyncio
async def test_read_video_default_mime_round_046(monkeypatch, tmp_path):
    """
    Cover video branch where mimetypes.guess_type returns None and default mime 'video/mp4' is used
    (lines ~491-500). Assert returned data URL decodes back to original bytes.
    """
    video_bytes = b'VIDEO_BYTES'
    video_path = tmp_path / 'movie.webm'
    video_path.write_bytes(video_bytes)

    monkeypatch.setattr(module, 'is_binary', lambda p: False)
    monkeypatch.setattr(mimetypes, 'guess_type', lambda p: (None, None))

    ex = DummyExecutor(str(tmp_path), resolve_map={'movie.webm': str(video_path)})
    action = types.SimpleNamespace(path='movie.webm', impl_source=None, view_range=None, start=None, end=None)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, FileReadObservation)
    content = getattr(obs, 'content', '')
    assert content.startswith('data:video/mp4;base64,')
    payload = content.split(',', 1)[1]
    assert base64.b64decode(payload.encode('utf-8')) == video_bytes


@pytest.mark.asyncio
async def test_read_not_found_round_046(monkeypatch, tmp_path):
    """
    Trigger FileNotFoundError (line ~504-507). Oracle: returns ErrorObservation that mentions 'File not found' and includes path and working directory.
    """
    monkeypatch.setattr(module, 'is_binary', lambda p: False)

    # Map the action path to a non-existing file
    nonexist = str(tmp_path / 'no_such_file.txt')
    ex = DummyExecutor(str(tmp_path), resolve_map={'no_such_file.txt': nonexist})
    action = types.SimpleNamespace(path='no_such_file.txt', impl_source=None, view_range=None, start=0, end=10)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, ErrorObservation)
    all_vals = ' '.join(str(v) for v in vars(obs).values())
    assert 'File not found' in all_vals
    assert nonexist in all_vals
    assert str(tmp_path) in all_vals


@pytest.mark.asyncio
async def test_read_unicode_decode_error_round_046(monkeypatch, tmp_path):
    """
    Trigger UnicodeDecodeError handler (line ~508-509) by monkeypatching builtins.open for a specific path.
    Oracle: returns ErrorObservation mentioning that file could not be decoded as utf-8.
    """
    monkeypatch.setattr(module, 'is_binary', lambda p: False)

    bad_path = tmp_path / 'bad.txt'
    bad_path.write_bytes(b"\xff\xff\xff")

    ex = DummyExecutor(str(tmp_path), resolve_map={'bad.txt': str(bad_path)})
    action = types.SimpleNamespace(path='bad.txt', impl_source=None, view_range=None, start=0, end=10)

    # Replace builtins.open to raise UnicodeDecodeError when opening this file in text mode
    orig_open = builtins.open

    def fake_open(path, mode='r', *args, **kwargs):
        # only raise for the target file when opened in text mode
        if os.path.abspath(path) == os.path.abspath(str(bad_path)) and 'b' not in mode:
            raise UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        return orig_open(path, mode, *args, **kwargs)

    # Patch builtins.open (open is a builtin, not module attribute)
    monkeypatch.setattr(builtins, 'open', fake_open)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, ErrorObservation)
    all_vals = ' '.join(str(v) for v in vars(obs).values())
    assert 'could not be decoded as utf-8' in all_vals or 'could not be decoded' in all_vals


@pytest.mark.asyncio
async def test_read_is_directory_round_046(monkeypatch, tmp_path):
    """
    Trigger IsADirectoryError handler (lines ~510-513) by resolving to a directory.
    Oracle: returns ErrorObservation that mentions 'Path is a directory'.
    """
    monkeypatch.setattr(module, 'is_binary', lambda p: False)

    dir_path = tmp_path / 'somedir'
    dir_path.mkdir()

    ex = DummyExecutor(str(tmp_path), resolve_map={'somedir': str(dir_path)})
    action = types.SimpleNamespace(path='somedir', impl_source=None, view_range=None, start=0, end=10)

    obs = await module.ActionExecutor.read(ex, action)
    assert isinstance(obs, ErrorObservation)
    all_vals = ' '.join(str(v) for v in vars(obs).values())
    assert 'directory' in all_vals
