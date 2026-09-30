import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_batch')
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
        """Run the batch with multiple workers to exercise main_multi_worker."""
        # Create a deterministic temporary output directory in the current working dir
        tmp_dir = Path.cwd() / "tmp_run_multi_worker_test"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Minimal problem-statement and instance objects expected by RunBatch
        class PS:
            def __init__(self, id_):
                self.id = id_

        class BI:
            def __init__(self, id_):
                self.problem_statement = PS(id_)
                self.env = None

        instances = [BI("inst_1"), BI("inst_2")]

        # Minimal no-op hook to satisfy add_hook -> on_init and later calls
        class NoOpHook:
            def on_init(self, run=None):
                return None

            def on_start(self):
                return None

            def on_instance_start(self, index, env, problem_statement):
                return None

            def on_instance_completed(self, result):
                return None

            def on_end(self):
                return None

        # Construct RunBatch with num_workers=2 so _num_workers > 1
        rb = RunBatch(
            instances=instances,
            agent_config=type("AC", (), {})(),
            output_dir=tmp_dir,
            hooks=[NoOpHook()],
            raise_exceptions=False,
            redo_existing=False,
            num_workers=2,
            progress_bar=False,
            random_delay_multiplier=0.0,
        )

        # Monkeypatch run_instance to do minimal expected work:
        # create the instance output dir and write a simple .traj file so assertions can check it.
        def fake_run_instance(instance):
            out = Path(rb.output_dir) / instance.problem_statement.id
            out.mkdir(parents=True, exist_ok=True)
            traj_path = out / f"{instance.problem_statement.id}.traj"
            traj_path.write_text("traj-placeholder")
            # Return a simple result object with .info for consistency with caller expectations
            return type("R", (), {"info": {"exit_status": "success"}})()

        rb.run_instance = fake_run_instance

        # Run main which should choose main_multi_worker path
        rb.main()

        # Verify that the .traj files were created by our fake run_instance
        self.assertTrue((tmp_dir / "inst_1" / "inst_1.traj").exists())
        self.assertTrue((tmp_dir / "inst_2" / "inst_2.traj").exists())
