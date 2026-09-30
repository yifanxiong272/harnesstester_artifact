# file: aider/args_formatter.py:41-72
# asked: {"lines": [42, 43, 45, 46, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 62, 63, 65, 66, 67, 68, 70, 72], "branches": [[42, 43], [42, 45], [45, 46], [45, 48], [51, 52], [51, 53], [53, 54], [53, 55], [55, 56], [55, 57], [57, 58], [57, 60], [62, 63], [62, 65], [65, 66], [65, 72], [67, 68], [67, 70]]}
# gained: {"lines": [42, 43, 45, 46, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 62, 63, 65, 66, 67, 68, 70, 72], "branches": [[42, 43], [42, 45], [45, 46], [45, 48], [51, 52], [51, 53], [53, 54], [53, 55], [55, 56], [55, 57], [57, 58], [57, 60], [62, 63], [62, 65], [65, 66], [67, 68], [67, 70]]}

import argparse
import pytest

from aider.args_formatter import DotEnvFormatter


class DummyAction:
    def __init__(self, option_strings, env_var, default, help_text=None):
        self.option_strings = option_strings
        self.env_var = env_var
        self.default = default
        # use attribute name 'help' to match argparse.Action
        self.help = help_text


def test_no_option_strings_returns_empty():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(option_strings=[], env_var="FOO", default="bar", help_text="h")
    result = fmt._format_action(action)
    assert result == ""


def test_no_env_var_returns_none():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(option_strings=["--foo"], env_var=None, default="bar", help_text="h")
    result = fmt._format_action(action)
    assert result is None


def test_default_argparse_suppress_and_help_and_empty_assignment():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(
        option_strings=["--foo"],
        env_var="FOO",
        default=argparse.SUPPRESS,
        help_text="Some help",
    )
    result = fmt._format_action(action)
    # Expected:
    # leading blank line, help line, env var with empty assignment line, and final newline
    expected = "\n## Some help\n#FOO=\n\n"
    assert result == expected


def test_default_string_results_in_assignment_with_value():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(option_strings=["--bar"], env_var="BAR", default="baz", help_text=None)
    result = fmt._format_action(action)
    expected = "\n#BAR=baz\n\n"
    assert result == expected


def test_default_empty_list_becomes_empty_assignment_with_help():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(option_strings=["-l"], env_var="LIST", default=[], help_text="List help")
    result = fmt._format_action(action)
    expected = "\n## List help\n#LIST=\n\n"
    assert result == expected


def test_default_boolean_true_and_false_map_to_true_false_strings():
    fmt = DotEnvFormatter("prog")
    action_true = DummyAction(option_strings=["--flag"], env_var="FLAG", default=True, help_text=None)
    res_true = fmt._format_action(action_true)
    assert "\n#FLAG=true\n\n" == res_true

    action_false = DummyAction(option_strings=["--flag"], env_var="FLAG", default=False, help_text=None)
    res_false = fmt._format_action(action_false)
    assert "\n#FLAG=false\n\n" == res_false


def test_default_none_leads_to_empty_assignment():
    fmt = DotEnvFormatter("prog")
    action = DummyAction(option_strings=["--none"], env_var="NONE", default=None, help_text="No default")
    result = fmt._format_action(action)
    expected = "\n## No default\n#NONE=\n\n"
    assert result == expected
