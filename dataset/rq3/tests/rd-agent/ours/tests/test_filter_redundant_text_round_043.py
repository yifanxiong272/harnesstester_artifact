import sys
import importlib
import types
import json
import re

import rdagent.utils as utils

# Provide a small FakeT to satisfy T(...).r(...) calls inside the function
class FakeT:
    def __init__(self, key):
        self.key = key

    def r(self, stdout=None):
        # return predictable prompts; if stdout present include length to ensure deterministic behavior
        if stdout is None:
            return "SYSTEM_PROMPT"
        return f"USER_PROMPT(len={len(str(stdout))})"


def _make_fake_llm_module():
    """Create a fake rdagent.oai.llm_utils module exposing an APIBackend class.

    The returned APIBackend class exposes two configurable class attributes that tests can adjust:
      - chat_token_limit
      - calc_sequence (an iterator yielding either ints or Exception instances)
      - create_response (object to json.dumps when create_chat is called)
      - create_raises (bool to raise when create_chat is invoked)
    """

    mod = types.ModuleType("rdagent.oai.llm_utils")

    class APIBackend:
        # Defaults; tests will replace these class attributes before calling
        chat_token_limit = 1000
        calc_sequence = iter([100])
        create_response = {}
        create_raises = False

        def __init__(self):
            pass

        def build_messages_and_calculate_token(self, user_prompt=None, system_prompt=None):
            # Pop a value from the configured sequence; if it's an Exception instance, raise it
            try:
                v = next(self.__class__.calc_sequence)
            except StopIteration:
                # default behavior if tests forget to set sequence
                return 100
            if isinstance(v, Exception):
                raise v
            return v

        def build_messages_and_create_chat_completion(self, user_prompt=None, system_prompt=None, json_mode=None, json_target_type=None):
            if self.__class__.create_raises:
                raise RuntimeError("simulated create error")
            return json.dumps(self.__class__.create_response)

        # keep build_messages_and_calculate_token and create_chat deterministic

    mod.APIBackend = APIBackend
    return mod


def _setup_test_env(fake_llm_module):
    # Install fake llm module so the in-function import resolves to our fake
    sys.modules["rdagent.oai.llm_utils"] = fake_llm_module
    # Patch T used by rdagent.utils
    utils.T = FakeT
    # Provide deterministic helpers for regex and filter application used by the function
    def try_regex_sub(pattern, text, replace_with=None, flags=None):
        # Keep behavior simple and deterministic: if replace_with provided, use python re.sub,
        # otherwise return original text unchanged
        if replace_with is None:
            return text
        try:
            # ignore flags from regex module; use re for deterministic substitution in tests
            return re.sub(pattern, replace_with, text)
        except re.error:
            # fallback: return text unchanged if pattern incompatible
            return text

    def filter_with_time_limit(regex_patterns, text):
        # If regex_patterns is a sentinel that tests look for, return a fixed token so tests can assert it
        if regex_patterns == ["__RETURN_FILTERED_BY_TEST__"]:
            return "FILTERED_BY_LLM"
        # Otherwise, perform no change
        return text

    utils.try_regex_sub = try_regex_sub
    utils.filter_with_time_limit = filter_with_time_limit


def _teardown_test_env():
    # Remove our fake module if installed
    sys.modules.pop("rdagent.oai.llm_utils", None)


def test_early_return_small_token_round_043():
    """If build_messages_and_calculate_token returns a small token count (< 0.1 * limit),
    filter_redundant_text should return the current truncated_stdout immediately.
    """
    fake_mod = _make_fake_llm_module()
    # Configure the fake backend: chat_token_limit=1000, and token calc returns 50 (<100)
    fake_mod.APIBackend.chat_token_limit = 1000
    fake_mod.APIBackend.calc_sequence = iter([50])
    fake_mod.APIBackend.create_response = {}
    fake_mod.APIBackend.create_raises = False

    _setup_test_env(fake_mod)
    try:
        # Use a simple input; try_regex_sub is identity so filtered_stdout equals original
        s = "original_text_line"
        res = utils.filter_redundant_text(s)
        assert res == s
    finally:
        _teardown_test_env()


def test_needs_sub_false_returns_new_filtered_round_043():
    """When the LLM returns a JSON with needs_sub = False, the function should return the
    filter_with_time_limit result (here driven by the sentinel regex patterns).
    """
    fake_mod = _make_fake_llm_module()
    fake_mod.APIBackend.chat_token_limit = 1000
    # Make token size be moderate so the inner loop breaks and we proceed to call the model
    fake_mod.APIBackend.calc_sequence = iter([200])
    # have the LLM return a dict where needs_sub is False and regex_patterns is sentinel list
    fake_mod.APIBackend.create_response = {"needs_sub": False, "regex_patterns": ["__RETURN_FILTERED_BY_TEST__"]}
    fake_mod.APIBackend.create_raises = False

    _setup_test_env(fake_mod)
    try:
        res = utils.filter_redundant_text("some text that will be filtered")
        # Our filter_with_time_limit returns fixed string for the sentinel
        assert res == "FILTERED_BY_LLM"
    finally:
        _teardown_test_env()


def test_build_chat_completion_exception_breaks_and_returns_filtered_round_043():
    """If the call to build_messages_and_create_chat_completion raises, the outer loop should catch,
    log an error and break, and ultimately the function should return the last filtered_stdout.
    """
    fake_mod = _make_fake_llm_module()
    fake_mod.APIBackend.chat_token_limit = 1000
    fake_mod.APIBackend.calc_sequence = iter([200])
    # configure the create to raise
    fake_mod.APIBackend.create_raises = True

    _setup_test_env(fake_mod)
    try:
        s = "unchanged_after_create_error"
        res = utils.filter_redundant_text(s)
        # since the create raised and we break, we expect the original (post-try_regex_sub) output
        assert res == s
    finally:
        _teardown_test_env()


def test_calculate_token_value_error_shrink_and_continue_round_043():
    """If build_messages_and_calculate_token raises ValueError (tokenizer regex issue),
    the code should call _shrink_stdout_once and then continue; if a subsequent token size is small,
    the function will return the shrunk truncated_stdout.
    """
    fake_mod = _make_fake_llm_module()
    fake_mod.APIBackend.chat_token_limit = 1000
    # First call raises ValueError; second call returns small size forcing early return
    fake_mod.APIBackend.calc_sequence = iter([ValueError("Regex error while tokenizing"), 50])
    fake_mod.APIBackend.create_response = {}
    fake_mod.APIBackend.create_raises = False

    _setup_test_env(fake_mod)
    try:
        # Make the initial filtered_stdout long enough to be visibly shrunk by _shrink_stdout_once
        long_text = "A" * 1200
        res = utils.filter_redundant_text(long_text)
        # _shrink_stdout_once keeps head and tail each of length int(limit*0.3)=300 => total 600
        assert isinstance(res, str)
        assert len(res) == 600
        # ensure start and end slices match original head & tail
        assert res == long_text[:300] + long_text[-300:]
    finally:
        _teardown_test_env()
