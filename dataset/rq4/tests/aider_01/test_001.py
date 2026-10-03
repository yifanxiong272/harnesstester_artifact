import pytest
from aider.coders.base_coder import Coder


def test_probe_001_format_chat_chunks_no_system_reminder_does_not_mutate_final_user_message():
    # Patch module ChatChunks with a minimal, deterministic implementation
    import aider.coders.base_coder as base

    class MinimalChunks:
        def __init__(self):
            self.system = []
            self.examples = []
            self.done = []
            self.repo = []
            self.readonly_files = []
            self.chat_files = []
            self.cur = []
            self.reminder = []

        def all_messages(self):
            # deterministic aggregation used by token_count
            return (
                list(self.system)
                + list(self.examples)
                + list(self.done)
                + list(self.repo)
                + list(self.readonly_files)
                + list(self.chat_files)
                + list(self.cur)
            )

    base.ChatChunks = MinimalChunks

    # Build a minimal Coder instance without invoking its real __init__
    coder = object.__new__(Coder)

    # No-op choose_fence
    coder.choose_fence = lambda: None

    # fmt_system_prompt: safe deterministic stub that returns empty string for falsy input.
    # This avoids treating a missing reminder as a harness-induced exception while still
    # allowing detection of any mutation to the last user message.
    def fmt_system_prompt(content):
        if not content:
            return ""  # safe no-op for missing reminder
        return f"FMT:{content}"

    coder.fmt_system_prompt = fmt_system_prompt

    # gpt_prompts with falsy system_reminder (activation condition)
    class GP:
        main_system = "MAIN SYS"
        example_messages = []
        system_reminder = None

    coder.gpt_prompts = GP()

    # main_model configured so max_input_tokens is falsy and reminder == 'user'
    class MM:
        def __init__(self):
            self.system_prompt_prefix = None
            self.examples_as_sys_msg = False
            self.use_system_prompt = True
            self.reminder = "user"
            self.info = {"max_input_tokens": 0}

        def token_count(self, msgs):
            # deterministic token counts: non-empty -> 1, empty -> 0
            return 1 if msgs else 0

    coder.main_model = MM()

    # Other required methods/attributes used by format_chat_chunks
    coder.summarize_end = lambda: None
    coder.done_messages = []
    coder.get_repo_messages = lambda: []
    coder.get_readonly_files_messages = lambda: []
    coder.get_chat_files_messages = lambda: []

    # cur_messages must end with a user message
    original_user = {"role": "user", "content": "original user content"}
    coder.cur_messages = [{"role": "assistant", "content": "hello"}, original_user.copy()]

    # Call the entrypoint under test. The invariant expects no exception
    # and no mutation of the final user message.
    chunks = coder.format_chat_chunks()

    # Primary behavioral oracle: final user message content must be unchanged
    assert chunks.cur[-1]["content"] == original_user["content"]
