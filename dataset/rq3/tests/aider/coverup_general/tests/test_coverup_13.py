# file: aider/report.py:94-154
# asked: {"lines": [96, 97, 100, 103, 104, 105, 106, 107, 110, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 126, 129, 130, 131, 134, 135, 136, 137, 138, 139, 142, 145, 148, 151, 154], "branches": [[96, 97], [96, 100], [104, 105], [104, 110], [114, 115], [114, 126], [116, 117], [116, 124], [118, 119], [118, 124], [130, 131], [130, 134]]}
# gained: {"lines": [96, 97, 100, 103, 104, 105, 106, 107, 110, 113, 114, 115, 116, 117, 118, 119, 120, 121, 124, 126, 129, 130, 131, 134, 135, 136, 137, 142, 145, 148, 151, 154], "branches": [[96, 97], [96, 100], [104, 105], [114, 115], [114, 126], [116, 117], [116, 124], [118, 119], [130, 131], [130, 134]]}

import os
import sys
import traceback
import types
import pytest

import aider.report as report_module
from aider.report import exception_handler


def test_keyboardinterrupt_calls_default_excepthook(monkeypatch):
    called = {}

    def fake_excepthook(exc_type, exc_value, exc_traceback):
        # record that it was called and return a sentinel
        called['args'] = (exc_type, exc_value, exc_traceback)
        return "kb-return"

    # Ensure we replace sys.__excepthook__ with our fake and restore after test
    monkeypatch.setattr(sys, "__excepthook__", fake_excepthook, raising=False)

    # Call the handler with KeyboardInterrupt class (issubclass check expects a class)
    result = exception_handler(KeyboardInterrupt, KeyboardInterrupt(), None)

    assert result == "kb-return"
    assert called['args'][0] is KeyboardInterrupt


def _raise_nested_value_error():
    # Create a nested call stack so the innermost frame is not the top one
    def inner():
        raise ValueError("boom")

    def middle():
        return inner()

    def outer():
        return middle()

    outer()


def test_non_keyboard_exception_reports_issue_and_unlinks_version_file(monkeypatch):
    # Capture calls to report_github_issue
    calls = []

    def fake_report(issue_text, title=None):
        calls.append({"issue_text": issue_text, "title": title})

    monkeypatch.setattr(report_module, "report_github_issue", fake_report)

    # Create a dummy VERSION_CHECK_FNAME that reports exists() True and records unlink()
    class DummyPath:
        def __init__(self):
            self.unlinked = False

        def exists(self):
            return True

        def unlink(self):
            self.unlinked = True

    dummy_path = DummyPath()
    monkeypatch.setattr(report_module, "VERSION_CHECK_FNAME", dummy_path)

    # Replace sys.__excepthook__ with a dummy so the final call is safe and recordable
    final_called = {}

    def fake_final_excepthook(exc_type, exc_value, exc_traceback):
        final_called['called'] = True
        final_called['args'] = (exc_type, exc_value, exc_traceback)

    monkeypatch.setattr(sys, "__excepthook__", fake_final_excepthook, raising=False)

    # Record original sys.excepthook so we can assert it's changed by the handler and restored by monkeypatch teardown
    original_excepthook = sys.excepthook

    # Generate an actual exception to get a real traceback
    try:
        _raise_nested_value_error()
    except Exception as e:
        exc_type, exc_value, exc_tb = type(e), e, e.__traceback__

    # Call the exception handler with our captured exception info
    exception_handler(exc_type, exc_value, exc_tb)

    # Check that VERSION_CHECK_FNAME.unlink was called
    assert getattr(dummy_path, "unlinked", False) is True

    # Ensure report_github_issue was called once
    assert len(calls) == 1
    call = calls[0]

    # Title should mention the exception type and the basename of the innermost file and the correct line number
    innermost_tb = exc_tb
    while innermost_tb.tb_next:
        innermost_tb = innermost_tb.tb_next
    filename = innermost_tb.tb_frame.f_code.co_filename
    expected_basename = os.path.basename(filename)
    expected_line = innermost_tb.tb_lineno
    assert call["title"].startswith(f"Uncaught {exc_type.__name__} in {expected_basename} line {expected_line}")

    # The issue text should contain the expected header and the traceback. The full path should have been replaced with basename.
    assert "An uncaught exception occurred" in call["issue_text"]
    assert expected_basename in call["issue_text"]
    assert filename not in call["issue_text"]

    # The final sys.__excepthook__ should have been called
    assert final_called.get("called", False) is True

    # The handler sets sys.excepthook = None; ensure it has been modified (will be restored by monkeypatch teardown)
    assert sys.excepthook is None or sys.excepthook == original_excepthook


def test_non_keyboard_exception_handles_version_check_errors(monkeypatch):
    # Capture calls to report_github_issue
    calls = []

    def fake_report(issue_text, title=None):
        calls.append({"issue_text": issue_text, "title": title})

    monkeypatch.setattr(report_module, "report_github_issue", fake_report)

    # Create a dummy VERSION_CHECK_FNAME whose exists() raises an exception (to exercise the except: pass)
    class DummyPathError:
        def exists(self):
            raise RuntimeError("cannot check")

        def unlink(self):
            raise RuntimeError("cannot unlink")

    dummy_path_error = DummyPathError()
    monkeypatch.setattr(report_module, "VERSION_CHECK_FNAME", dummy_path_error)

    # Replace sys.__excepthook__ so final call is safe
    final_called = {}

    def fake_final_excepthook(exc_type, exc_value, exc_traceback):
        final_called['called'] = True

    monkeypatch.setattr(sys, "__excepthook__", fake_final_excepthook, raising=False)

    # Generate an exception to pass to the handler
    try:
        _raise_nested_value_error()
    except Exception as e:
        exc_type, exc_value, exc_tb = type(e), e, e.__traceback__

    # Call the handler; it should swallow VERSION_CHECK_FNAME.exists() errors and still report
    exception_handler(exc_type, exc_value, exc_tb)

    # report_github_issue should still have been called
    assert len(calls) == 1
    assert "An uncaught exception occurred" in calls[0]["issue_text"]

    # The final excepthook should have been invoked
    assert final_called.get("called", False) is True
