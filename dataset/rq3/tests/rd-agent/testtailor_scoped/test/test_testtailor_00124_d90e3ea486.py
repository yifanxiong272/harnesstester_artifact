import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.mle_summary')
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
        """Create a competition pkl log and ensure save_grade_info reads it without initializing heavy eval."""
        # obtain globals used by the function under test to avoid relying on imports here
        gi = save_grade_info.__globals__
        Path = gi.get("Path", __import__("pathlib").Path)
        pickle = gi.get("pickle", __import__("pickle"))
        FileStorage = gi.get("FileStorage")
        # create a unique temporary folder under cwd to avoid needing tempfile/datetime imports
        uid = __import__("uuid").uuid4().hex
        base = Path.cwd() / f"tmp_save_grade_info_test_{uid}"
        base.mkdir(parents=True, exist_ok=True)

        try:
            comp_subdir = base / "competition" / "pid_1234"
            comp_subdir.mkdir(parents=True, exist_ok=True)

            # use a fixed timestamp format that FileStorage.iter_msg expects
            ts = "2020-01-01_00-00-00-000000"
            pkl_file = comp_subdir / f"{ts}.pkl"

            # write a simple competition content
            with pkl_file.open("wb") as f:
                pickle.dump("my_competition_id", f)

            # Monkeypatch get_test_eval in the save_grade_info globals to avoid heavy initialization
            orig_get = gi.get("get_test_eval")

            class _DummyEval:
                def eval(self, competition, workspace):
                    return "dummy_score"

            gi["get_test_eval"] = (lambda: _DummyEval())

            try:
                # run the function under test; it should iterate competition messages and not raise
                save_grade_info(base)
            finally:
                # restore original
                if orig_get is not None:
                    gi["get_test_eval"] = orig_get
                else:
                    gi.pop("get_test_eval", None)

            # verify that iter_msg can read back the message we created
            if FileStorage is None:
                FileStorage = gi.get("FileStorage", __import__("rdagent.log.storage", fromlist=["FileStorage"]).FileStorage)
            fs = FileStorage(base)
            msgs = list(fs.iter_msg(tag="competition"))
            self.assertEqual(len(msgs), 1)
            self.assertEqual(msgs[0].content, "my_competition_id")
        finally:
            # cleanup created folder
            __import__("shutil").rmtree(base, ignore_errors=True)
