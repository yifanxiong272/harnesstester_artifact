# file: aider/commands.py:560-655
# asked: {"lines": [562, 563, 574, 575, 576, 579, 582, 583, 585, 611, 616, 617, 618, 621, 630, 631, 634, 635, 636, 637, 638, 639, 640, 641, 655], "branches": [[561, 562], [573, 574], [581, 582], [615, 616], [616, 617], [616, 624], [633, 634], [636, 637], [636, 638], [639, 640], [639, 641], [654, 655]]}
# gained: {"lines": [562, 563, 574, 575, 576, 579, 582, 583, 585, 611, 616, 617, 618, 621, 630, 631, 634, 635, 636, 637, 638, 639, 640, 641, 655], "branches": [[561, 562], [573, 574], [581, 582], [615, 616], [616, 617], [616, 624], [633, 634], [636, 637], [636, 638], [639, 640], [639, 641], [654, 655]]}

import types
import pytest
from types import SimpleNamespace

from aider.commands import Commands
from aider.repo import ANY_GIT_ERROR
from aider import prompts


class FakeIO:
    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


class FakeDiff:
    def __init__(self, a_path):
        self.a_path = a_path


class FakeCommit:
    def __init__(self, parents, hexsha="deadbeef", diffs=None, sha="abc", message="msg"):
        self.parents = parents
        self.hexsha = hexsha
        self._diffs = diffs or []
        self._sha = sha
        self._message = message

    def diff(self, prev):
        return self._diffs

    def __repr__(self):
        return f"<FakeCommit {self.hexsha}>"


class FakePrevCommit:
    def __init__(self, tree_files):
        class Tree:
            def __init__(self, files):
                self._files = set(files)

            def __getitem__(self, item):
                if item not in self._files:
                    raise KeyError(item)
                return item

        self.tree = Tree(tree_files)


class FakeGit:
    def __init__(self, rev_map=None, checkout_behaviour=None):
        self.rev_map = rev_map or {}
        self.checkout_behaviour = checkout_behaviour or (lambda *a, **k: None)
        self.reset_called = False
        self.checkout_calls = []

    def rev_parse(self, arg):
        if arg in self.rev_map:
            val = self.rev_map[arg]
            if isinstance(val, Exception):
                raise val
            return val
        raise ANY_GIT_ERROR("no such ref")

    def checkout(self, *args):
        if len(args) >= 2:
            file_path = args[1]
        elif args:
            file_path = args[0]
        else:
            file_path = None
        self.checkout_calls.append(file_path)
        return self.checkout_behaviour(file_path)

    def reset(self, *args, **kwargs):
        self.reset_called = True
        return None


class FakeRepoInner:
    def __init__(self, git_obj, active_branch_name="main", is_dirty_func=None):
        self.git = git_obj
        self.active_branch = SimpleNamespace(name=active_branch_name)
        self._is_dirty = is_dirty_func or (lambda path=None: False)

    def is_dirty(self, path=None):
        return self._is_dirty(path)


class FakeRepo:
    def __init__(self, head_commit, prev_commit=None, git_obj=None, sha_before="abc", sha_after="def", message_before="before", message_after="after"):
        self._head = head_commit
        self._prev = prev_commit or FakePrevCommit([])
        self.repo = FakeRepoInner(git_obj or FakeGit(), active_branch_name="main")
        self._sha_before = sha_before
        self._sha_after = sha_after
        self._message_before = message_before
        self._message_after = message_after

    def get_head_commit(self):
        return self._head

    def get_head_commit_sha(self, short=False):
        return self._sha_before

    def get_head_commit_message(self, default="(unknown)"):
        return self._message_before


def make_commands_with_io(initial_coder=None):
    io = FakeIO()
    if initial_coder is None:
        initial_coder = SimpleNamespace(repo=None, aider_commit_hashes=set(), main_model=SimpleNamespace(send_undo_reply=False))
    cmds = Commands(io, initial_coder)
    return cmds


def test_no_repo_returns_error_and_none():
    cmds = make_commands_with_io()
    result = cmds.raw_cmd_undo(args=[])
    assert result is None
    assert cmds.io.errors, "Expected an error when no repo"
    assert "No git repository found." in cmds.io.errors[0]


def test_last_commit_not_aider_commit_emits_error_and_tip():
    cmds = make_commands_with_io()

    prev = FakePrevCommit(["file.txt"])
    commit = FakeCommit(parents=[prev], hexsha="hex1", diffs=[FakeDiff("file.txt")], sha="sha1", message="a commit")
    fake_git = FakeGit(rev_map={"HEAD": "L"})
    fake_repo = FakeRepo(head_commit=commit, prev_commit=prev, git_obj=fake_git, sha_before="sha1", message_before="a commit")
    cmds.coder = SimpleNamespace(repo=fake_repo, aider_commit_hashes=set(), main_model=SimpleNamespace(send_undo_reply=False))
    result = cmds.raw_cmd_undo(args=[])
    assert result is None
    assert any("not made by aider" in e for e in cmds.io.errors)
    assert any("/git reset --hard HEAD^" in o for o in cmds.io.outputs)


def test_merge_commit_with_multiple_parents_errors():
    cmds = make_commands_with_io()
    prev1 = FakePrevCommit(["file.txt"])
    commit = FakeCommit(parents=[prev1, prev1], hexsha="mergehex", diffs=[FakeDiff("file.txt")], sha="sha1", message="merge commit")
    fake_git = FakeGit(rev_map={"HEAD": "L"})
    fake_repo = FakeRepo(head_commit=commit, prev_commit=prev1, git_obj=fake_git, sha_before="sha1", message_before="merge commit")
    cmds.coder = SimpleNamespace(repo=fake_repo, aider_commit_hashes={"sha1"}, main_model=SimpleNamespace(send_undo_reply=False))
    result = cmds.raw_cmd_undo(args=[])
    assert result is None
    assert cmds.io.errors
    assert any("has more than 1 parent" in e for e in cmds.io.errors)


def test_pushed_commit_prevents_undo_when_head_equals_origin():
    cmds = make_commands_with_io()
    prev = FakePrevCommit(["file.txt"])
    commit = FakeCommit(parents=[prev], hexsha="h1", diffs=[FakeDiff("file.txt")], sha="shaX", message="msg")
    fake_git = FakeGit(rev_map={"HEAD": "SAME", "origin/main": "SAME"})
    fake_repo = FakeRepo(head_commit=commit, prev_commit=prev, git_obj=fake_git, sha_before="shaX", message_before="msg")
    fake_repo.repo._is_dirty = lambda path=None: False
    cmds.coder = SimpleNamespace(repo=fake_repo, aider_commit_hashes={"shaX"}, main_model=SimpleNamespace(send_undo_reply=False))
    result = cmds.raw_cmd_undo(args=[])
    assert result is None
    assert any("already been pushed to the origin" in e for e in cmds.io.errors)


def test_unrestored_files_produce_error_and_listings():
    cmds = make_commands_with_io()
    prev = FakePrevCommit(["keep.txt", "lost.txt"])
    diffs = [FakeDiff("keep.txt"), FakeDiff("lost.txt")]
    commit = FakeCommit(parents=[prev], hexsha="h2", diffs=diffs, sha="shaY", message="commit Y")

    def checkout_behaviour(file_path):
        if file_path == "lost.txt":
            raise ANY_GIT_ERROR("failed checkout")
        return None

    fake_git = FakeGit(rev_map={"HEAD": "L", "origin/main": "ORIGIN_HEAD"}, checkout_behaviour=checkout_behaviour)
    fake_repo = FakeRepo(head_commit=commit, prev_commit=prev, git_obj=fake_git, sha_before="shaY", message_before="commit Y")
    fake_repo.repo._is_dirty = lambda path=None: False
    cmds.coder = SimpleNamespace(repo=fake_repo, aider_commit_hashes={"shaY"}, main_model=SimpleNamespace(send_undo_reply=False))
    result = cmds.raw_cmd_undo(args=[])
    assert result is None
    assert any("Error restoring" in e for e in cmds.io.errors)
    assert any("Restored files:" in o for o in cmds.io.outputs)
    assert any("Unable to restore files:" in o for o in cmds.io.outputs)
    assert any("  keep.txt" in o for o in cmds.io.outputs)
    assert any("  lost.txt" in o for o in cmds.io.outputs)


def test_send_undo_reply_returns_prompts_reply_on_success():
    cmds = make_commands_with_io()
    prev = FakePrevCommit(["only.txt"])
    diffs = [FakeDiff("only.txt")]
    commit = FakeCommit(parents=[prev], hexsha="h3", diffs=diffs, sha="shaZ", message="some message")
    fake_git = FakeGit(rev_map={"HEAD": "LOCAL_HEAD", "origin/main": "REMOTE_HEAD"})
    fake_repo = FakeRepo(head_commit=commit, prev_commit=prev, git_obj=fake_git, sha_before="shaZ", message_before="some message")
    fake_repo.repo._is_dirty = lambda path=None: False

    fake_repo.get_head_commit_sha = lambda short=True: "shaZ"
    fake_repo.get_head_commit_message = lambda default="(unknown)": "some message"

    cmds.coder = SimpleNamespace(repo=fake_repo, aider_commit_hashes={"shaZ"}, main_model=SimpleNamespace(send_undo_reply=True))
    result = cmds.raw_cmd_undo(args=[])
    assert result == prompts.undo_command_reply
    assert any("Removed:" in o for o in cmds.io.outputs)
    assert any("Now at:" in o for o in cmds.io.outputs)
