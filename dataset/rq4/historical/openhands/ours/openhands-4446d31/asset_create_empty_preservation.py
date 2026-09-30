from pathlib import Path
import pytest

from openhands.runtime.plugins.agent_skills.file_editor.impl import EditTool


def test_generated_target_probe_asset_001_create_accepts_present_empty_string(tmp_path, monkeypatch):
    """Probe: create should preserve a present-but-empty file_text ('') and append it to _file_history.

    This test supplies file_text='' (present but falsy) and asserts the tool records it in its history.
    """
    tool = EditTool()

    # Build an absolute path that does not yet exist
    target_path = tmp_path / "test_empty.txt"
    path_str = str(target_path)

    # Monkeypatch write_file to avoid touching the real filesystem
    def fake_write_file(p: Path, content: str):
        # intentionally no-op to prevent disk writes; the tool should still record the content
        return None

    monkeypatch.setattr(tool, "write_file", fake_write_file)

    # Call the tool with an empty-but-present file_text
    result = tool(command='create', path=path_str, file_text='')

    # Primary oracle: verify the internal history recorded the exact empty string
    key = Path(path_str)
    assert key in tool._file_history, "_file_history must have an entry for the created Path"
    assert tool._file_history[key][-1] == "", "The empty string provided should be appended to _file_history as-is"
