# file: aider/coders/context_coder.py:5-53
# asked: {"lines": [12, 14, 15, 17, 18, 19, 22, 23, 24, 27, 28, 34, 35, 37, 38, 40, 41, 42, 45, 50, 53], "branches": [[14, 15], [14, 17], [23, 24], [23, 27], [34, 35], [34, 37], [37, 38], [37, 40], [41, 42], [41, 45]]}
# gained: {"lines": [12, 14, 15, 17, 18, 19, 22, 23, 24, 27, 28, 34, 35, 37, 38, 40, 41, 42, 45, 50, 53], "branches": [[14, 15], [14, 17], [23, 24], [23, 27], [34, 35], [34, 37], [37, 38], [37, 40], [41, 42], [41, 45]]}

import types
import pytest

import aider.coders.context_coder as cc
from aider.coders.context_coder import ContextCoder


def _fake_init_base(self, *args, **kwargs):
    """
    Fake initializer to replace Coder.__init__ during tests.
    It sets a few attributes that ContextCoder methods expect.
    """
    # repo_map may be passed via kwargs in tests
    self.repo_map = kwargs.get("repo_map", None)
    # attributes used by reply_completed
    self.partial_response_content = None
    self.num_reflections = 0
    self.max_reflections = 3
    # placeholders for methods that may be monkeypatched per-test
    return None


def test_init_with_no_repo_map(monkeypatch):
    # Patch the base Coder.__init__ so ContextCoder.__init__ can call it safely
    monkeypatch.setattr(cc.Coder, "__init__", _fake_init_base, raising=True)

    coder = ContextCoder(repo_map=None)
    # Because repo_map is falsy, the constructor should return early and repo_map remains None
    assert coder.repo_map is None


def test_init_with_repo_map_updates_values(monkeypatch):
    monkeypatch.setattr(cc.Coder, "__init__", _fake_init_base, raising=True)

    class RepoMap:
        pass

    rm = RepoMap()
    rm.refresh = "sometimes"
    rm.max_map_tokens = 100
    rm.map_mul_no_files = 2.0

    coder = ContextCoder(repo_map=rm)
    # After initialization, attributes should be updated as in the source code
    assert coder.repo_map.refresh == "always"
    assert coder.repo_map.max_map_tokens == 100 * 2.0
    assert coder.repo_map.map_mul_no_files == 1.0


def test_reply_completed_empty_and_equal_mentions(monkeypatch):
    monkeypatch.setattr(cc.Coder, "__init__", _fake_init_base, raising=True)

    # Test 1: empty content -> True
    coder = ContextCoder(repo_map=None)
    coder.partial_response_content = ""  # empty content triggers early return
    assert coder.reply_completed() is True

    # Test 2: mentioned_rel_fnames == current_rel_fnames -> True
    coder = ContextCoder(repo_map=None)
    coder.partial_response_content = "some content"
    # Provide matching lists so equality branch is taken
    coder.get_inchat_relative_files = lambda: ["a.py", "b.py"]
    coder.get_file_mentions = lambda content, ignore_current=True: ["a.py", "b.py"]
    coder.num_reflections = 0
    coder.max_reflections = 5
    assert coder.reply_completed() is True


def test_reply_completed_reflection_limit_and_add_files(monkeypatch):
    monkeypatch.setattr(cc.Coder, "__init__", _fake_init_base, raising=True)

    # Case: mentions differ but num_reflections >= max_reflections - 1 -> True
    coder = ContextCoder(repo_map=None)
    coder.partial_response_content = "mentions b"
    coder.get_inchat_relative_files = lambda: ["a.py"]
    coder.get_file_mentions = lambda content, ignore_current=True: ["b.py"]
    coder.num_reflections = 2
    coder.max_reflections = 3  # num_reflections == max_reflections - 1
    assert coder.reply_completed() is True

    # Case: mentions differ and we can reflect again -> add_rel_fname invoked and message set
    coder = ContextCoder(repo_map=None)
    coder.partial_response_content = "mentions c and d"
    coder.get_inchat_relative_files = lambda: []  # current files empty
    coder.get_file_mentions = lambda content, ignore_current=True: ["c.py", "d.py"]
    coder.num_reflections = 0
    coder.max_reflections = 5

    # Prepare a gpt_prompts stub with try_again attribute
    coder.gpt_prompts = types.SimpleNamespace(try_again="PLEASE_TRY_AGAIN")

    # add_rel_fname should be called for each mentioned file; since reply_completed
    # sets self.abs_fnames = set() we implement add_rel_fname to add to that set.
    def add_rel_fname(fname):
        # Ensure abs_fnames exists (reply_completed sets it), then add
        if not hasattr(coder, "abs_fnames") or coder.abs_fnames is None:
            coder.abs_fnames = set()
        coder.abs_fnames.add(fname)

    coder.add_rel_fname = add_rel_fname

    result = coder.reply_completed()
    assert result is True
    # reflected_message should be set from gpt_prompts.try_again
    assert getattr(coder, "reflected_message", None) == "PLEASE_TRY_AGAIN"
    # abs_fnames should contain both mentioned files
    assert coder.abs_fnames == {"c.py", "d.py"}

    # Also call check_for_file_mentions to execute the (currently empty) method body
    # This ensures that the 'pass' line is covered.
    coder.check_for_file_mentions("no-op content")


# Ensure tests are discoverable by pytest without any top-level execution code.
