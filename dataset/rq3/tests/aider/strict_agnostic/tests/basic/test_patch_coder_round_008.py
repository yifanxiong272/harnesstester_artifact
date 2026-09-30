import pathlib
import types
import pytest
from types import SimpleNamespace

from aider.coders.patch_coder import PatchCoder, ActionType


class DummyIO:
    def __init__(self, read_override=None):
        # store messages and a simple mapping for written content
        self.outputs = []
        self.warnings = []
        self.writes = {}
        self.read_override = read_override

    def tool_output(self, msg: str):
        self.outputs.append(msg)

    def tool_warning(self, msg: str):
        self.warnings.append(msg)

    def write_text(self, full_path: str, content: str):
        # write to actual filesystem so pathlib.Path checks work
        p = pathlib.Path(full_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        self.writes[str(full_path)] = content

    def read_text(self, full_path: str):
        # if an override callback is supplied, call it to allow tests to return None
        if self.read_override is not None:
            return self.read_override(full_path)
        p = pathlib.Path(full_path)
        if not p.exists():
            return None
        return p.read_text()


def _make_coder(tmp_path, read_override=None):
    # create an instance without calling __init__ and inject the attributes used by apply_edits
    coder = object.__new__(PatchCoder)
    # abs_root_path should map action.path to a path under tmp_path
    coder.abs_root_path = lambda p: str(tmp_path / p)
    coder.io = DummyIO(read_override=read_override)

    # default _apply_update simply returns supplied new body (or appends marker)
    def _apply_update(current, action, path):
        # produce deterministic new content for assertions
        return f"UPDATED:{path}\n"

    coder._apply_update = _apply_update
    return coder


def test_add_existing_file_round_008(tmp_path):
    # Prepare a pre-existing file
    src = tmp_path / "exists.txt"
    src.write_text("orig\n")

    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "exists.txt"
    action.type = ActionType.ADD
    action.new_content = "new content"
    action.move_path = None

    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])

    # Error should indicate ADD and the path
    assert "ADD Error" in str(exc.value) and "exists.txt" in str(exc.value)


def test_add_new_file_appends_newline_and_outputs_round_008(tmp_path):
    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "newdir/newfile.txt"
    action.type = ActionType.ADD
    action.new_content = "line without nl"
    action.move_path = None

    # Ensure target does not exist
    target_path = tmp_path / action.path
    if target_path.exists():
        target_path.unlink()

    coder.apply_edits([(None, action)])

    # File should now exist and have a single trailing newline
    text = target_path.read_text()
    assert text.endswith("\n")
    assert text == "line without nl\n"

    # tool_output should have recorded adding
    assert any("Adding newdir/newfile.txt" in o for o in coder.io.outputs)


def test_delete_missing_file_warns_but_no_error_round_008(tmp_path):
    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "missing.txt"
    action.type = ActionType.DELETE
    action.new_content = None
    action.move_path = None

    # Ensure missing
    target_path = tmp_path / action.path
    if target_path.exists():
        target_path.unlink()

    # Should not raise
    coder.apply_edits([(None, action)])

    # tool_warning should have been called mentioning missing file
    assert any("DELETE Warning" in w and "missing.txt" in w for w in coder.io.warnings)


def test_delete_existing_file_unlinks_round_008(tmp_path):
    # Create file to delete
    target = tmp_path / "to_delete.txt"
    target.write_text("bye\n")

    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "to_delete.txt"
    action.type = ActionType.DELETE
    action.new_content = None
    action.move_path = None

    coder.apply_edits([(None, action)])

    assert not target.exists()
    assert any("Deleting to_delete.txt" in o for o in coder.io.outputs)


def test_update_missing_file_raises_round_008(tmp_path):
    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "nope.txt"
    action.type = ActionType.UPDATE
    action.new_content = None
    action.move_path = None

    # Ensure missing
    target = tmp_path / action.path
    if target.exists():
        target.unlink()

    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])

    assert "UPDATE Error" in str(exc.value) and action.path in str(exc.value)


def test_update_read_returns_none_raises_round_008(tmp_path):
    # Create file but make read_text return None to trigger the specific branch
    target = tmp_path / "file.txt"
    target.write_text("content\n")

    # read_override returns None for the target path only
    def read_override(full_path):
        if str(target) == full_path:
            return None
        p = pathlib.Path(full_path)
        return p.read_text() if p.exists() else None

    coder = _make_coder(tmp_path, read_override=read_override)

    action = SimpleNamespace()
    action.path = "file.txt"
    action.type = ActionType.UPDATE
    action.new_content = None
    action.move_path = None

    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])

    assert "Could not read file for UPDATE" in str(exc.value)


def test_update_move_overwrite_and_unlink_round_008(tmp_path):
    # Prepare source and target files
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("old-src\n")
    dst.write_text("old-dst\n")

    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "src.txt"
    action.type = ActionType.UPDATE
    action.new_content = None
    action.move_path = "dst.txt"

    # _apply_update returns deterministic string 'UPDATED:src.txt\n'
    coder.apply_edits([(None, action)])

    # target should be overwritten with updated content
    assert dst.read_text() == f"UPDATED:{action.path}\n"
    # source should be removed because move_path provided and different
    assert not src.exists()

    # There should be a tool_warning about overwriting since target existed
    assert any("UPDATE Warning" in w for w in coder.io.warnings)
    # And an output about moving
    assert any("Updating and moving src.txt to dst.txt" in o for o in coder.io.outputs)


def test_unknown_action_type_raises_round_008(tmp_path):
    coder = _make_coder(tmp_path)

    action = SimpleNamespace()
    action.path = "whatever.txt"
    # Use an integer to simulate an unknown type; not equal to any ActionType members
    action.type = 999
    action.new_content = None
    action.move_path = None

    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])

    assert "Unknown action type" in str(exc.value)
