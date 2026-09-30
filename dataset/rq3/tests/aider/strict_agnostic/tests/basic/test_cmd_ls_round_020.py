import pytest
from types import SimpleNamespace
from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.outputs = []

    def tool_output(self, s):
        # Capture outputs exactly as the real io would receive them
        self.outputs.append(s)


class DummyCoder:
    def __init__(self, files, abs_fnames=None, abs_read_only_fnames=None, root="/root"):
        self._files = list(files)
        self.abs_fnames = set(abs_fnames or [])
        self.abs_read_only_fnames = list(abs_read_only_fnames or [])
        self._root = root

    def get_all_relative_files(self):
        # deterministic ordering as provided
        return list(self._files)

    def abs_root_path(self, file):
        # deterministic mapping from relative to absolute path
        return f"{self._root}/{file}"

    def get_rel_fname(self, abs_path):
        # return the final path component, deterministic
        return abs_path.split("/")[-1]


def make_self(coder):
    io = DummyIO()
    # We do not instantiate the full Commands object; instead call the function
    # with a lightweight 'self' that has the required attributes.
    return SimpleNamespace(io=io, coder=coder)


def test_cmd_ls_empty_round_020():
    """
    When there are no repo files, no chat files, and no read-only files,
    Commands.cmd_ls should emit the 'No files in chat, git repo, or read-only list.'
    message and return early.
    """
    coder = DummyCoder(files=[], abs_fnames=set(), abs_read_only_fnames=[])
    self_obj = make_self(coder)

    # Call the unbound function with our fake self
    result = Commands.cmd_ls(self_obj, args=None)

    # The function returns None and produces exactly the expected single output
    assert result is None
    assert self_obj.io.outputs == ["\nNo files in chat, git repo, or read-only list."]


def test_cmd_ls_mixed_round_020():
    """
    Exercise the branches that print repo files not in chat, read-only files,
    and files in chat. Verify ordering and exact strings emitted to io.tool_output.
    """
    files = ["a.txt", "b.py", "c.md"]

    # Mark only b.py as present in the chat (abs_fnames)
    abs_fnames = {"/root/b.py"}
    # Add c.md to the read-only set (absolute path)
    abs_read_only_fnames = ["/root/c.md"]

    coder = DummyCoder(files=files, abs_fnames=abs_fnames, abs_read_only_fnames=abs_read_only_fnames)
    self_obj = make_self(coder)

    Commands.cmd_ls(self_obj, args=None)

    # Expected sequence of outputs according to the function logic
    expected = [
        "Repo files not in the chat:\n",
        "  a.txt",
        "  c.md",
        "\nRead-only files:\n",
        "  c.md",
        "\nFiles in chat:\n",
        "  b.py",
    ]

    assert self_obj.io.outputs == expected
