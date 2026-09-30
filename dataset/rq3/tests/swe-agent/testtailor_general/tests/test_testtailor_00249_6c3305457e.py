import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.inspector_cli')
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
        """Test that load_trajectory replaces trajectory data, updates metadata, and calls scroll/update."""
        tempfile = __import__("tempfile")
        json = __import__("json")
        os = __import__("os")
        Path = __import__("pathlib").Path
        Mock = __import__("unittest.mock", fromlist=["Mock"]).Mock

        # create initial temp trajectory file
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        initial_data = {"trajectory": [], "info": {"meta": "initial"}}
        json.dump(initial_data, tmp)
        tmp.flush()
        tmp.close()
        path = Path(tmp.name)

        try:
            # instantiate viewer with the initial file
            viewer = TrajectoryViewer(path, "initial title", {"result": "initial"})

            # Replace scroll_top and update_content with mocks so we don't depend on Textual runtime
            viewer.scroll_top = Mock()
            viewer.update_content = Mock()

            # prepare new trajectory content and write it to the same path
            new_data = {"trajectory": [{"action": "do_something"}], "info": {"meta": "updated"}}
            with open(path, "w") as fh:
                json.dump(new_data, fh)

            # call load_trajectory which should read the new file and update state
            viewer.load_trajectory(path, "new title", {"result": "updated"}, gold_patch="patch-123")

            # assertions: state updated accordingly
            self.assertEqual(viewer.trajectory, new_data)
            self.assertEqual(viewer.title, "new title")
            self.assertEqual(viewer.gold_patch, "patch-123")
            self.assertEqual(viewer.overview_stats, {"result": "updated"})
            # i_step must be reset to -1
            self.assertEqual(viewer.i_step, -1)
            # ensure scroll_top and update_content were invoked
            viewer.scroll_top.assert_called_once()
            viewer.update_content.assert_called_once()
        finally:
            # cleanup temp file
            try:
                os.remove(path)
            except Exception:
                pass
