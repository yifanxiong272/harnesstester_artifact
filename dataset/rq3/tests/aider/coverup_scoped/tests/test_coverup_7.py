# file: aider/commands.py:1054-1091
# asked: {"lines": [1057, 1059, 1060, 1061, 1062, 1063, 1064, 1065, 1067, 1070, 1071, 1072, 1074, 1075, 1076, 1078, 1079, 1080, 1081, 1083, 1084, 1085, 1086, 1088, 1089, 1090, 1091], "branches": [[1062, 1063], [1062, 1070], [1064, 1065], [1064, 1067], [1070, 1071], [1070, 1074], [1074, 1075], [1074, 1078], [1078, 1079], [1078, 1080], [1080, 1081], [1080, 1083], [1083, 1084], [1083, 1085], [1085, 1086], [1085, 1088], [1088, 1089], [1088, 1090], [1090, 0], [1090, 1091]]}
# gained: {"lines": [1057, 1059, 1060, 1061, 1062, 1063, 1064, 1065, 1067, 1070, 1071, 1072, 1074, 1075, 1076, 1078, 1079, 1080, 1081, 1083, 1084, 1085, 1086, 1088, 1089, 1090, 1091], "branches": [[1062, 1063], [1062, 1070], [1064, 1065], [1064, 1067], [1070, 1071], [1070, 1074], [1074, 1075], [1074, 1078], [1078, 1079], [1080, 1081], [1080, 1083], [1083, 1084], [1085, 1086], [1085, 1088], [1088, 1089], [1090, 0], [1090, 1091]]}

import pytest

from aider.commands import Commands


class FakeIO:
    def __init__(self):
        self.outputs = []

    def tool_output(self, text):
        # Simulate the io.tool_output used by Commands
        self.outputs.append(text)


class FakeCoder:
    def __init__(self, rel_files=None, chat_abs_fnames=None, read_only_abs_fnames=None):
        # rel_files: list of relative filenames returned by get_all_relative_files
        self._rel_files = list(rel_files or [])
        # abs_fnames: set of absolute file paths considered "in chat"
        self.abs_fnames = set(chat_abs_fnames or [])
        # abs_read_only_fnames: iterable of abs paths considered read-only
        self.abs_read_only_fnames = list(read_only_abs_fnames or [])

    def get_all_relative_files(self):
        return list(self._rel_files)

    def abs_root_path(self, rel):
        # Simple mapping for tests: prefix with /root/
        return f"/root/{rel}"

    def get_rel_fname(self, abs_path):
        # Simple mapping for tests: return basename after last slash
        return abs_path.split("/")[-1]


def test_cmd_ls_no_files():
    io = FakeIO()
    coder = FakeCoder(rel_files=[], chat_abs_fnames=[], read_only_abs_fnames=[])
    cmd = Commands(io=io, coder=coder)

    # Call cmd_ls: should detect no files and output the no-files message exactly once.
    cmd.cmd_ls(args="")

    assert len(io.outputs) == 1
    assert io.outputs[0] == "\nNo files in chat, git repo, or read-only list."


def test_cmd_ls_with_files():
    # Prepare files: file1 and file3 are in chat, file2 is in repo only.
    rel_files = ["file1.txt", "file2.py", "file3.md"]
    chat_abs = {"/root/file1.txt", "/root/file3.md"}
    read_only_abs = ["/abs/ro.md"]

    io = FakeIO()
    coder = FakeCoder(rel_files=rel_files, chat_abs_fnames=chat_abs, read_only_abs_fnames=read_only_abs)
    cmd = Commands(io=io, coder=coder)

    cmd.cmd_ls(args="")

    # Expect outputs in sequence:
    # - Repo files heading, then the repo-only file
    # - Read-only heading, then the read-only rel name
    # - Files in chat heading, then each chat file (in order encountered)
    expected = [
        "Repo files not in the chat:\n",
        "  file2.py",
        "\nRead-only files:\n",
        "  ro.md",
        "\nFiles in chat:\n",
        "  file1.txt",
        "  file3.md",
    ]

    assert io.outputs == expected
