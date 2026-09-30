import importlib
import types

import pytest

from aider.coders import context_coder as context_coder_mod
from aider.coders import base_coder as base_coder_mod


class DummyRepoMap:
    def __init__(self, max_map_tokens=10.0, map_mul_no_files=2.0):
        self.refresh = None
        self.max_map_tokens = max_map_tokens
        self.map_mul_no_files = map_mul_no_files


def _patch_base_init_set_repo(repo_map_value):
    """Return a function that will be used to monkey-patch Coder.__init__.
    It sets self.repo_map to repo_map_value and does nothing else.
    """

    def _init(self, *a, **k):
        # mimic base initializer behavior by setting repo_map only
        self.repo_map = repo_map_value

    return _init


def test_init_with_no_repo_map_returns_early_round_045():
    # Patch base Coder.__init__ to set repo_map to a falsy value (None)
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = _patch_base_init_set_repo(None)
        inst = context_coder_mod.ContextCoder()
        # The __init__ should return early when repo_map is falsy.
        assert getattr(inst, "repo_map") is None
        # Because it returned early, attributes changed only by base init.
        # Ensure no repo_map mutation attributes exist.
        assert not hasattr(inst.repo_map, "refresh") if inst.repo_map is not None else True
    finally:
        base_coder_mod.Coder.__init__ = orig_init


def test_init_with_repo_map_adjusts_fields_round_045():
    # Provide a DummyRepoMap instance so ContextCoder.__init__ performs the mutations
    dummy = DummyRepoMap(max_map_tokens=100.0, map_mul_no_files=1.5)
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = _patch_base_init_set_repo(dummy)
        inst = context_coder_mod.ContextCoder()
        # After init, repo_map.refresh should be set to "always"
        assert inst.repo_map.refresh == "always"
        # max_map_tokens should be multiplied by the previous map_mul_no_files
        # initial max_map_tokens 100.0 * map_mul_no_files 1.5 => 150.0
        assert inst.repo_map.max_map_tokens == pytest.approx(100.0 * 1.5)
        # map_mul_no_files should be reset to 1.0
        assert inst.repo_map.map_mul_no_files == pytest.approx(1.0)
    finally:
        base_coder_mod.Coder.__init__ = orig_init


def test_reply_completed_handles_empty_and_whitespace_content_round_045():
    # Ensure reply_completed returns True for empty/whitespace content
    # Use a no-op base init so instantiation is safe
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = lambda self, *a, **k: None
        inst = context_coder_mod.ContextCoder()
        inst.partial_response_content = "   \n\t"
        assert inst.reply_completed() is True
        # Also test None
        inst.partial_response_content = None
        assert inst.reply_completed() is True
    finally:
        base_coder_mod.Coder.__init__ = orig_init


def test_reply_completed_equal_file_sets_returns_true_round_045():
    # Case where mentioned_rel_fnames == current_rel_fnames -> True (no changes)
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = lambda self, *a, **k: None
        inst = context_coder_mod.ContextCoder()

        inst.partial_response_content = "something"
        # Provide methods that return the same filenames (as iterables)
        inst.get_inchat_relative_files = lambda: ["file1.py", "file2.py"]
        inst.get_file_mentions = lambda content, ignore_current=True: ["file2.py", "file1.py"]
        # Sanity defaults
        inst.num_reflections = 0
        inst.max_reflections = 3
        # Call and assert True
        assert inst.reply_completed() is True
        # No reflected_message should be set in this path
        assert not hasattr(inst, "reflected_message") or inst.reflected_message is None
    finally:
        base_coder_mod.Coder.__init__ = orig_init


def test_reply_completed_respects_reflection_limit_round_045():
    # When mentioned files differ and num_reflections >= max_reflections - 1 -> True
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = lambda self, *a, **k: None
        inst = context_coder_mod.ContextCoder()

        inst.partial_response_content = "nonempty"
        inst.get_inchat_relative_files = lambda: {"a.py"}
        inst.get_file_mentions = lambda content, ignore_current=True: {"b.py"}
        # set reflections to be at the threshold
        inst.max_reflections = 5
        inst.num_reflections = inst.max_reflections - 1
        # add_rel_fname should not be called in this branch; make it error if called
        def _bad_add(fname):
            raise AssertionError("add_rel_fname should not be called when reflection limit reached")

        inst.add_rel_fname = _bad_add
        assert inst.reply_completed() is True
    finally:
        base_coder_mod.Coder.__init__ = orig_init


def test_reply_completed_adds_mentioned_files_and_sets_reflection_round_045():
    # When mentioned files differ and there is room for reflections, add_rel_fname is called and reflected_message set
    orig_init = base_coder_mod.Coder.__init__
    try:
        base_coder_mod.Coder.__init__ = lambda self, *a, **k: None
        inst = context_coder_mod.ContextCoder()

        inst.partial_response_content = "please update files"
        inst.get_inchat_relative_files = lambda: set()
        inst.get_file_mentions = lambda content, ignore_current=True: {"c.py", "d.py"}
        inst.num_reflections = 0
        inst.max_reflections = 10

        called = []

        def recorder(fname):
            called.append(fname)

        inst.add_rel_fname = recorder

        # Ensure the class-level gpt_prompts instance has try_again set to a known value
        # ContextCoder.gpt_prompts was created at import time; set its attribute
        context_coder_mod.ContextCoder.gpt_prompts.try_again = "please try again"

        # Run
        result = inst.reply_completed()

        assert result is True
        # add_rel_fname should have been called for each mentioned file
        assert set(called) == {"c.py", "d.py"}
        # abs_fnames should be initialized to an empty set by the method
        assert hasattr(inst, "abs_fnames") and inst.abs_fnames == set()
        # reflected_message should be set from gpt_prompts.try_again
        assert inst.reflected_message == "please try again"
    finally:
        base_coder_mod.Coder.__init__ = orig_init
