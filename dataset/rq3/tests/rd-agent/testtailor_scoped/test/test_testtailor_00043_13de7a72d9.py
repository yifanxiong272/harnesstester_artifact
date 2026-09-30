import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.utils.health_check')
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
        """Locate the module that defines check_docker_status, patch its docker.from_env to raise
        DockerException so the function takes the exception branch (container stays None)
        and ensure it handles the error without raising.
        """
        # Find the rdagent package root
        rdagent_pkg = __import__("rdagent", fromlist=["*"])
        pkg_path = rdagent_pkg.__path__[0]
        from pathlib import Path

        target_module_name = None
        pkg_dir = Path(pkg_path).resolve()
        # Search for the file that contains the function definition
        for file in pkg_dir.rglob("*.py"):
            try:
                text = file.read_text(encoding="utf-8")
            except Exception:
                continue
            if "def check_docker_status" in text:
                fstr = str(file)
                # build module import path like "rdagent.sub.module"
                modname = fstr[fstr.index("rdagent") : -3].replace("/", ".").replace("\\", ".")
                target_module_name = modname
                break

        if target_module_name is None:
            self.skipTest("check_docker_status not found in rdagent package")

        # Import the target module
        target_module = __import__(target_module_name, fromlist=["*"])

        # Build a dummy docker module that raises DockerException from from_env()
        class DummyDockerModule:
            class errors:
                class DockerException(Exception):
                    pass

            @staticmethod
            def from_env():
                raise DummyDockerModule.errors.DockerException("docker unavailable")

        # Patch the module's docker attribute, call the function, ensure it doesn't raise and returns None.
        original_docker = getattr(target_module, "docker", None)
        target_module.docker = DummyDockerModule
        try:
            result = target_module.check_docker_status()
            # The function handles the exception internally and should return None
            self.assertIsNone(result)
        finally:
            # Restore original docker attribute
            if original_docker is None:
                try:
                    delattr(target_module, "docker")
                except Exception:
                    target_module.docker = None
            else:
                target_module.docker = original_docker
