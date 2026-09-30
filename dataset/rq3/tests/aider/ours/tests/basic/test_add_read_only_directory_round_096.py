import types
import aider.commands as commands


class DummyCoder:
    def __init__(self, abs_fnames=None, abs_read_only_fnames=None):
        self.abs_fnames = set(abs_fnames or [])
        self.abs_read_only_fnames = set(abs_read_only_fnames or [])


class DummyIO:
    def __init__(self):
        self.messages = []

    def tool_output(self, msg):
        # mimic the real IO contract by accepting a string
        self.messages.append(msg)


class DummyInstance:
    def __init__(self, coder, io):
        self.coder = coder
        self.io = io


def test_add_new_files_round_096(monkeypatch):
    # Arrange: two new files (file2.txt and file3.txt) should be added
    abs_path = "/abs/path"
    original_name = "orig_dir"

    # os.walk yields tuples of (root, dirs, files)
    walk_data = [
        (abs_path, [], ["file1.txt", "file2.txt"]),
        (abs_path + "/sub", [], ["file3.txt"]),
    ]

    # Patch os.walk used inside the function under test
    def fake_walk(p):
        assert p == abs_path
        for t in walk_data:
            yield t

    monkeypatch.setattr(commands.os, "walk", fake_walk)

    # coder already contains file1 in abs_fnames, so file1 should be skipped
    abs_file1 = commands.os.path.join(abs_path, "file1.txt")
    coder = DummyCoder(abs_fnames=[abs_file1])
    io = DummyIO()
    inst = DummyInstance(coder, io)

    # Bind the function to our dummy instance and call it
    func = commands.Commands._add_read_only_directory
    method = types.MethodType(func, inst)

    # Act
    method(abs_path, original_name)

    # Assert: two new files should have been added to abs_read_only_fnames
    expected_added = {
        commands.os.path.join(abs_path, "file2.txt"),
        commands.os.path.join(abs_path + "/sub", "file3.txt"),
    }

    assert expected_added.issubset(coder.abs_read_only_fnames)

    # And the tool_output should reflect the correct number and original name
    assert io.messages == [
        f"Added 2 files from directory {original_name} to read-only files."
    ]


def test_add_no_new_files_round_096(monkeypatch):
    # Arrange: all files already present in abs_read_only_fnames so none added
    abs_path = "/abs/path"
    original_name = "orig_dir"

    walk_data = [
        (abs_path, [], ["file1.txt", "file2.txt"]),
    ]

    def fake_walk(p):
        assert p == abs_path
        for t in walk_data:
            yield t

    monkeypatch.setattr(commands.os, "walk", fake_walk)

    # Both files already present in abs_read_only_fnames
    file1 = commands.os.path.join(abs_path, "file1.txt")
    file2 = commands.os.path.join(abs_path, "file2.txt")
    coder = DummyCoder(abs_fnames=[], abs_read_only_fnames=[file1, file2])
    io = DummyIO()
    inst = DummyInstance(coder, io)

    func = commands.Commands._add_read_only_directory
    method = types.MethodType(func, inst)

    # Act
    method(abs_path, original_name)

    # Assert: no changes to abs_read_only_fnames beyond the originals
    assert coder.abs_read_only_fnames == {file1, file2}

    # And the tool_output should indicate no new files were added
    assert io.messages == [f"No new files added from directory {original_name}."]
