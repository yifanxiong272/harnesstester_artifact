# file: aider/report.py:174-196
# asked: {"lines": [175, 177, 179, 180, 182, 183, 184, 186, 189, 190, 191, 192, 193, 194, 196], "branches": [[180, 182], [180, 184], [184, 186], [184, 189], [191, 192], [191, 193]]}
# gained: {"lines": [175, 177, 179, 180, 182, 183, 184, 186, 189, 190, 191, 192, 193, 194, 196], "branches": [[180, 182], [180, 184], [184, 186], [184, 189], [191, 192]]}

import importlib
import sys
import builtins
import io
import pytest


def _import_report():
    # import fresh module to avoid state from other tests
    if 'aider.report' in sys.modules:
        return importlib.reload(importlib.import_module('aider.report'))
    return importlib.import_module('aider.report')


def test_main_with_two_args(monkeypatch):
    report = _import_report()
    calls = {}

    def fake_report_uncaught_exceptions():
        calls['uncaught'] = True

    def fake_dummy_function1():
        calls['dummy'] = True

    def fake_report_github_issue(issue_text, title):
        calls['issue'] = (issue_text, title)

    monkeypatch.setattr(report, 'report_uncaught_exceptions', fake_report_uncaught_exceptions)
    monkeypatch.setattr(report, 'dummy_function1', fake_dummy_function1)
    monkeypatch.setattr(report, 'report_github_issue', fake_report_github_issue)

    # Simulate invoking with program, title, issue
    monkeypatch.setattr(sys, 'argv', ['prog', 'MyTitle', 'MyIssue'])

    report.main()

    assert calls.get('uncaught') is True
    assert calls.get('dummy') is True
    assert calls.get('issue') == ('MyIssue', 'MyTitle')


def test_main_with_one_arg(monkeypatch):
    report = _import_report()
    calls = {}

    def fake_report_uncaught_exceptions():
        calls['uncaught'] = True

    def fake_dummy_function1():
        calls['dummy'] = True

    def fake_report_github_issue(issue_text, title):
        calls['issue'] = (issue_text, title)

    monkeypatch.setattr(report, 'report_uncaught_exceptions', fake_report_uncaught_exceptions)
    monkeypatch.setattr(report, 'dummy_function1', fake_dummy_function1)
    monkeypatch.setattr(report, 'report_github_issue', fake_report_github_issue)

    # Simulate invoking with program and only issue text
    monkeypatch.setattr(sys, 'argv', ['prog', 'OnlyIssueText'])

    report.main()

    assert calls.get('uncaught') is True
    assert calls.get('dummy') is True
    # title should be None when only one arg provided
    assert calls.get('issue') == ('OnlyIssueText', None)


def test_main_with_no_args_reads_stdin_and_handles_empty_title(monkeypatch, capsys):
    report = _import_report()
    calls = {}

    def fake_report_uncaught_exceptions():
        calls['uncaught'] = True

    def fake_dummy_function1():
        calls['dummy'] = True

    def fake_report_github_issue(issue_text, title):
        calls['issue'] = (issue_text, title)

    monkeypatch.setattr(report, 'report_uncaught_exceptions', fake_report_uncaught_exceptions)
    monkeypatch.setattr(report, 'dummy_function1', fake_dummy_function1)
    monkeypatch.setattr(report, 'report_github_issue', fake_report_github_issue)

    # No CLI args other than program name
    monkeypatch.setattr(sys, 'argv', ['prog'])

    # Simulate user pressing Enter (empty title) and then typing issue body in stdin
    monkeypatch.setattr(builtins, 'input', lambda: '')  # returns empty string
    fake_stdin = io.StringIO("This is the issue body.\nWith multiple lines.\n")
    monkeypatch.setattr(sys, 'stdin', fake_stdin)

    report.main()

    # Ensure the prompt prints occurred (we can capture stdout)
    captured = capsys.readouterr()
    assert "Enter the issue title" in captured.out
    assert "Enter the issue text" in captured.out

    assert calls.get('uncaught') is True
    assert calls.get('dummy') is True
    # title should be None because input returned empty/blank
    assert calls.get('issue') == ("This is the issue body.\nWith multiple lines.", None)
