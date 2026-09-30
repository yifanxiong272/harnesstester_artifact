# file: aider/commands.py:1537-1549
# asked: {"lines": [1539, 1541, 1542, 1544, 1545, 1547, 1549], "branches": [[1544, 1545], [1544, 1547]]}
# gained: {"lines": [1539, 1541, 1542, 1544, 1545, 1547, 1549], "branches": [[1544, 1545], [1544, 1547]]}

import sys
import types
from types import SimpleNamespace

import pytest


def _make_dummy_report_module(call_recorder):
    mod = types.ModuleType("aider.report")

    def report_github_issue(issue_text, title=None, confirm=True):
        call_recorder['called'] = True
        call_recorder['issue_text'] = issue_text
        call_recorder['title'] = title
        call_recorder['confirm'] = confirm
        return "reported"

    mod.report_github_issue = report_github_issue
    return mod


def test_cmd_report_with_title(monkeypatch):
    from aider.commands import Commands

    recorder = {}
    dummy_mod = _make_dummy_report_module(recorder)
    # Ensure the importer finds the module when "from aider.report import ..." runs
    monkeypatch.setitem(sys.modules, "aider.report", dummy_mod)

    # Provide required constructor args: io and coder. coder must have get_announcements.
    fake_io = SimpleNamespace()
    fake_coder = SimpleNamespace(get_announcements=lambda: ["line1", "line2"])
    cmd = Commands(fake_io, fake_coder)

    # Call cmd_report with a non-empty title (with surrounding spaces to exercise strip())
    cmd.cmd_report("  My Bug Title  ")

    assert recorder.get('called', False) is True
    assert recorder['issue_text'] == "line1\nline2"
    assert recorder['title'] == "My Bug Title"
    assert recorder['confirm'] is False


def test_cmd_report_without_title_whitespace_args(monkeypatch):
    from aider.commands import Commands

    recorder = {}
    dummy_mod = _make_dummy_report_module(recorder)
    monkeypatch.setitem(sys.modules, "aider.report", dummy_mod)

    fake_io = SimpleNamespace()
    fake_coder = SimpleNamespace(get_announcements=lambda: [])
    cmd = Commands(fake_io, fake_coder)

    # Call with whitespace-only args -> title should be None
    cmd.cmd_report("    ")

    assert recorder.get('called', False) is True
    assert recorder['issue_text'] == ""
    assert recorder['title'] is None
    assert recorder['confirm'] is False
