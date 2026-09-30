import asyncio
import base64
import os
from types import SimpleNamespace
from pathlib import Path
import pytest

import openhands.runtime.action_execution_server as aes

# Helper to run the async read method deterministically
def run_read(self_obj, action):
    return asyncio.get_event_loop().run_until_complete(aes.ActionExecutor.read(self_obj, action))

@pytest.fixture(autouse=True)
def patch_observation_constructors(monkeypatch):
    # Replace observation constructors with simple deterministic factories
    monkeypatch.setattr(aes, 'ErrorObservation', lambda msg: {'error': str(msg)})
    monkeypatch.setattr(aes, 'FileReadObservation', lambda **kwargs: {'path': kwargs.get('path'), 'content': kwargs.get('content'), 'impl_source': kwargs.get('impl_source', None)})
    yield

def make_dummy_self(tmp_path):
    # Creates a lightweight 'self' object expected by ActionExecutor.read
    bash_session = SimpleNamespace(cwd=str(tmp_path))
    self_obj = SimpleNamespace(bash_session=bash_session, file_editor=None)

    def _resolve_path(path, working_dir):
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(Path(working_dir) / path)

    self_obj._resolve_path = _resolve_path
    return self_obj

def test_binary_file_round_046(monkeypatch, tmp_path):
    # Ensure binary check short-circuits and returns an ErrorObservation
    monkeypatch.setattr(aes, 'is_binary', lambda path: True)

    self_obj = make_dummy_self(tmp_path)
    action = SimpleNamespace(path='some.bin', impl_source=None, view_range=None, start=None, end=None)

    obs = run_read(self_obj, action)

    assert isinstance(obs, dict)
    assert obs == {'error': 'ERROR_BINARY_FILE'}

def test_oh_aci_file_read_round_046(monkeypatch, tmp_path):
    # When impl_source == OH_ACI the file_editor path is used via _execute_file_editor
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)
    # Provide a sentinel OH_ACI and patch the module symbol to match
    monkeypatch.setattr(aes, 'FileReadSource', SimpleNamespace(OH_ACI='OH_ACI'))
    # Return synthetic editor content
    monkeypatch.setattr(aes, '_execute_file_editor', lambda editor, command, path, view_range: ('EDITOR_CONTENT', None))

    self_obj = make_dummy_self(tmp_path)
    action = SimpleNamespace(path='ignored', impl_source='OH_ACI', view_range=None, start=None, end=None)

    obs = run_read(self_obj, action)

    assert obs['content'] == 'EDITOR_CONTENT'
    assert obs['impl_source'] == 'OH_ACI'
    assert obs['path'] == 'ignored'

def test_image_mime_default_and_explicit_round_046(monkeypatch, tmp_path):
    # Test both branches for image mime_type being None and not-None
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    # Create a small binary file representing an image
    img_bytes = b"\x89PNGTEST"
    img_path = tmp_path / 'pic.png'
    img_path.write_bytes(img_bytes)

    self_obj = make_dummy_self(tmp_path)

    # Case A: mimetypes.guess_type returns None -> default 'image/png'
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda path: (None, None))
    action = SimpleNamespace(path=str(img_path), impl_source=None, view_range=None, start=None, end=None)
    obs = run_read(self_obj, action)

    expected_b64 = base64.b64encode(img_bytes).decode('utf-8')
    assert obs['content'] == f'data:image/png;base64,{expected_b64}'
    assert obs['path'] == str(img_path)

    # Case B: mimetypes.guess_type returns a real mime type -> use that
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda path: ('image/jpeg', None))
    obs2 = run_read(self_obj, action)
    assert obs2['content'] == f'data:image/jpeg;base64,{expected_b64}'

def test_pdf_and_video_and_text_errors_round_046(monkeypatch, tmp_path):
    # Cover PDF and video encodings and error cases (FileNotFoundError, IsADirectoryError)
    monkeypatch.setattr(aes, 'is_binary', lambda path: False)

    # PDF file
    pdf_bytes = b"%PDF-1.4 PDFDATA"
    pdf_path = tmp_path / 'doc.pdf'
    pdf_path.write_bytes(pdf_bytes)

    self_obj = make_dummy_self(tmp_path)

    action_pdf = SimpleNamespace(path=str(pdf_path), impl_source=None, view_range=None, start=None, end=None)
    obs_pdf = run_read(self_obj, action_pdf)
    expected_pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    assert obs_pdf['content'] == f'data:application/pdf;base64,{expected_pdf_b64}'

    # Video file with missing mime type -> default to video/mp4
    vid_bytes = b"VIDDATA"
    vid_path = tmp_path / 'movie.mp4'
    vid_path.write_bytes(vid_bytes)
    action_vid = SimpleNamespace(path=str(vid_path), impl_source=None, view_range=None, start=None, end=None)
    monkeypatch.setattr(aes.mimetypes, 'guess_type', lambda path: (None, None))
    obs_vid = run_read(self_obj, action_vid)
    expected_vid_b64 = base64.b64encode(vid_bytes).decode('utf-8')
    assert obs_vid['content'] == f'data:video/mp4;base64,{expected_vid_b64}'

    # File not found -> FileNotFoundError branch
    missing_path = tmp_path / 'does_not_exist.txt'
    action_nf = SimpleNamespace(path=str(missing_path), impl_source=None, view_range=None, start=None, end=None)
    nf_obs = run_read(self_obj, action_nf)
    # ErrorObservation factory returns dict with 'error' key
    assert 'File not found:' in nf_obs['error']
    assert str(self_obj.bash_session.cwd) in nf_obs['error']

    # Is a directory -> IsADirectoryError branch
    dir_path = tmp_path / 'somedir'
    dir_path.mkdir()
    action_dir = SimpleNamespace(path=str(dir_path), impl_source=None, view_range=None, start=None, end=None)
    dir_obs = run_read(self_obj, action_dir)
    assert 'Path is a directory' in dir_obs['error']


# Keep tests deterministic and avoid any network or external services.
