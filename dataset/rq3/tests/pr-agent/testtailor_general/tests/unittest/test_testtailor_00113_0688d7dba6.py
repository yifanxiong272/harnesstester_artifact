import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.file_filter')
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
        """Ensure that when ignore.glob is provided as a string (like "[a,b]"),
        the code path that strips the brackets and splits the string is executed
        and the resulting glob patterns are applied to filter files.
        """
        # build a minimal settings object expected by filter_ignored
        class DummyIgnore:
            def __init__(self):
                # allow an empty list for regex so no extra regex is introduced
                self.regex = []
                # this is the important part: a string that needs strip('[]') and split(',')
                self.glob = "[foo.py,bar/*.py]"

        class DummySettings:
            pass

        s = DummySettings()
        s.ignore = DummyIgnore()
        # these dicts are referenced by the function; keep them empty for this test
        s.config = {}
        s.generated_code = {}

        # expected regexes corresponding to the globs after splitting and translation
        regexes = [r"^foo\.py$", r"^bar/.*\.py$"]

        # Locate the module that actually defines filter_ignored by scanning pr_agent package modules
        import pr_agent
        import pkgutil
        import importlib

        filter_module = None
        for finder, name, ispkg in pkgutil.walk_packages(pr_agent.__path__, prefix=pr_agent.__name__ + "."):
            try:
                m = importlib.import_module(name)
            except Exception:
                continue
            if hasattr(m, "filter_ignored"):
                filter_module = m
                break

        if filter_module is None:
            self.skipTest("Could not locate module defining filter_ignored")

        # Save originals to restore later
        orig_get_settings = getattr(filter_module, "get_settings", None)
        orig_translate = getattr(filter_module, "translate_globs_to_regexes", None)

        try:
            # Inject our test get_settings and translate_globs_to_regexes into the module
            setattr(filter_module, "get_settings", lambda *args, **kwargs: s)
            setattr(filter_module, "translate_globs_to_regexes", lambda globs: regexes)

            filter_ignored = getattr(filter_module, "filter_ignored")

            # create simple file-like objects with .filename attribute used by 'github' branch
            class F:
                def __init__(self, filename):
                    self.filename = filename
                def __repr__(self):
                    return f"F({self.filename})"

            files = [F("foo.py"), F("bar/baz.py"), F("keep.txt")]
            filtered = filter_ignored(files, platform="github")

            # Expect foo.py and bar/baz.py to be filtered out, keep.txt should remain
            assert isinstance(filtered, list)
            assert len(filtered) == 1
            assert filtered[0].filename == "keep.txt"
        finally:
            # restore original attributes if present
            if orig_get_settings is not None:
                setattr(filter_module, "get_settings", orig_get_settings)
            else:
                try:
                    delattr(filter_module, "get_settings")
                except Exception:
                    pass
            if orig_translate is not None:
                setattr(filter_module, "translate_globs_to_regexes", orig_translate)
            else:
                try:
                    delattr(filter_module, "translate_globs_to_regexes")
                except Exception:
                    pass
