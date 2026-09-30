import types
import pytest

from aider.coders import patch_coder

PatchCoder = patch_coder.PatchCoder
Patch = patch_coder.Patch
PatchAction = patch_coder.PatchAction
ActionType = patch_coder.ActionType
DiffError = patch_coder.DiffError


def test_end_patch_round_002():
    # A minimal case: immediate End Patch should return an empty Patch with fuzz 0
    lines = ["*** End Patch"]
    # Use a simple dummy self; this method does not touch self for this branch
    result = PatchCoder._parse_patch_text(object(), lines, 0, {})
    assert isinstance(result, Patch)
    assert result.fuzz == 0
    assert result.actions == {}


def test_update_missing_path_round_002():
    # Update action with an empty path should raise the expected DiffError
    lines = ["*** Update File: "]
    with pytest.raises(DiffError) as exc:
        PatchCoder._parse_patch_text(object(), lines, 0, {})
    assert str(exc.value) == "Update File action missing path."


def test_update_move_to_missing_path_round_002():
    # When Move to is present but empty, the parser must raise Move to action missing path.
    lines = ["*** Update File: a.py", "*** Move to: "]
    # Ensure the file is known so the code reaches the Move-to validation
    current_files = {"a.py": "content"}
    with pytest.raises(DiffError) as exc:
        PatchCoder._parse_patch_text(object(), lines, 0, current_files)
    assert str(exc.value) == "Move to action missing path."


def test_update_conflicting_actions_round_002():
    # First UPDATE block will create an action of type ADD (via our stub), then a second
    # UPDATE for the same file should raise a conflicting actions DiffError.
    lines = ["*** Update File: a.py", "<first-block>", "*** Update File: a.py", "<second-block>"]
    current_files = {"a.py": "content"}

    # Fake self with a stubbed _parse_update_file_sections that simulates creating
    # a non-UPDATE action on first call (so the next UPDATE will conflict).
    class Fake:
        def __init__(self):
            self.calls = 0
            self.io = types.SimpleNamespace()
            self.io.tool_warning = lambda msg: None

        def _parse_update_file_sections(self, lines_arg, index_arg, file_content):
            # return a PatchAction (non-UPDATE to cause the conflict), advance index
            self.calls += 1
            action = PatchAction(type=ActionType.ADD, path="a.py")
            return action, index_arg + 1, 0

    fake = Fake()
    with pytest.raises(DiffError) as exc:
        PatchCoder._parse_patch_text(fake, lines, 0, current_files)
    assert str(exc.value) == "Conflicting actions for file: a.py"


def test_delete_duplicate_round_002():
    # Two consecutive DELETE blocks for the same file should create the action once
    # and call io.tool_warning for the duplicate.
    lines = ["*** Delete File: a.py", "*** Delete File: a.py", "*** End Patch"]
    current_files = {"a.py": "content"}

    class Fake:
        def __init__(self):
            self.io = types.SimpleNamespace()
            self.warnings = []
            self.io.tool_warning = lambda msg: self.warnings.append(msg)

    fake = Fake()
    patch = PatchCoder._parse_patch_text(fake, lines, 0, current_files)

    # After parsing, the action for a.py should be DELETE and the warning should be issued
    assert "a.py" in patch.actions
    act = patch.actions["a.py"]
    assert act.type == ActionType.DELETE
    assert len(fake.warnings) == 1
    assert "Duplicate delete action for file: a.py ignored." in fake.warnings[0]


def test_add_missing_path_round_002():
    # Add File with empty path raises the specific DiffError
    lines = ["*** Add File: "]
    with pytest.raises(DiffError) as exc:
        PatchCoder._parse_patch_text(object(), lines, 0, {})
    assert str(exc.value) == "Add File action missing path."


def test_unknown_or_misplaced_line_round_002():
    # An unexpected non-blank line should raise the Unknown or misplaced line error
    lines = ["This is not a valid section header"]
    with pytest.raises(DiffError) as exc:
        PatchCoder._parse_patch_text(object(), lines, 0, {})
    assert str(exc.value).startswith("Unknown or misplaced line while parsing patch:")


def test_blank_lines_tolerated_round_002():
    # Blank lines should be skipped without raising and return an empty patch
    lines = ["", ""]
    res = PatchCoder._parse_patch_text(object(), lines, 0, {})
    assert isinstance(res, Patch)
    assert res.actions == {}
    assert res.fuzz == 0


def test_update_fuzz_accumulation_round_002():
    # If _parse_update_file_sections returns a non-zero fuzz, it must accumulate into patch.fuzz
    lines = ["*** Update File: a.py", "<dummy>", "*** End Patch"]
    current_files = {"a.py": "content"}

    class Fake:
        def __init__(self):
            self.io = types.SimpleNamespace()
            self.io.tool_warning = lambda msg: None
            self.called = 0

        def _parse_update_file_sections(self, lines_arg, index_arg, file_content):
            # Simulate one chunk parsed and return a fuzz of 3
            action = PatchAction(type=ActionType.UPDATE, path="a.py")
            # Put a dummy chunk list to mimic a realistic action
            if not hasattr(action, "chunks"):
                action.chunks = []
            return action, index_arg + 1, 3

    fake = Fake()
    patch = PatchCoder._parse_patch_text(fake, lines, 0, current_files)
    assert patch.fuzz == 3
    assert "a.py" in patch.actions
    assert patch.actions["a.py"].type == ActionType.UPDATE
