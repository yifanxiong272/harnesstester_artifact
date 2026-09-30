import os
import tempfile
import base64
import asyncio
from types import SimpleNamespace
import openhands.runtime.action_execution_server as aes
import mimetypes


def make_fake_self(tmpdir):
    class FakeBashSession:
        def __init__(self, cwd):
            self.cwd = cwd

    class FakeSelf:
        def __init__(self, cwd):
            self.bash_session = FakeBashSession(cwd)
            self.file_editor = None

        def _resolve_path(self, path, working_dir):
            # If an absolute path was provided, return as-is, otherwise join with cwd
            return path if os.path.isabs(path) else os.path.join(working_dir, path)

    return FakeSelf(tmpdir)


def make_action(path, impl_source=None, start=0, end=None):
    # lightweight stand-in for the real FileReadAction
    return SimpleNamespace(path=path, impl_source=impl_source, view_range=None, start=start, end=end)


def run_read(fake_self, action):
    # Helper to run the async read coroutine deterministically
    coro = aes.ActionExecutor.read(fake_self, action)
    return asyncio.run(coro)


def test_read_returns_error_for_binary_round_046(monkeypatch, tmp_path):
    # Arrange: force is_binary to return True so the binary-file early-return branch executes
    monkeypatch.setattr(aes, "is_binary", lambda path: True)

    fake = make_fake_self(str(tmp_path))
    action = make_action("somefile.png", impl_source=None)

    # Act
    obs = run_read(fake, action)

    # Assert: ErrorObservation with expected error code
    assert isinstance(obs, aes.ErrorObservation)
    assert "ERROR_BINARY_FILE" in getattr(obs, "message", str(obs))


def test_read_image_with_unknown_mime_round_046(monkeypatch, tmp_path):
    # Arrange: ensure is_binary returns False so image branch is considered
    monkeypatch.setattr(aes, "is_binary", lambda path: False)
    # Force mimetypes to return None so the default MIME branch is taken
    monkeypatch.setattr(mimetypes, "guess_type", lambda p: (None, None))

    fake = make_fake_self(str(tmp_path))
    # create a small binary file that will be base64-encoded
    fname = tmp_path / "pic.PNG"
    data = b"\x89PNG\r\nTESTDATA"
    fname.write_bytes(data)

    action = make_action(str(fname), impl_source=None)

    # Act
    obs = run_read(fake, action)

    # Assert: FileReadObservation and content starts with the default png data URI prefix
    assert isinstance(obs, aes.FileReadObservation)
    assert isinstance(obs.content, str)
    assert obs.content.startswith("data:image/png;base64,")
    # ensure the base64 payload decodes to original bytes suffix (basic sanity)
    payload = obs.content.split(",", 1)[1]
    decoded = base64.b64decode(payload)
    assert decoded.endswith(b"TESTDATA")


def test_read_pdf_round_046(monkeypatch, tmp_path):
    # Arrange: non-binary detection and create a pdf file
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    fake = make_fake_self(str(tmp_path))
    fname = tmp_path / "doc.pdf"
    pdf_bytes = b"%PDF-1.4\n%EOF"
    fname.write_bytes(pdf_bytes)

    action = make_action(str(fname), impl_source=None)

    # Act
    obs = run_read(fake, action)

    # Assert: PDF is returned as a data URI for application/pdf
    assert isinstance(obs, aes.FileReadObservation)
    assert obs.content.startswith("data:application/pdf;base64,")
    payload = obs.content.split(",", 1)[1]
    assert base64.b64decode(payload).startswith(b"%PDF")


def test_read_video_with_unknown_mime_round_046(monkeypatch, tmp_path):
    # Arrange: ensure mimetype detection fails so default video mime is used
    monkeypatch.setattr(aes, "is_binary", lambda path: False)
    monkeypatch.setattr(mimetypes, "guess_type", lambda p: (None, None))

    fake = make_fake_self(str(tmp_path))
    fname = tmp_path / "movie.MP4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00"
    fname.write_bytes(video_bytes)

    action = make_action(str(fname), impl_source=None)

    # Act
    obs = run_read(fake, action)

    # Assert: video returned with default video MIME data URI
    assert isinstance(obs, aes.FileReadObservation)
    assert obs.content.startswith("data:video/mp4;base64,")
    payload = obs.content.split(",", 1)[1]
    assert base64.b64decode(payload).startswith(b"\x00\x00\x00")


def test_read_file_not_found_and_decode_and_isdir_round_046(monkeypatch, tmp_path):
    # This test covers three exception branches by invoking read with paths that cause
    # FileNotFoundError, UnicodeDecodeError, and IsADirectoryError.
    monkeypatch.setattr(aes, "is_binary", lambda path: False)

    fake = make_fake_self(str(tmp_path))

    # 1) FileNotFoundError
    missing_path = "does_not_exist.txt"
    action_missing = make_action(missing_path, impl_source=None)
    obs_missing = run_read(fake, action_missing)
    assert isinstance(obs_missing, aes.ErrorObservation)
    # message should include the missing path and current working directory
    assert "File not found:" in getattr(obs_missing, "message", str(obs_missing))
    assert str(tmp_path) in getattr(obs_missing, "message", str(obs_missing))

    # 2) UnicodeDecodeError
    # Create a file with invalid UTF-8 bytes so opening in text mode raises
    bad_fname = tmp_path / "bad.txt"
    bad_fname.write_bytes(b"\xff\xff\xff")
    action_bad = make_action(str(bad_fname), impl_source=None)
    obs_bad = run_read(fake, action_bad)
    assert isinstance(obs_bad, aes.ErrorObservation)
    assert "could not be decoded as utf-8" in getattr(obs_bad, "message", str(obs_bad))

    # 3) IsADirectoryError
    dir_path = tmp_path / "somedir"
    dir_path.mkdir()
    action_dir = make_action(str(dir_path), impl_source=None)
    obs_dir = run_read(fake, action_dir)
    assert isinstance(obs_dir, aes.ErrorObservation)
    assert "Path is a directory" in getattr(obs_dir, "message", str(obs_dir))
