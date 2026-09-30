import types
import importlib
import pytest

pc = importlib.import_module("aider.coders.patch_coder")

class DummyIO:
    def __init__(self, read_map=None):
        # read_map maps absolute paths to returned content or Exception to raise
        self.read_map = read_map or {}
        self.warnings = []

    def read_text(self, path):
        # Accept pathlib.Path or string
        key = str(path)
        if key in self.read_map:
            val = self.read_map[key]
            if isinstance(val, Exception):
                raise val
            return val
        # Simulate typical behavior: missing files raise FileNotFoundError
        raise FileNotFoundError(key)

    def tool_warning(self, msg):
        self.warnings.append(msg)


def make_instance():
    # Create a PatchCoder instance without running its __init__
    inst = object.__new__(pc.PatchCoder)
    return inst


def test_empty_content_round_018():
    inst = make_instance()
    inst.partial_response_content = "   "  # whitespace only
    inst.io = DummyIO()

    # Ensure identify_files_needed won't be accidentally used
    # but it's fine if left as-is; call should short-circuit early.
    result = pc.PatchCoder.get_edits(inst)
    assert result == []


def test_non_patch_like_warns_and_returns_empty_round_018():
    inst = make_instance()
    inst.partial_response_content = "just some text"
    dummy_io = DummyIO()
    inst.io = dummy_io

    # Ensure _norm behaves as production (use actual implementation)
    # Call get_edits and expect it to warn and return []
    result = pc.PatchCoder.get_edits(inst)
    assert result == []
    # Exact message asserted to match behavior in source
    assert any("Response does not appear to be in patch format." in w for w in dummy_io.warnings)


def test_missing_file_raises_differror_round_018(monkeypatch):
    inst = make_instance()
    # Provide content that looks like a patch but lacks sentinels (triggers is_patch_like)
    inst.partial_response_content = "@@ -1,1 +1,1\n- old\n+ new\n"
    dummy_io = DummyIO(read_map={})
    inst.io = dummy_io

    # Make identify_files_needed return a referenced relative path
    monkeypatch.setattr(pc, "identify_files_needed", lambda text: ["missing.py"])
    # abs_root_path should return an absolute-like string for the missing file
    inst.abs_root_path = lambda rel: f"/fake/root/{rel}"

    # Make read_text return None to trigger the `if file_content is None: raise DiffError(...)` branch
    dummy_io.read_map["/fake/root/missing.py"] = None

    with pytest.raises(pc.DiffError) as excinfo:
        pc.PatchCoder.get_edits(inst)
    assert "File referenced in patch not found or could not be read: missing.py" in str(excinfo.value)


def test_parse_success_returns_actions_round_018(monkeypatch):
    inst = make_instance()
    # Provide explicit sentinels so code sets start_index = 1 in the else branch
    inst.partial_response_content = "*** Begin Patch***\n*** Update File: a.txt ***\n"
    inst.io = DummyIO()

    # Force _norm to be identity so sentinel check behaves predictably
    monkeypatch.setattr(pc, "_norm", lambda s: s)
    # No files needed for this synthetic parse
    monkeypatch.setattr(pc, "identify_files_needed", lambda text: [])

    # Provide a fake patch object with an `actions` dict
    fake_patch = types.SimpleNamespace(actions={"a.txt": "FAKE_ACTION"})
    inst._parse_patch_text = lambda lines, start_index, current_files: fake_patch

    results = pc.PatchCoder.get_edits(inst)
    assert results == [("a.txt", "FAKE_ACTION")]


def test_parse_differror_converted_to_valueerror_round_018(monkeypatch):
    inst = make_instance()
    inst.partial_response_content = "*** Begin Patch***\nstuff\n"
    inst.io = DummyIO()

    # Ensure consistent sentinel handling
    monkeypatch.setattr(pc, "_norm", lambda s: s)
    monkeypatch.setattr(pc, "identify_files_needed", lambda text: [])

    # Make the parser raise DiffError and expect get_edits to convert it to ValueError
    def raise_diff(lines, start_index, current_files):
        raise pc.DiffError("bad parse")

    inst._parse_patch_text = raise_diff

    with pytest.raises(ValueError) as excinfo:
        pc.PatchCoder.get_edits(inst)
    assert "Error parsing patch content: bad parse" in str(excinfo.value)


def test_parse_unexpected_exception_converted_round_018(monkeypatch):
    inst = make_instance()
    inst.partial_response_content = "*** Begin Patch***\nstuff\n"
    inst.io = DummyIO()

    monkeypatch.setattr(pc, "_norm", lambda s: s)
    monkeypatch.setattr(pc, "identify_files_needed", lambda text: [])

    def raise_generic(lines, start_index, current_files):
        raise RuntimeError("boom")

    inst._parse_patch_text = raise_generic

    with pytest.raises(ValueError) as excinfo:
        pc.PatchCoder.get_edits(inst)
    assert "Unexpected error parsing patch: boom" in str(excinfo.value)
