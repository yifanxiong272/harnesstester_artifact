import pathlib
from types import SimpleNamespace
import pytest

from aider.coders.patch_coder import PatchCoder, ActionType


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.warnings = []
        self.writes = []
        # map full_path -> content to return for read_text
        self.read_map = {}

    def tool_output(self, msg):
        self.outputs.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def write_text(self, path, content):
        self.writes.append((path, content))

    def read_text(self, path):
        return self.read_map.get(path)


# Helper to build a bare PatchCoder instance without running its __init__
def make_coder(tmp_path, io=None):
    coder = object.__new__(PatchCoder)
    # abs_root_path should map logical path to an actual path under tmp_path
    coder.abs_root_path = lambda p: str(tmp_path / p)
    coder.io = io or DummyIO()
    # default _apply_update just returns the provided replacement for testing
    coder._apply_update = lambda current, action, path: "UPDATED_CONTENT"
    return coder


def test_no_edits_round_008(tmp_path):
    coder = make_coder(tmp_path)
    # Should return None / do nothing and not raise
    result = coder.apply_edits([])
    assert result is None


def test_add_file_already_exists_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    # create the file so .exists() is True
    target = tmp_path / "a.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("existing")

    action = SimpleNamespace(type=ActionType.ADD, path="a.txt", new_content="new")
    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])
    # Expect the message to indicate ADD Error and include the path
    assert "ADD Error" in str(exc.value)
    assert "a.txt" in str(exc.value)


def test_add_missing_content_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    action = SimpleNamespace(type=ActionType.ADD, path="b.txt", new_content=None)
    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])
    assert "has no content" in str(exc.value)
    assert "b.txt" in str(exc.value)


def test_add_writes_with_newline_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    action = SimpleNamespace(type=ActionType.ADD, path="c.txt", new_content="line")
    coder.apply_edits([(None, action)])

    # One write should have occurred, with a single trailing newline ensured
    assert len(io.writes) == 1
    path_written, content_written = io.writes[0]
    assert path_written == str(tmp_path / "c.txt")
    assert content_written.endswith("\n")
    assert content_written == "line\n"


def test_delete_not_found_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    action = SimpleNamespace(type=ActionType.DELETE, path="missing.txt")
    coder.apply_edits([(None, action)])

    # Should have produced a tool_output and a tool_warning about missing file
    assert any("Deleting missing.txt" in o or "Deleting missing.txt" in o for o in io.outputs) or any("Deleting missing.txt" in o for o in io.outputs)
    # Ensure a DELETE warning was emitted
    assert any("DELETE Warning" in w for w in io.warnings)


def test_delete_existing_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    target = tmp_path / "to_delete.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("remove me")

    action = SimpleNamespace(type=ActionType.DELETE, path="to_delete.txt")
    coder.apply_edits([(None, action)])

    assert not target.exists()
    assert any("Deleting to_delete.txt" in msg for msg in io.outputs)


def test_update_not_exists_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    action = SimpleNamespace(type=ActionType.UPDATE, path="nope.txt", move_path=None)
    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])
    assert "UPDATE Error" in str(exc.value)
    assert "nope.txt" in str(exc.value)


def test_update_read_none_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    # Create file so exists() is True, but set read_text to return None
    full = tmp_path / "readnone.txt"
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text("content")
    # configure io to return None for this path
    io.read_map[str(full)] = None

    action = SimpleNamespace(type=ActionType.UPDATE, path="readnone.txt", move_path=None)
    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])
    assert "Could not read file for UPDATE" in str(exc.value)
    assert "readnone.txt" in str(exc.value)


def test_update_move_overwrite_warning_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    # create source and target so both exist
    src = tmp_path / "src.txt"
    tgt = tmp_path / "dst" / "tgt.txt"
    tgt.parent.mkdir(parents=True, exist_ok=True)
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("old")
    tgt.write_text("existing target")

    # ensure read_text will return something (simulate reading current content)
    io.read_map[str(src)] = "old"

    # make _apply_update produce a recognizable new content
    coder._apply_update = lambda current, action, path: "MOVED_NEW_CONTENT"

    action = SimpleNamespace(type=ActionType.UPDATE, path="src.txt", move_path=str(pathlib.Path("dst") / "tgt.txt"))
    coder.apply_edits([(None, action)])

    # Expect a warning about overwriting the target
    assert any("UPDATE Warning" in w for w in io.warnings)
    # Expect write to have been called for the target path
    expected_target_path = str(tmp_path / action.move_path)
    assert any(p == expected_target_path and c == "MOVED_NEW_CONTENT" for (p, c) in io.writes)
    # Original source should have been removed
    assert not src.exists()


def test_unknown_action_type_round_008(tmp_path):
    io = DummyIO()
    coder = make_coder(tmp_path, io=io)

    action = SimpleNamespace(type="NOT_A_REAL_ACTION", path="z.txt")
    with pytest.raises(ValueError) as exc:
        coder.apply_edits([(None, action)])
    assert "Unknown action type" in str(exc.value) or "Unknown action type" in str(exc.value)
