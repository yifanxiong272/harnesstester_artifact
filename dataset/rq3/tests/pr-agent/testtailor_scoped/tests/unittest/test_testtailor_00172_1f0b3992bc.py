import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_code_suggestions')
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
        """Test that when publish_output and publish_output_progress are True and the provider
        does not support gfm_markdown, we publish a temporary 'Preparing suggestions...' comment
        and later publish the 'No code suggestions found for the PR.' body."""
        # Helper mapping that supports both dict(...) conversion and attribute access
        class AttrDict(dict):
            def __init__(self, mapping=None):
                mapping = mapping or {}
                super().__init__(mapping)
                # copy keys to attributes for attribute-style access
                for k, v in mapping.items():
                    setattr(self, k, v)

            def get(self, key, default=None):
                return super().get(key, default)

        # Minimal dummy settings object
        class DummySettings:
            def __init__(self):
                # config must be convertible to dict(...) and allow attribute access
                self.config = AttrDict({
                    "publish_output": True,
                    "publish_output_progress": True,
                    "is_auto_command": False,
                    "temperature": 0.0,
                    "verbosity_level": 0,
                })
                # pr_code_suggestions also needs to be both dict-like and attribute-accessible
                self.pr_code_suggestions = AttrDict({
                    "publish_output_no_suggestions": True,
                    "commitable_code_suggestions": False,
                    "demand_code_suggestions_self_review": False,
                    "enable_chat_text": False,
                    "enable_help_text": False,
                    "persistent_comment": False,
                    "max_history_len": 1,
                    "dual_publishing_score_threshold": 0,
                    "num_code_suggestions_per_chunk": "1",
                    "decouple_hunks": True,
                    "parallel_calls": False,
                    "new_score_mechanism": False,
                })
                # used by generate_summarized_suggestions if invoked
                self.language_extension_map_org = {}
                # placeholders for storing prompts when publish_output is False in other flows
                self.system_prompt = None
                self.user_prompt = None

            def get(self, key, default=None):
                return getattr(self, key, default)

            def set(self, *args, **kwargs):
                # simple set implementation to avoid attribute errors if called
                if len(args) == 2 and isinstance(args[0], str):
                    # support dotted keys like "openai.deployment_id" by setting a flat attribute
                    setattr(self, args[0], args[1])
                elif len(args) == 1 and isinstance(args[0], dict):
                    for k, v in args[0].items():
                        setattr(self, k, v)
                else:
                    # fallback: accept kw args
                    for k, v in kwargs.items():
                        setattr(self, k, v)

        dummy_settings = DummySettings()

        # Create a fake git provider
        git_provider = MagicMock()
        git_provider.get_files.return_value = ["some_file.py"]  # non-empty so run() proceeds
        git_provider.is_supported.return_value = False  # trigger non-gfm path
        git_provider.publish_comment = MagicMock()
        git_provider.remove_initial_comment = MagicMock()
        git_provider.remove_comment = MagicMock()
        git_provider.edit_comment = MagicMock()
        git_provider.get_pr_description.return_value = ("desc", [])
        git_provider.pr = MagicMock()
        git_provider.pr.title = "PR Title"
        git_provider.get_pr_branch.return_value = "branch"
        git_provider.get_commit_messages.return_value = "commit msg"
        git_provider.get_diff_files.return_value = []

        # Create PRCodeSuggestions instance without invoking __init__
        inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
        inst.git_provider = git_provider
        inst.progress = "progress"
        inst.progress_response = None
        inst.pr_url = "http://pr"
        inst.data = None

        # Patch get_settings and retry_with_fallback_models in the module where PRCodeSuggestions is defined
        target_mod = "pr_agent.tools.pr_code_suggestions"

        # async fake retry that returns None (so code sets data to {"code_suggestions": []})
        async def fake_retry(f, model_type=None):
            return None

        with patch(f"{target_mod}.get_settings", return_value=dummy_settings), \
             patch(f"{target_mod}.retry_with_fallback_models", new=fake_retry):
            # Run the async run() method
            loop = asyncio.get_event_loop()
            loop.run_until_complete(inst.run())

        # Assertions:
        # First call should be the temporary "Preparing suggestions..." with is_temporary=True
        self.assertGreaterEqual(git_provider.publish_comment.call_count, 1)
        first_call = git_provider.publish_comment.call_args_list[0]
        # positional first arg is the comment text
        self.assertEqual(first_call[0][0], "Preparing suggestions...")
        # kwargs should include is_temporary=True
        self.assertIn('is_temporary', first_call[1])
        self.assertTrue(first_call[1]['is_temporary'])

        # After no suggestions, publish_comment should be called again with the PR body
        found_no_suggestions = False
        for call in git_provider.publish_comment.call_args_list:
            body_arg = call[0][0] if call[0] else ""
            if isinstance(body_arg, str) and body_arg.startswith("## PR Code Suggestions ✨"):
                found_no_suggestions = True
                self.assertIn("No code suggestions found for the PR.", body_arg)
                break
        self.assertTrue(found_no_suggestions, "Expected a follow-up publish_comment with no-suggestions body")
