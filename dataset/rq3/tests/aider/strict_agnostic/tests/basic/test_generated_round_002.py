import types
import pytest

from aider.coders import patch_coder as pc

DiffError = pc.DiffError
ActionType = pc.ActionType
PatchCoder = pc.PatchCoder


class SimpleAction:
    def __init__(self, type_, chunks=None, path=None, move_path=None):
        self.type = type_
        self.chunks = chunks or []
        self.path = path
        self.move_path = move_path


class FakeSelf:
    """A minimal fake 'self' to call the unbound _parse_patch_text method.

    It implements just enough of the real PatchCoder used by _parse_patch_text:
    - _parse_update_file_sections(lines, index, file_content) -> (action, index, fuzz)
    - _parse_add_file_content(lines, index) -> (action, index)
    - io.tool_warning(message) to record warnings

    The behavior is deterministic and controlled by internal counters.
    """

    def __init__(self):
        self._update_calls = 0
        self.warnings = []
        self.io = types.SimpleNamespace(tool_warning=self._record_warning)

    def _record_warning(self, msg):
        self.warnings.append(msg)

    def _parse_update_file_sections(self, lines, index, file_content):
        # deterministic simple simulation: advance index by 1 and return a simple action
        self._update_calls += 1
        new_index = index + 1
        fuzz = 1
        # For the first update call, return an action with a non-UPDATE type so tests can exercise
        # the conflicting-action branch. Later calls behave like UPDATE actions.
        if self._update_calls == 1:
            return SimpleAction(type_=ActionType.DELETE, chunks=["chunk1"]), new_index, fuzz
        return SimpleAction(type_=ActionType.UPDATE, chunks=["chunk2"]), new_index, fuzz

    def _parse_add_file_content(self, lines, index):
        # deterministic simple simulation: return an ADD action and advance index
        new_index = index + 1
        return SimpleAction(type_=ActionType.ADD, chunks=["a"]), new_index


def call_parser(fake, lines, start_index, current_files):
    # Call the unbound function from the class with our fake self
    return PatchCoder._parse_patch_text(fake, lines, start_index, current_files)


def test_update_missing_path_round_002():
    fake = FakeSelf()
    # Update line with empty path should raise DiffError about missing path
    lines = ["*** Update File: "]
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, {})
    assert "Update File action missing path." in str(excinfo.value)


def test_update_move_missing_path_round_002():
    fake = FakeSelf()
    # Update with a valid path but Move to with empty path should raise Move to action missing path.
    lines = ["*** Update File: a.txt", "*** Move to: "]
    # provide current_files so path exists
    current_files = {"a.txt": "content"}
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, current_files)
    assert "Move to action missing path." in str(excinfo.value)


def test_update_missing_current_file_round_002():
    fake = FakeSelf()
    # Update refers to a file that is not present in current_files
    lines = ["*** Update File: missing.txt"]
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, {})
    assert "Update File Error - missing file content for: missing.txt" in str(excinfo.value)


def test_update_merge_conflicting_action_round_002():
    fake = FakeSelf()
    # Two successive Update blocks for the same path. The fake's first returned action has type DELETE
    # so the second Update should trigger a conflicting-actions DiffError.
    lines = [
        "*** Update File: duplicate.txt",
        "first-update-body",
        "*** Update File: duplicate.txt",
        "second-update-body",
    ]
    current_files = {"duplicate.txt": "content"}
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, current_files)
    assert "Conflicting actions for file: duplicate.txt" in str(excinfo.value)


def test_delete_duplicate_ignored_round_002():
    fake = FakeSelf()
    # Two Delete blocks for the same file. The second should be ignored and a warning recorded.
    lines = [
        "*** Delete File: foo.txt",
        "*** Delete File: foo.txt",
        "*** End Patch",
    ]
    current_files = {"foo.txt": "some content"}
    patch = call_parser(fake, lines, 0, current_files)
    # The parser should have produced a Patch and recorded a warning for the duplicate delete
    assert isinstance(patch, pc.Patch)
    # ensure the delete action is present
    assert "foo.txt" in patch.actions
    assert patch.actions["foo.txt"].type == ActionType.DELETE
    # warning message must mention duplicate delete
    assert any("Duplicate delete action for file: foo.txt" in w for w in fake.warnings)


def test_unknown_line_raises_round_002():
    fake = FakeSelf()
    # An unexpected non-empty line should raise an Unknown or misplaced line DiffError
    lines = ["this is not a directive"]
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, {})
    assert "Unknown or misplaced line while parsing patch: this is not a directive" in str(excinfo.value)


def test_add_missing_path_round_002():
    fake = FakeSelf()
    # Add File with empty path should raise a DiffError
    lines = ["*** Add File: "]
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, {})
    assert "Add File action missing path." in str(excinfo.value)


def test_add_duplicate_action_round_002():
    fake = FakeSelf()
    # Add the same path twice: second should raise Duplicate action for file
    lines = [
        "*** Add File: new.txt",
        "content-line",
        "*** Add File: new.txt",
        "more-content",
    ]
    # start parsing; first Add will create an action, second should raise
    with pytest.raises(DiffError) as excinfo:
        call_parser(fake, lines, 0, {})
    assert "Duplicate action for file: new.txt" in str(excinfo.value)
