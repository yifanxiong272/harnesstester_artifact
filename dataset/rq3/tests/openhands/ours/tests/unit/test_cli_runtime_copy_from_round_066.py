import os
import tempfile
import zipfile
from pathlib import Path
import pytest

import openhands.runtime.impl.cli.cli_runtime as cli_module
from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


def _make_instance(runtime_initialized: bool = True, sanitize_ret=None):
    """Create a CLIRuntime instance without running __init__, set minimal attributes used by copy_from."""
    inst = CLIRuntime.__new__(CLIRuntime)
    inst._runtime_initialized = runtime_initialized
    # default sanitizer returns what is passed through
    if sanitize_ret is None:
        inst._sanitize_filename = lambda p: p
    else:
        inst._sanitize_filename = lambda p: sanitize_ret
    return inst


def test_copy_from_not_initialized_round_066():
    inst = _make_instance(runtime_initialized=False)

    with pytest.raises(RuntimeError, match="Runtime not initialized"):
        inst.copy_from("/some/path")


def test_copy_from_path_not_exists_round_066():
    # Create instance that believes runtime is initialized but points to a non-existent path
    inst = _make_instance(runtime_initialized=True, sanitize_ret="/definitely/not/exist/xyz")

    with pytest.raises(FileNotFoundError) as exc:
        inst.copy_from("/definitely/not/exist/xyz")

    # Ensure message references the original requested path
    assert "Path not found" in str(exc.value)


def test_copy_from_single_file_round_066():
    # Create a real temporary file to be zipped
    tmpf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmpf.write(b"hello")
        tmpf.flush()
        tmpf_path = tmpf.name
    finally:
        tmpf.close()

    inst = _make_instance(runtime_initialized=True, sanitize_ret=tmpf_path)

    zip_path = None
    try:
        result = inst.copy_from(tmpf_path)
        # Should return a Path pointing to the created zip file
        assert isinstance(result, Path)
        zip_path = str(result)
        assert os.path.exists(zip_path)

        # Validate zip contains the single file with its basename
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
        assert os.path.basename(tmpf_path) in names
    finally:
        # cleanup
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(tmpf_path):
            os.remove(tmpf_path)


def test_copy_from_directory_round_066():
    # Create a temporary directory with nested files to exercise the os.walk loop
    tmpdir = tempfile.mkdtemp()
    try:
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir, exist_ok=True)
        file_a = os.path.join(tmpdir, "a.txt")
        file_b = os.path.join(subdir, "b.txt")
        with open(file_a, "wb") as f:
            f.write(b"A")
        with open(file_b, "wb") as f:
            f.write(b"B")

        inst = _make_instance(runtime_initialized=True, sanitize_ret=tmpdir)

        zip_path = None
        try:
            result = inst.copy_from(tmpdir)
            zip_path = str(result)
            assert os.path.exists(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                names = set(zf.namelist())

            # The archived names should be relative to the source directory
            assert "a.txt" in names
            assert os.path.join("sub", "b.txt") in names
        finally:
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
    finally:
        # cleanup directory
        try:
            if os.path.exists(file_a):
                os.remove(file_a)
            if os.path.exists(file_b):
                os.remove(file_b)
            if os.path.isdir(subdir):
                os.rmdir(subdir)
            if os.path.isdir(tmpdir):
                os.rmdir(tmpdir)
        except OSError:
            # best-effort cleanup; tests should still be deterministic
            pass


def test_copy_from_zipfile_raises_round_066(monkeypatch):
    # Simulate zipfile.ZipFile raising an error to exercise the exception handler
    class BadZip:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise RuntimeError("simulated-zip-error")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(cli_module.zipfile, "ZipFile", BadZip)

    # Use a real file path so path existence checks pass
    tmpf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmpf.write(b"x")
        tmpf.flush()
        tmpf_path = tmpf.name
    finally:
        tmpf.close()

    inst = _make_instance(runtime_initialized=True, sanitize_ret=tmpf_path)

    try:
        with pytest.raises(RuntimeError) as exc:
            inst.copy_from(tmpf_path)
        # Ensure the raised RuntimeError includes the original simulated message
        assert "simulated-zip-error" in str(exc.value)
    finally:
        if os.path.exists(tmpf_path):
            os.remove(tmpf_path)
