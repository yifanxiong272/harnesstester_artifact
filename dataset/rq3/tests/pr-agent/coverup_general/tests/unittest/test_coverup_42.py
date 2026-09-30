# file: pr_agent/algo/utils.py:771-928
# asked: {"lines": [829, 830, 883, 884, 906, 907, 910, 911, 912, 913, 914, 915, 916, 917, 920, 921, 922, 923, 924, 925, 926, 927, 928], "branches": [[846, 864], [855, 864], [921, 0], [921, 922], [924, 921], [924, 925]]}
# gained: {"lines": [883, 884, 906, 907, 910, 911, 912, 913, 916, 917, 920, 921, 922, 923, 924, 925, 926, 927, 928], "branches": [[846, 864], [921, 0], [921, 922], [924, 925]]}

import pytest

import pr_agent.algo.utils as utils

# Helper to create a fake yaml.safe_load that follows a scripted sequence of behaviors.
# behaviors is a list where each item is either ("raise", "optional message") or ("return", value)
def _patch_safe_load_sequence(monkeypatch, behaviors):
    counter = {"i": 0}

    def fake_safe_load(obj):
        i = counter["i"]
        counter["i"] += 1
        if i >= len(behaviors):
            # Default to raising if sequence exhausted
            raise Exception("forced-exhausted")
        kind, payload = behaviors[i]
        if kind == "raise":
            raise Exception(payload or "forced")
        elif kind == "return":
            return payload
        else:
            raise RuntimeError("Invalid behavior spec")

    # Patch the yaml.safe_load used inside the module under test
    monkeypatch.setattr(utils.yaml, "safe_load", fake_safe_load)
    return counter

def test_snippet_parsing_exception_paths(monkeypatch):
    """
    Ensure that when a YAML fenced snippet is present but parsing it raises an exception,
    the function handles the exception path (the debug except) and ultimately returns None
    when no fallback succeeds.
    This exercises the snippet-extraction except branch.
    """
    # Build the fenced yaml snippet without embedding literal triple-backticks in the source
    backticks = "`" * 3
    response_text = "intro text\n" + backticks + "yaml\n: - not a valid yaml\n" + backticks + "\nend"

    # All safe_load attempts will raise to simulate failures up to the end.
    behaviors = [
        ("raise", "initial"),  # initial try
        ("raise", "replace_pipe"),  # replace '|\n' try
        ("raise", "add_spaces"),  # after replace '|2' attempt
        # snippet parsing will be attempted here (since there's a fenced snippet)
        ("raise", "snippet_parse"),  # snippet parsing (this should hit the snippet except)
        ("raise", "curly"),  # removing curly brackets try
        ("raise", "leading_plus"),  # removing leading '+' try
        ("raise", "tab_replace"),  # tab replacement try (if reached)
        ("raise", "indent"),  # adding indent for sections try
        ("raise", "remove_pipe_chars"),  # removing root-level pipe chars try
        ("raise", "encodings_latin1"),  # first encoding try
        ("raise", "encodings_utf16"),  # second encoding try
    ]
    _patch_safe_load_sequence(monkeypatch, behaviors)

    # Call function; expect None because all attempts failed
    res = utils.try_fix_yaml(response_text, keys_fix_yaml=[], first_key="", last_key="", response_text_original="")
    assert res is None

def test_first_and_last_key_extraction_success(monkeypatch):
    """
    Test the branch where first_key and last_key are provided and the function extracts
    the substring between them and successfully parses it as YAML.
    This exercises the branch for first_key/last_key extraction.
    """
    # Prepare a response string where 'firstkey:' appears, and 'lastkey:' appears later followed by a double newline to denote end.
    response_text = "firstkey:\n  a: 1\nlastkey:\n  b: 2\n\ntrailer"

    # Calls expected:
    # 1 initial, 2 replace_pipe, 3 add_spaces, 4 curly_removal, 5 first_key-block parse -> should return here
    behaviors = [
        ("raise", "initial"),
        ("raise", "replace_pipe"),
        ("raise", "add_spaces"),
        ("raise", "curly"),
        ("return", {"firstkey": {"a": 1}, "lastkey": {"b": 2}}),
    ]
    _patch_safe_load_sequence(monkeypatch, behaviors)

    res = utils.try_fix_yaml(response_text, keys_fix_yaml=[], first_key="firstkey", last_key="lastkey", response_text_original="")
    assert isinstance(res, dict)
    assert "firstkey" in res and res["firstkey"]["a"] == 1
    assert "lastkey" in res and res["lastkey"]["b"] == 2

def test_tab_and_indent_fallbacks_lead_to_encoding_success(monkeypatch):
    """
    Drive the function through earlier failing attempts and ensure the encodings loop
    eventually returns a parsed dict.
    """
    # Make response_text include a tab to reach the tab-replacement fallback.
    response_text = "some: value\n\tindented: yes\nanother: thing"

    # Calls expected:
    # 1 initial
    # 2 replace_pipe
    # 3 add_spaces
    # 4 curly_removal
    # 5 remove_leading_plus
    # 6 tab-replacement attempt
    # 7 adding-indent attempt
    # 8 remove_pipe_chars attempt
    # 9 encoding latin-1 -> return here
    behaviors = [
        ("raise", "initial"),
        ("raise", "replace_pipe"),
        ("raise", "add_spaces"),
        ("raise", "curly"),
        ("raise", "leading_plus"),
        ("raise", "tab_replace_exception"),
        ("raise", "indent_exception"),
        ("raise", "remove_pipe_exception"),
        ("return", {"decoded_with": "latin-1"}),
    ]
    _patch_safe_load_sequence(monkeypatch, behaviors)

    res = utils.try_fix_yaml(response_text, keys_fix_yaml=[], first_key="", last_key="", response_text_original="")
    assert isinstance(res, dict)
    assert res.get("decoded_with") == "latin-1"
