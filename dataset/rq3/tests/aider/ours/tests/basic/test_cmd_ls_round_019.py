import types
import pytest
from aider import commands


class FakeIO:
    def __init__(self):
        self.outputs = []

    def tool_output(self, msg):
        # mimic side-effectful printing/capturing used by Commands
        self.outputs.append(msg)


class FakeCoder:
    def __init__(self, files, abs_map=None, abs_fnames=None, abs_read_only_fnames=None):
        # files: list of relative filenames
        self._files = list(files)
        # abs_map: dict relative -> absolute
        self._abs_map = abs_map or {}
        # set or list of absolute filenames that are in chat
        self.abs_fnames = set(abs_fnames or [])
        # iterable of absolute read-only filenames
        self.abs_read_only_fnames = list(abs_read_only_fnames or [])

    def get_all_relative_files(self):
        return list(self._files)

    def abs_root_path(self, rel):
        # return mapped absolute path or a deterministic default
        if rel in self._abs_map:
            return self._abs_map[rel]
        return f"/root/{rel}"

    def get_rel_fname(self, abs_path):
        # reverse lookup if present, else basename
        for k, v in self._abs_map.items():
            if v == abs_path:
                return k
        # fallback to last path component
        return abs_path.split("/")[-1]


def make_commands_with(coder):
    # Create Commands instance without calling __init__ and set attributes used by cmd_ls
    cmd = commands.Commands.__new__(commands.Commands)
    cmd.coder = coder
    cmd.io = FakeIO()
    return cmd


def test_cmd_ls_empty_round_019():
    # No repo files, no chat files, no read-only files -> prints the single "No files..." message
    coder = FakeCoder(files=[], abs_map={}, abs_fnames=[], abs_read_only_fnames=[])
    cmd = make_commands_with(coder)

    result = commands.Commands.cmd_ls(cmd, args=None)

    # function returns None and only emits the no-files message
    assert result is None
    assert cmd.io.outputs == ["\nNo files in chat, git repo, or read-only list."], (
        "Expected exactly the no-files message when there are no files anywhere"
    )


def test_cmd_ls_mixed_round_019():
    # Mix of chat files, repo-only files, and read-only files
    files = ["a.txt", "b.py", "c.md"]
    abs_map = {
        "a.txt": "/root/a.txt",
        "b.py": "/root/b.py",
        "c.md": "/root/c.md",
        # read-only file not part of the relative files list
        "other_readonly.txt": "/root/other_readonly.txt",
    }
    # Mark a.txt and c.md as present in chat
    abs_fnames = {"/root/a.txt", "/root/c.md"}
    # One read-only absolute filename
    abs_read_only_fnames = ["/root/other_readonly.txt"]

    coder = FakeCoder(files=files, abs_map=abs_map, abs_fnames=abs_fnames, abs_read_only_fnames=abs_read_only_fnames)
    cmd = make_commands_with(coder)

    # Call the method under test
    result = commands.Commands.cmd_ls(cmd, args=None)
    assert result is None

    # Collect outputs and assert ordering and content exactly as the implementation emits
    # Expected sequence based on source logic:
    # 0: Repo files header (because b.py not in abs_fnames)
    # 1: b.py listing
    # 2: Read-only header (note leading newline)
    # 3: other_readonly.txt listing (converted to relative by get_rel_fname)
    # 4: Files in chat header (leading newline)
    # 5: a.txt listing
    # 6: c.md listing
    expected = [
        "Repo files not in the chat:\n",
        "  b.py",
        "\nRead-only files:\n",
        "  other_readonly.txt",
        "\nFiles in chat:\n",
        "  a.txt",
        "  c.md",
    ]

    assert cmd.io.outputs == expected, (
        "cmd_ls outputs did not match expected sequence for mixed files.\n"
        f"Got: {cmd.io.outputs}\nExpected: {expected}"
    )
