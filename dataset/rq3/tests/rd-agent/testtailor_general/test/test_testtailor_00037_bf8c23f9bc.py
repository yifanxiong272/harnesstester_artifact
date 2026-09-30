import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.benchmark.factor.analysis')
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
        """Test main path: patch BenchmarkAnalyzer to avoid filesystem and plotting side effects,
        and patch Plotter.plot_data to capture the data passed for plotting.
        """
        # keep originals to restore later
        orig_load_index_map = BenchmarkAnalyzer.load_index_map
        orig_process_results = BenchmarkAnalyzer.process_results
        orig_plot_data = Plotter.plot_data

        called = {}

        try:
            # Patch load_index_map so BenchmarkAnalyzer.__init__ won't read any file
            BenchmarkAnalyzer.load_index_map = lambda self: {"dummy_factor": ("dummy_factor", "Cat", "Easy")}

            # Fake process_results to return a mapping of experiment -> Series with required indices
            def fake_process_results(self, results):
                idx = [
                    "Avg Correlation",
                    "Avg Format SR",
                    "Avg Run SR",
                    "Max Correlation",
                    "Max Accuracy",
                    "Avg Accuracy",
                ]
                vals = [0.11, 0.22, 0.33, 0.44, 0.55, 0.66]
                name = list(results.keys())[0]
                ser = pd.Series(vals, index=idx, name=name)
                return {name: ser}

            BenchmarkAnalyzer.process_results = fake_process_results

            # Patch the plotting function to capture arguments instead of creating a file
            def fake_plot_data(data, file_name, title):
                called["data"] = data
                called["file_name"] = file_name
                called["title"] = title

            Plotter.plot_data = fake_plot_data

            # Call main; since we patched process_results and plot_data, no filesystem access occurs
            main(path="irrelevant.pkl", round=2, title="Unit Test Plot", only_correct_format=True)

            # Verify that our fake_plot_data was called and received expected parameters
            self.assertIn("data", called, "Plotter.plot_data was not called")
            self.assertEqual(called["file_name"], "./comparison_plot.png")
            self.assertEqual(called["title"], "Unit Test Plot")

            # The data passed should be the melted DataFrame with columns 'a' and 'b'
            data = called["data"]
            self.assertTrue(hasattr(data, "columns"))
            self.assertIn("a", data.columns)
            self.assertIn("b", data.columns)

        finally:
            # restore originals
            BenchmarkAnalyzer.load_index_map = orig_load_index_map
            BenchmarkAnalyzer.process_results = orig_process_results
            Plotter.plot_data = orig_plot_data
