import types
import pytest

from aider import commands as commands_module
from aider import prompts
from aider.commands import Commands


class IORecorder:
    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


class DiffItem:
    def __init__(self, a_path):
        self.a_path = a_path


class Commit:
    def __init__(self, hexsha, parents, diffs=None, tree=None):
        self.hexsha = hexsha
        self.parents = parents
        self._diffs = diffs or []
        # tree is dict-like to simulate prev_commit.tree[fname]
        self.tree = tree if tree is not None else {}

    def diff(self, other):
        return self._diffs


class FakeGit:
    def __init__(self, revparse_map=None, checkout_behavior=None, reset_callback=None):
        # revparse_map maps ref->value or raises if value is Exception
        self.revparse_map = revparse_map or {}
        # checkout_behavior: dict file->(raises_bool)
        self.checkout_behavior = checkout_behavior or {}
        self.reset_callback = reset_callback
        self.checkout_calls = []
        self.reset_calls = []

    def rev_parse(self, ref):
        if ref in self.revparse_map:
            val = self.revparse_map[ref]
            if isinstance(val, Exception):
                raise val
            return val
        raise Exception("ref not found")

    def checkout(self, ref, file_path):
        self.checkout_calls.append((ref, file_path))
        if self.checkout_behavior.get(file_path, False):
            raise Exception("checkout failed")
        return None

    def reset(self, *args):
        self.reset_calls.append(args)
        if self.reset_callback:
            self.reset_callback()
        return None


class FakeRepoRepo:
    def __init__(self, is_dirty_map=None, active_branch_name="main"):
        self._is_dirty_map = is_dirty_map or {}
        self.active_branch = types.SimpleNamespace(name=active_branch_name)
        self.git = None

    def is_dirty(self, path=None):
        # match call signature used in code: is_dirty(path=fname)
        return self._is_dirty_map.get(path, False)


class FakeRepo:
    def __init__(self, head_commit, head_sha, head_message, repo_repo_obj, git_obj):
        self._head_commit = head_commit
        self._head_sha = head_sha
        self._head_message = head_message
        self.repo = repo_repo_obj
        self.repo.git = git_obj
        # After reset we may want to change what get_head_commit_sha returns
        self._reset_called = False

    def get_head_commit(self):
        return self._head_commit

    def get_head_commit_sha(self, short=False):
        # return different sha after reset to simulate HEAD moving back
        return "after-reset-sha" if self._reset_called else self._head_sha

    def get_head_commit_message(self, default):
        return "after-reset-message" if self._reset_called else self._head_message

    # helper to be called by FakeGit.reset via callback
    def _mark_reset(self):
        self._reset_called = True


def make_cmd_with_io_and_coder(repo_obj=None, aider_hashes=None, send_undo_reply=False):
    cmd = object.__new__(Commands)
    cmd.io = IORecorder()
    coder = types.SimpleNamespace()
    coder.repo = repo_obj
    coder.aider_commit_hashes = set(aider_hashes or [])
    coder.main_model = types.SimpleNamespace(send_undo_reply=send_undo_reply)
    cmd.coder = coder
    return cmd


@pytest.fixture(autouse=True)
def patch_ANY_GIT_ERROR_and_prompt():
    # Ensure the module will catch our test Exceptions by using Exception
    original_any = commands_module.ANY_GIT_ERROR
    commands_module.ANY_GIT_ERROR = Exception
    # Patch prompts.undo_command_reply to deterministic sentinel
    original_undo = commands_module.prompts.undo_command_reply
    commands_module.prompts.undo_command_reply = "UNDO_REPLY_SENTINEL"
    yield
    commands_module.ANY_GIT_ERROR = original_any
    commands_module.prompts.undo_command_reply = original_undo


def test_no_repo_round_036():
    cmd = make_cmd_with_io_and_coder(repo_obj=None)
    # Call raw_cmd_undo and assert it errors out when no repo
    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    assert cmd.io.errors
    assert "No git repository found" in cmd.io.errors[0]


def test_last_commit_not_in_aider_hashes_round_036():
    # Create a head commit with a single parent
    prev = Commit(hexsha="prevsha", parents=[])
    head = Commit(hexsha="headsha", parents=[prev], diffs=[DiffItem("file.txt")])
    repo_repo = FakeRepoRepo(is_dirty_map={"file.txt": False})
    # git that will not be used here
    fake_git = FakeGit(revparse_map={})
    fake_repo = FakeRepo(head_commit=head, head_sha="h1", head_message="msg\nline2", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes=set())

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    # Expect an error about last commit not made by aider
    assert any("not made by aider" in e for e in cmd.io.errors), cmd.io.errors
    # expect the explanatory tool_output lines to be present
    assert any("/git reset --hard HEAD^" in o for o in cmd.io.outputs)


def test_merge_commit_with_multiple_parents_round_036():
    # Create a merge commit (more than 1 parent)
    parent1 = Commit(hexsha="p1", parents=[])
    parent2 = Commit(hexsha="p2", parents=[])
    head = Commit(hexsha="hmerge", parents=[parent1, parent2], diffs=[])
    repo_repo = FakeRepoRepo(is_dirty_map={})
    fake_git = FakeGit(revparse_map={})
    fake_repo = FakeRepo(head_commit=head, head_sha="hmerge_sha", head_message="merge msg", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"hmerge_sha"})

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    assert any("more than 1 parent" in e for e in cmd.io.errors), cmd.io.errors


def test_file_dirty_prevents_undo_round_036():
    # Commit with 1 parent and one changed file that is dirty
    prev = Commit(hexsha="prev", parents=[], tree={"file_a": True})
    head = Commit(hexsha="h", parents=[prev], diffs=[DiffItem("file_a")])
    repo_repo = FakeRepoRepo(is_dirty_map={"file_a": True})
    fake_git = FakeGit(revparse_map={})
    fake_repo = FakeRepo(head_commit=head, head_sha="h", head_message="m", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"h"})

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    assert any("uncommitted changes" in e for e in cmd.io.errors), cmd.io.errors


def test_prev_commit_missing_file_round_036():
    # Commit with 1 parent but prev_commit.tree does not contain file -> KeyError
    prev = Commit(hexsha="prev", parents=[], tree={})
    head = Commit(hexsha="h2", parents=[prev], diffs=[DiffItem("missing_file")])
    repo_repo = FakeRepoRepo(is_dirty_map={"missing_file": False})
    fake_git = FakeGit(revparse_map={})
    fake_repo = FakeRepo(head_commit=head, head_sha="h2", head_message="m", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"h2"})

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    assert any("was not in the repository in the previous commit" in e for e in cmd.io.errors), cmd.io.errors


def test_has_origin_and_local_equals_remote_prevents_undo_round_036():
    # No changed files to simplify; origin rev_parse returns same as local
    prev = Commit(hexsha="prev", parents=[])
    head = Commit(hexsha="h3", parents=[prev], diffs=[])
    repo_repo = FakeRepoRepo(is_dirty_map={})
    # local rev_parse for HEAD
    fake_git = FakeGit(revparse_map={"origin/main": "R1"})
    # FakeRepo.get_head_commit_sha returns 'R1' as local head as well
    fake_repo = FakeRepo(head_commit=head, head_sha="R1", head_message="m", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"h3"})

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    assert any("already been pushed to the origin" in e for e in cmd.io.errors), cmd.io.errors


def test_unrestored_causes_error_and_outputs_lists_round_036():
    # One file that will be restored successfully, one that will fail checkout
    prev = Commit(hexsha="pv", parents=[], tree={"good.txt": True, "bad.txt": True})
    head = Commit(hexsha="h4", parents=[prev], diffs=[DiffItem("good.txt"), DiffItem("bad.txt")])
    repo_repo = FakeRepoRepo(is_dirty_map={"good.txt": False, "bad.txt": False})
    # git.checkout will fail for bad.txt
    fake_git = FakeGit(revparse_map={}, checkout_behavior={"bad.txt": True})

    fake_repo = FakeRepo(head_commit=head, head_sha="h4", head_message="message", repo_repo_obj=repo_repo, git_obj=fake_git)
    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"h4"})

    res = Commands.raw_cmd_undo(cmd, args=None)
    assert res is None
    # Expect error about restoring bad file
    assert any("Error restoring" in e for e in cmd.io.errors), cmd.io.errors
    # Restored files list and Unable to restore list should be present in outputs
    assert any("Restored files" in o for o in cmd.io.outputs) or any("Unable to restore files" in o for o in cmd.io.outputs)


def test_successful_undo_and_returns_prompt_reply_round_036():
    # Happy path: checkout succeeds, reset called, and send_undo_reply True -> returns prompt
    prev = Commit(hexsha="prevok", parents=[], tree={"only.txt": True})
    head = Commit(hexsha="h5", parents=[prev], diffs=[DiffItem("only.txt")])
    repo_repo = FakeRepoRepo(is_dirty_map={"only.txt": False})

    # Create FakeGit and make sure reset calls back to mark reset on fake_repo
    fake_git = FakeGit(revparse_map={})

    fake_repo = FakeRepo(head_commit=head, head_sha="HEAD1", head_message="last msg", repo_repo_obj=repo_repo, git_obj=fake_git)

    # connect the reset callback so that after reset, get_head_commit_sha returns different value
    def mark_reset_cb():
        fake_repo._mark_reset()

    fake_git.reset_callback = mark_reset_cb

    cmd = make_cmd_with_io_and_coder(repo_obj=fake_repo, aider_hashes={"HEAD1"}, send_undo_reply=True)

    res = Commands.raw_cmd_undo(cmd, args=None)
    # Should return the patched prompt reply sentinel
    assert res == "UNDO_REPLY_SENTINEL"
    # The outputs should contain Removed: and Now at:
    assert any("Removed:" in o for o in cmd.io.outputs), cmd.io.outputs
    assert any("Now at:" in o for o in cmd.io.outputs), cmd.io.outputs
