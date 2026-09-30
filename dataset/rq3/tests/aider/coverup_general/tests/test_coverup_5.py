# file: aider/args_formatter.py:105-166
# asked: {"lines": [106, 107, 109, 111, 112, 113, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 127, 128, 130, 131, 132, 133, 135, 136, 137, 138, 140, 141, 142, 143, 145, 146, 147, 149, 150, 151, 152, 153, 154, 155, 156, 158, 159, 161, 166], "branches": [[106, 107], [106, 109], [112, 113], [112, 115], [116, 117], [116, 118], [118, 119], [118, 120], [120, 121], [120, 122], [122, 123], [122, 125], [127, 128], [127, 130], [130, 131], [130, 133], [131, 130], [131, 132], [135, 136], [135, 137], [137, 138], [137, 140], [140, 141], [140, 142], [142, 143], [142, 145], [145, 146], [145, 150], [146, 147], [146, 149], [150, 151], [150, 158], [158, 159], [158, 161]]}
# gained: {"lines": [106, 107, 109, 111, 112, 113, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 127, 128, 130, 131, 132, 133, 135, 136, 137, 140, 141, 142, 145, 146, 147, 149, 150, 151, 152, 153, 154, 155, 156, 158, 159, 161, 166], "branches": [[106, 107], [106, 109], [112, 113], [112, 115], [116, 117], [116, 118], [118, 119], [118, 120], [120, 121], [120, 122], [122, 123], [122, 125], [127, 128], [127, 130], [130, 131], [131, 130], [131, 132], [135, 136], [135, 137], [137, 140], [140, 141], [140, 142], [142, 145], [145, 146], [145, 150], [146, 147], [146, 149], [150, 151], [150, 158], [158, 159], [158, 161]]}

import argparse
import re

import pytest

from aider.args_formatter import YamlHelpFormatter


def _get_action_by_dest(parser, dest):
    for a in parser._actions:
        if a.dest == dest:
            return a
    raise KeyError(dest)


def test_positional_action_returns_empty():
    parser = argparse.ArgumentParser()
    parser.add_argument("pos")  # positional -> no option_strings
    action = _get_action_by_dest(parser, "pos")
    fmt = YamlHelpFormatter(prog="p")
    out = fmt._format_action(action)
    # According to implementation, positional actions return empty string
    assert out == ""


def test_format_action_covers_all_branches():
    parser = argparse.ArgumentParser(add_help=False)
    # Long option with help and default containing '#'
    parser.add_argument("--long", help="long help", default="a#b")
    # Option with default argparse.SUPPRESS
    parser.add_argument("--sup", default=argparse.SUPPRESS)
    # Option with empty list default
    parser.add_argument("--elist", default=[])
    # Store true action (flag)
    parser.add_argument("--flag", action="store_true", help="flag help")
    # Nargs '*' action
    parser.add_argument("--multi", nargs="*", help="multi help")
    # Append action
    parser.add_argument("--app", action="append")
    # Option ending with 'color' and no default (to trigger color-specific branch)
    parser.add_argument("--foregroundcolor")
    # Numeric default that is falsy (0) to exercise boolean conversion to "false"
    parser.add_argument("--num", default=0)
    # Default that is True to exercise conversion to "true"
    parser.add_argument("--set", default=True)
    # Short-only option to exercise switch selection without '--'
    parser.add_argument("-c", "--compound", dest="compound")

    fmt = YamlHelpFormatter(prog="p")

    # long: default contains '#', should be quoted and include help
    a_long = _get_action_by_dest(parser, "long")
    out_long = fmt._format_action(a_long)
    assert "## long help" in out_long
    assert '#long: "a#b"' in out_long

    # sup: default argparse.SUPPRESS -> treated as empty and yields fallback 'xxx'
    a_sup = _get_action_by_dest(parser, "sup")
    out_sup = fmt._format_action(a_sup)
    assert "#sup: xxx" in out_sup

    # elist: default empty list -> treated as empty and yields fallback 'xxx'
    a_elist = _get_action_by_dest(parser, "elist")
    out_elist = fmt._format_action(a_elist)
    assert "#elist: xxx" in out_elist

    # flag: store_true -> default becomes false and is printed
    a_flag = _get_action_by_dest(parser, "flag")
    out_flag = fmt._format_action(a_flag)
    assert "## flag help" in out_flag
    # should show '#flag: false' (string)
    assert re.search(r"#flag:\s*false", out_flag)

    # multi: nargs '*' -> should include multiple-values block
    a_multi = _get_action_by_dest(parser, "multi")
    out_multi = fmt._format_action(a_multi)
    assert "#multi: xxx" in out_multi
    assert "## Specify multiple values like this:" in out_multi
    assert "#  - zzz" in out_multi

    # app: append action should also yield multiple-values block
    a_app = _get_action_by_dest(parser, "app")
    out_app = fmt._format_action(a_app)
    assert "#app: xxx" in out_app
    assert "## Specify multiple values like this:" in out_app

    # foregroundcolor: switch endswith 'color' -> should suggest quoted example "xxx"
    a_fg = _get_action_by_dest(parser, "foregroundcolor")
    out_fg = fmt._format_action(a_fg)
    assert '#foregroundcolor: "xxx"' in out_fg

    # num: default 0 -> treated as not None and falsy -> becomes "false"
    a_num = _get_action_by_dest(parser, "num")
    out_num = fmt._format_action(a_num)
    assert re.search(r"#num:\s*false", out_num)

    # set: default True -> becomes "true"
    a_set = _get_action_by_dest(parser, "set")
    out_set = fmt._format_action(a_set)
    assert re.search(r"#set:\s*true", out_set)

    # compound: has both short and long, should prefer long starting with '--'
    a_comp = _get_action_by_dest(parser, "compound")
    out_comp = fmt._format_action(a_comp)
    # switch should be 'compound' in the output fragment
    assert "#compound:" in out_comp
