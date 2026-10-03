from pathlib import Path
import tempfile

from rdagent.core.experiment import FBWorkspace


def test_probe_001():
    """Probe: ensure inject_files does not allow path traversal out of workspace."""
    tmp = tempfile.TemporaryDirectory()
    try:
        ws = FBWorkspace()
        # place workspace under the temporary directory so workspace_path.parent is deterministic
        ws.workspace_path = Path(tmp.name) / "ws"

        outside = ws.workspace_path.parent / "escape.txt"
        # Precondition: ensure outside path does not exist before the call
        if outside.exists():
            # If a stale file exists for any reason, remove it to keep test deterministic
            outside.unlink()

        # Call the targeted entrypoint with a traversal key and a safe key
        ws.inject_files(**{"../escape.txt": "x", "safe.py": "y"})

        # Primary behavioral oracle: no file should have been created outside the workspace
        assert not outside.exists(), f"Path traversal detected: external file created at {outside!s}"

        # Supporting observation: the safe file should exist inside the workspace with expected content
        safe = ws.workspace_path / "safe.py"
        assert safe.exists(), "Expected safe file was not created inside the workspace"
        assert safe.read_text() == "y"
    finally:
        tmp.cleanup()
