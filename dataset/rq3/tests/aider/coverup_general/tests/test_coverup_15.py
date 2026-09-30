# file: aider/args_formatter.py:187-222
# asked: {"lines": [188, 189, 191, 193, 194, 195, 197, 198, 199, 201, 202, 204, 205, 206, 208, 209, 211, 212, 214, 215, 216, 217, 218, 220, 222], "branches": [[188, 189], [188, 191], [194, 195], [194, 197], [197, 198], [197, 201], [198, 197], [198, 199], [201, 202], [201, 204], [205, 206], [205, 208], [208, 209], [208, 211], [211, 212], [211, 214], [214, 215], [214, 222], [216, 217], [216, 222], [217, 218], [217, 220]]}
# gained: {"lines": [188, 189, 191, 193, 194, 195, 197, 198, 199, 201, 202, 204, 205, 206, 208, 209, 211, 212, 214, 215, 216, 217, 218, 220, 222], "branches": [[188, 189], [188, 191], [194, 195], [194, 197], [197, 198], [197, 201], [198, 197], [198, 199], [201, 202], [201, 204], [205, 206], [205, 208], [208, 209], [208, 211], [211, 212], [211, 214], [214, 215], [216, 217], [216, 222], [217, 218], [217, 220]]}

import argparse
import types

import pytest

from aider.args_formatter import MarkdownHelpFormatter


def _find_action_by_option(actions, opt):
    for a in actions:
        if opt in a.option_strings:
            return a
    return None


def test_positional_action_returns_empty():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("positional")
    # find the positional action (option_strings should be empty)
    pos_action = None
    for a in parser._actions:
        if not a.option_strings:
            pos_action = a
            break
    assert pos_action is not None
    fmt = MarkdownHelpFormatter("prog")
    out = fmt._format_action(pos_action)
    assert out == ""


def test_store_action_with_metavar_default_env_and_aliases():
    parser = argparse.ArgumentParser(add_help=False)
    # add option with short and long form, no explicit metavar so it's None initially
    parser.add_argument("-f", "--foo", help="help text", default="bar")
    action = _find_action_by_option(parser._actions, "--foo")
    assert action is not None
    # add env_var attribute which the formatter will use if present
    action.env_var = "FOO"

    fmt = MarkdownHelpFormatter("prog")
    output = fmt._format_action(action)

    expected = (
        "\n"
        "### `--foo VALUE`\n"
        "help text  \n"
        "Default: bar  \n"
        "Environment variable: `FOO`  \n"
        "Aliases:\n"
        "  - `-f VALUE`\n"
        "  - `--foo VALUE`\n"
    )
    assert output == expected


def test_custom_action_without_store_behavior_aliases_without_metavar():
    # Create a lightweight dummy action object that mimics required attributes
    DummyAction = types.SimpleNamespace
    # option_strings has more than one item and none start with "--"
    dummy = DummyAction(
        option_strings=["-a", "-b"],
        metavar=None,
        help=None,
        default=argparse.SUPPRESS,
        env_var=None,
    )
    # Ensure it's NOT an instance of argparse._StoreAction so the formatter won't set VALUE
    assert not isinstance(dummy, argparse._StoreAction)

    fmt = MarkdownHelpFormatter("prog")
    out = fmt._format_action(dummy)

    expected = "\n### `-b`\nAliases:\n  - `-a`\n  - `-b`\n"
    assert out == expected
