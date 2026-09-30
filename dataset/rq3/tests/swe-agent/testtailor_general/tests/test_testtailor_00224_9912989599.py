import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.swe_bench_evaluate')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Warns (logger.error) when a running call finished with non-zero returncode and stderr is read."""
        output_dir = Path("tmp_sb_eval_test_case_XX")
        created = False
        try:
            if not output_dir.exists():
                output_dir.mkdir()
                created = True

            # create evaluator
            ev = SweBenchEvaluate(output_dir=output_dir, subset="lite", split="dev", continuous_submission_every=0)

            # create a fake call that has finished (poll() != None) and failed (returncode != 0)
            class FakeStderr:
                def __init__(self):
                    self._data = b"submission failed"

                def read(self):
                    return self._data

            class FakeCall:
                def __init__(self):
                    self.returncode = 1
                    self._stderr = FakeStderr()

                def poll(self):
                    return 1  # non-None indicates process finished

                @property
                def stderr(self):
                    return self._stderr

            fake = FakeCall()

            # attach a mock logger to capture error calls
            ev.logger = Mock()

            # put the fake call into the running calls list
            ev._running_calls = [fake]

            # execute the method under test
            ev.check_running_calls()

            # assert logger.error was called with the stderr content
            ev.logger.error.assert_called_with("Failed to submit results to SweBench eval: %s", fake.stderr.read())

            # the finished call should have been removed from _running_calls
            self.assertEqual(ev._running_calls, [])
        finally:
            # cleanup created directory if empty
            try:
                if created and output_dir.exists():
                    output_dir.rmdir()
            except Exception:
                pass
