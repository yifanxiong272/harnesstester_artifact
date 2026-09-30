import os
import zipfile
from pathlib import Path
import tempfile
import pytest

# Import the module/class under test. Tests call the bound function with a lightweight fake 'self'
from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


class DummySelf:
    """Minimal fake self object that provides only the attributes used by copy_from."""
    pass


def _make_dummy(sanitize_return: str, initialized: bool = True) -> DummySelf:
    d = DummySelf()
    d._runtime_initialized = initialized
    # _sanitize_filename is accessed as self._sanitize_filename(path) and expected to be callable(path)
    d._sanitize_filename = (lambda path: sanitize_return)
    return d


def test_not_initialized_round_066():
    """If _runtime_initialized is False, copy_from should raise RuntimeError('Runtime not initialized')."""
    dummy = _make_dummy(sanitize_return="/does/not/matter", initialized=False)

    with pytest.raises(RuntimeError) as exc:
        CLIRuntime.copy_from(dummy, "some/path")

    assert "Runtime not initialized" in str(exc.value)


def test_path_not_found_round_066(tmp_path):
    """If sanitized path does not exist, copy_from should raise FileNotFoundError with the original path in the message."""
    # Provide an input path string that will be used in the FileNotFoundError message
    input_path = "input/that/does/not/exist.txt"
    # sanitized returns a non-existent location inside tmp_path
    nonexist = str(tmp_path / "no_such_location")
    dummy = _make_dummy(sanitize_return=nonexist, initialized=True)

    with pytest.raises(FileNotFoundError) as excinfo:
        CLIRuntime.copy_from(dummy, input_path)

    assert f"Path not found: {input_path}" == str(excinfo.value)


def test_copy_from_directory_writes_all_files_round_066(tmp_path):
    """When source is a directory, all files under it should be added to the created zip and returned Path should point to a .zip file."""
    # Create a directory tree with files
    src = tmp_path / "srcdir"
    sub = src / "subdir"
    sub.mkdir(parents=True)
    (src / "a.txt").write_text("content a")
    (sub / "b.txt").write_text("content b")

    dummy = _make_dummy(sanitize_return=str(src), initialized=True)

    result_path = CLIRuntime.copy_from(dummy, "original/input/path")

    # Check returned path exists and is a zip file
    assert isinstance(result_path, Path)
    assert result_path.exists()
    assert result_path.suffix == ".zip"

    # Inspect zip contents to ensure both files were added with relative names
    with zipfile.ZipFile(result_path, 'r') as z:
        names = set(z.namelist())

    assert "a.txt" in names
    # depending on os.path.relpath, subdir entry should be 'subdir/b.txt'
    assert any(n.endswith("b.txt") for n in names)


def test_copy_from_single_file_round_066(tmp_path):
    """When source is a single file (not a directory), zip should contain the basename of that file."""
    f = tmp_path / "single.txt"
    f.write_text("only one")

    dummy = _make_dummy(sanitize_return=str(f), initialized=True)

    result_path = CLIRuntime.copy_from(dummy, "single/input/path")

    assert result_path.exists()
    with zipfile.ZipFile(result_path, 'r') as z:
        names = z.namelist()

    assert os.path.basename(str(f)) in names


def test_zip_write_raises_is_wrapped_in_runtimeerror_round_066(tmp_path, monkeypatch):
    """If an exception occurs while creating/writing the zip, copy_from should log and raise a RuntimeError containing the original error text."""
    # Create a source directory with one file so the code attempts to write into the zip
    src = tmp_path / "src_problem"
    src.mkdir()
    (src / "x.txt").write_text("x")

    dummy = _make_dummy(sanitize_return=str(src), initialized=True)

    # Replace zipfile.ZipFile with a dummy that raises when write() is called
    class DummyZip:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, *args, **kwargs):
            raise ValueError("simulated-zip-failure")

    monkeypatch.setattr(zipfile, "ZipFile", DummyZip)

    with pytest.raises(RuntimeError) as excinfo:
        CLIRuntime.copy_from(dummy, "input/for/error")

    # The RuntimeError message should include the original exception text
    assert "simulated-zip-failure" in str(excinfo.value)
