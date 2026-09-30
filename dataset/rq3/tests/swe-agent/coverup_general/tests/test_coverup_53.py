# file: sweagent/run/hooks/swe_bench_evaluate.py:57-63
# asked: {"lines": [57, 59, 60, 61, 62, 63], "branches": [[59, 0], [59, 60], [60, 59], [60, 61], [61, 62], [61, 63]]}
# gained: {"lines": [57, 59, 60, 61, 62, 63], "branches": [[59, 0], [59, 60], [60, 59], [60, 61], [61, 62], [61, 63]]}

import io
from pathlib import Path
import pytest

from sweagent.run.hooks.swe_bench_evaluate import SweBenchEvaluate


class DummyStdErr:
    def __init__(self, data: str):
        self._data = data

    def read(self):
        return self._data


class FakeProc:
    def __init__(self, poll_value, returncode, stderr_data=""):
        self._poll_value = poll_value
        self.returncode = returncode
        self.stderr = DummyStdErr(stderr_data)

    def poll(self):
        return self._poll_value


class MockLogger:
    def __init__(self):
        self.error_calls = []

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))


def make_sbe():
    # create a SweBenchEvaluate instance with harmless parameters
    return SweBenchEvaluate(output_dir=Path("."), subset="lite", split="test")


def test_check_running_calls_no_poll_remains_and_no_error(monkeypatch):
    sbe = make_sbe()
    mock_logger = MockLogger()
    sbe.logger = mock_logger

    proc = FakeProc(poll_value=None, returncode=None, stderr_data="nope")
    sbe._running_calls = [proc]

    sbe.check_running_calls()

    # since poll() returned None, the process should remain in the list
    assert sbe._running_calls == [proc]
    # and no error should have been logged
    assert mock_logger.error_calls == []


def test_check_running_calls_successful_removal_no_error(monkeypatch):
    sbe = make_sbe()
    mock_logger = MockLogger()
    sbe.logger = mock_logger

    proc = FakeProc(poll_value=0, returncode=0, stderr_data="ignored")
    sbe._running_calls = [proc]

    sbe.check_running_calls()

    # successful returncode (0) should remove the process
    assert sbe._running_calls == []
    # and no error logged for a successful run
    assert mock_logger.error_calls == []


def test_check_running_calls_failed_removal_and_error_logged(monkeypatch):
    sbe = make_sbe()
    mock_logger = MockLogger()
    sbe.logger = mock_logger

    proc = FakeProc(poll_value=1, returncode=2, stderr_data="bad stuff")
    sbe._running_calls = [proc]

    sbe.check_running_calls()

    # failed returncode should remove the process
    assert sbe._running_calls == []
    # and error should have been logged exactly once with the stderr content
    assert len(mock_logger.error_calls) == 1
    (args, kwargs) = mock_logger.error_calls[0]
    # first positional arg is the format string, second is the stderr read value
    assert args[0].startswith("Failed to submit results to SweBench eval")
    assert args[1] == "bad stuff"
