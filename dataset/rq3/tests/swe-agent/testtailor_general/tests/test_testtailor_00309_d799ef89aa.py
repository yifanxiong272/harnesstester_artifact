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
        """on_mount should call update_content"""
        # import required modules at runtime to avoid top-level import statements
        tempfile = __import__("tempfile")
        json = __import__("json")
        pathlib = __import__("pathlib")
        Path = pathlib.Path

        # create a minimal trajectory json file
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        try:
            tmp.write(json.dumps({"trajectory": [], "info": {}}))
            tmp.close()
            path = Path(tmp.name)

            viewer = TrajectoryViewer(path, "title", {"result": "ok"})
            # Replace update_content with a mock to avoid running UI code
            viewer.update_content = unittest.mock.MagicMock(name="update_content")

            # Call on_mount which should invoke update_content
            viewer.on_mount()

            # Assert the mock was called exactly once with no arguments
            self.assertTrue(viewer.update_content.called)
            viewer.update_content.assert_called_once_with()
        finally:
            # cleanup temp file
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
