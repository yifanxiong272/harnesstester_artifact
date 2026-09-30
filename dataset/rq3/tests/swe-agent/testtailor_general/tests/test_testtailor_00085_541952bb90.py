import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.__init__')
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
        """Ensure get_rex_commit_hash returns the repo head hexsha when Repo is available."""
        import pkgutil
        import importlib
        import types
        import sys
        import tempfile
        import shutil
        from pathlib import Path

        # locate the function inside the package
        pkg = importlib.import_module("sweagent")
        target_module = None
        get_hash_fn = None

        for finder, name, ispkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
            mod = importlib.import_module(name)
            if hasattr(mod, "get_rex_commit_hash"):
                target_module = mod
                get_hash_fn = getattr(mod, "get_rex_commit_hash")
                break

        if get_hash_fn is None and hasattr(pkg, "get_rex_commit_hash"):
            target_module = pkg
            get_hash_fn = getattr(pkg, "get_rex_commit_hash")

        self.assertIsNotNone(get_hash_fn, "Could not find get_rex_commit_hash in package submodules")

        # prepare fake swerex module with a real file path
        tmpd = tempfile.mkdtemp()
        try:
            nested = Path(tmpd) / "a" / "b" / "c"
            nested.mkdir(parents=True, exist_ok=True)
            fake_file = nested / "file.py"
            fake_file.write_text("# fake swerex file")

            fake_swerex = types.ModuleType("swerex")
            fake_swerex.__file__ = str(fake_file)

            # prepare dummy repo object
            dummy_repo = types.SimpleNamespace(
                head=types.SimpleNamespace(object=types.SimpleNamespace(hexsha="deadbeef"))
            )

            # factory that returns our dummy repo (accepts any args/kwargs)
            def fake_repo_factory(*args, **kwargs):
                return dummy_repo

            # Backup originals to restore later
            orig_repo_in_globals = get_hash_fn.__globals__.get("Repo", None)
            orig_git_module = sys.modules.get("git", None)
            orig_swerex_module = sys.modules.get("swerex", None)

            # Inject our fake modules and Repo into the environment the function will use
            sys.modules["swerex"] = fake_swerex
            # ensure importing git.Repo inside function (if it does) returns our factory
            git_mod = types.ModuleType("git")
            git_mod.Repo = fake_repo_factory
            sys.modules["git"] = git_mod

            # Also inject Repo into the function's globals so direct global lookup will find it
            get_hash_fn.__globals__["Repo"] = fake_repo_factory

            try:
                result = get_hash_fn()
            finally:
                # restore globals and sys.modules
                if orig_repo_in_globals is None:
                    get_hash_fn.__globals__.pop("Repo", None)
                else:
                    get_hash_fn.__globals__["Repo"] = orig_repo_in_globals

                # restore git module
                if orig_git_module is None:
                    sys.modules.pop("git", None)
                else:
                    sys.modules["git"] = orig_git_module

                # restore swerex module
                if orig_swerex_module is None:
                    sys.modules.pop("swerex", None)
                else:
                    sys.modules["swerex"] = orig_swerex_module
        finally:
            shutil.rmtree(tmpd, ignore_errors=True)

        self.assertEqual(result, "deadbeef")
