import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.inspector.server')
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
        """Test append_results inserts an evaluation report when trajectory file exists and model_stats present."""
        # Prepare a temporary trajectory file with "info" and "model_stats"
        instance_id = "inst1"
        traj_data = {
            "info": {
                "exit_status": "success",
                "model_stats": {
                    "instance_cost": 1.2345,
                    "tokens_sent": 1234,
                    "tokens_received": 5678,
                    "api_calls": 3,
                },
            }
        }

        filename = "tmp_test_case_XX.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(json.dumps(traj_data))

            traj_path = Path(filename)

            # content has no trajectory key to exercise creation of trajectory list
            content = {}
            results = {
                "completed_ids": {instance_id},
                "submitted_ids": {instance_id},
                "resolved_ids": {instance_id},
            }
            results_file = "results.json"

            updated = append_results(traj_path, instance_id, content, results, results_file)

            # Trajectory must be created and contain two reports (first and last)
            self.assertIn("trajectory", updated)
            self.assertIsInstance(updated["trajectory"], list)
            self.assertGreaterEqual(len(updated["trajectory"]), 2)
            self.assertEqual(updated["trajectory"][0], updated["trajectory"][-1])

            report = updated["trajectory"][0]
            # Check report structure
            self.assertIsInstance(report, dict)
            self.assertEqual(report.get("thought"), "Evaluation Report")
            self.assertIn("observation", report)

            obs = report["observation"]
            # Check stats formatting
            self.assertIn("Exit Status: success", obs)
            self.assertIn("Instance Cost: $1.23", obs)
            self.assertIn("Tokens Sent: 1,234", obs)
            self.assertIn("Tokens Received: 5,678", obs)
            self.assertIn("API Calls: 3", obs)

            # Check status section shows all checkmarks for this instance
            self.assertIn("✅ Completed", obs)
            self.assertIn("✅ Submitted", obs)
            self.assertIn("✅ Resolved", obs)
            self.assertIn(f"Instance ID: {instance_id}", obs)
        finally:
            try:
                os.unlink(filename)
            except Exception:
                pass
