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
    def test_generated_code_string_glob_is_converted_to_list_and_applied(self):
        """
        Ensure that when generated_code mapping returns a string for a language/framework,
        the code converts it to a list (glob_patterns = [glob_patterns]) and those globs
        are applied to filter files.
        """
        settings = get_settings()

        # Save originals to restore later
        had_ignore = hasattr(settings, 'ignore')
        orig_ignore = getattr(settings, 'ignore', None)
        had_config = hasattr(settings, 'config')
        orig_config = getattr(settings, 'config', None)
        had_generated = hasattr(settings, 'generated_code')
        orig_generated = getattr(settings, 'generated_code', None)

        try:
            # Ensure ignore exists and set its glob/regex to empty lists
            if not had_ignore or settings.ignore is None:
                class _IgnoreObj: pass
                settings.ignore = _IgnoreObj()
            # Try attribute style first, fall back to dict-like
            try:
                settings.ignore.glob = []
            except Exception:
                try:
                    settings.ignore['glob'] = []
                except Exception:
                    pass
            try:
                settings.ignore.regex = []
            except Exception:
                try:
                    settings.ignore['regex'] = []
                except Exception:
                    pass

            # Ensure config.ignore_language_framework is a list with one entry
            if isinstance(getattr(settings, 'config', None), dict):
                settings.config['ignore_language_framework'] = ['protobuf']
            else:
                try:
                    setattr(settings.config, 'ignore_language_framework', ['protobuf'])
                except Exception:
                    # fallback: replace config with a simple dict
                    settings.config = {'ignore_language_framework': ['protobuf']}

            # Ensure generated_code exists and set protobuf entry to a string (not a list)
            if not had_generated or settings.generated_code is None:
                settings.generated_code = {}
            try:
                settings.generated_code['protobuf'] = '**/*.pb.go'
            except Exception:
                # if generated_code isn't dict-like, set it to a dict
                settings.generated_code = {'protobuf': '**/*.pb.go'}

            # Prepare files: some should be filtered out by the protobuf glob string
            files = [
                type('', (object,), {'filename': 'main.go'})(),
                type('', (object,), {'filename': 'dir/service.pb.go'})(),
                type('', (object,), {'filename': 'file.pb.go'})(),
                type('', (object,), {'filename': 'util.go'})()
            ]

            expected = [
                files[0],
                files[3]
            ]

            filtered = filter_ignored(files)
            self.assertEqual(
                filtered,
                expected,
                f"Expected {[f.filename for f in expected]}, but got {[f.filename for f in filtered]}"
            )
        finally:
            # Restore originals
            if had_ignore:
                settings.ignore = orig_ignore
            else:
                try:
                    delattr(settings, 'ignore')
                except Exception:
                    pass

            if had_config:
                settings.config = orig_config
            else:
                try:
                    delattr(settings, 'config')
                except Exception:
                    pass

            if had_generated:
                settings.generated_code = orig_generated
            else:
                try:
                    delattr(settings, 'generated_code')
                except Exception:
                    pass
