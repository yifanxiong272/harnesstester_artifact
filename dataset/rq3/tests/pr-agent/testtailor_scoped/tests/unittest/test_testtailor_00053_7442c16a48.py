import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.pr_processing')
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
        """Ensure that when disable_extra_lines=True the function passes 0 for extra lines
        into pr_generate_extended_diff and returns the joined extended patches."""
        # Minimal fake GitProvider with the methods used by get_pr_diff
        class FakeGitProvider:
            def get_diff_files(self):
                return []  # no diff files needed for this test

            def get_languages(self):
                return {}  # empty languages -> pr_languages will be empty

        # Minimal fake token handler with required interface
        class FakeTokenHandler:
            def __init__(self):
                self.prompt_tokens = 0

            def count_tokens(self, text: str, force_accurate: bool = False):
                # simple token count approximation
                return len(text.split())

        git_provider = FakeGitProvider()
        token_handler = FakeTokenHandler()

        # Patch the pr_generate_extended_diff and get_max_tokens used inside get_pr_diff via its globals
        fn_globals = get_pr_diff.__globals__
        orig_pr_generate = fn_globals.get('pr_generate_extended_diff')
        orig_get_max_tokens = fn_globals.get('get_max_tokens')

        def fake_pr_generate_extended_diff(pr_languages, token_handler_arg, add_line_numbers_to_hunks,
                                           patch_extra_lines_before=999, patch_extra_lines_after=999):
            # The crux of the test: when disable_extra_lines=True, these should be zero
            self.assertEqual(patch_extra_lines_before, 0, "patch_extra_lines_before was not set to 0")
            self.assertEqual(patch_extra_lines_after, 0, "patch_extra_lines_after was not set to 0")
            # Return a small fake extended patch and token counts so get_pr_diff will take the early return path
            return (["FAKE_PATCH_CONTENT"], 10, [10])

        try:
            fn_globals['pr_generate_extended_diff'] = fake_pr_generate_extended_diff
            # ensure get_max_tokens is large enough so total_tokens + SOFT_THRESHOLD < get_max_tokens
            fn_globals['get_max_tokens'] = lambda model: 10000

            result = get_pr_diff(git_provider=git_provider,
                                 token_handler=token_handler,
                                 model="any-model",
                                 add_line_numbers_to_hunks=False,
                                 disable_extra_lines=True)

            # Expect the joined patches_extended result
            self.assertEqual(result, "FAKE_PATCH_CONTENT")
        finally:
            # restore originals
            if orig_pr_generate is not None:
                fn_globals['pr_generate_extended_diff'] = orig_pr_generate
            if orig_get_max_tokens is not None:
                fn_globals['get_max_tokens'] = orig_get_max_tokens
