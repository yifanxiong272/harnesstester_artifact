# file: aider/coders/base_coder.py:1226-1331
# asked: {"lines": [1234, 1235, 1236, 1237, 1238, 1239, 1240, 1271, 1272, 1273, 1292, 1306, 1322, 1324, 1325, 1326, 1327, 1329], "branches": [[1233, 1234], [1234, 1235], [1234, 1236], [1236, 1237], [1236, 1240], [1249, 1261], [1261, 1264], [1266, 1271], [1285, 1292], [1302, 1306], [1315, 1331], [1320, 1322], [1322, 1324], [1322, 1331]]}
# gained: {"lines": [1234, 1235, 1236, 1237, 1238, 1239, 1240, 1271, 1272, 1273, 1292, 1306, 1322, 1324, 1325, 1326, 1327, 1329], "branches": [[1233, 1234], [1234, 1235], [1236, 1237], [1236, 1240], [1249, 1261], [1261, 1264], [1266, 1271], [1285, 1292], [1302, 1306], [1315, 1331], [1320, 1322], [1322, 1324]]}

import pytest

from aider.coders.base_coder import Coder


class DummyPrompts:
    def __init__(self, main_system="", example_messages=None, system_reminder=None):
        self.main_system = main_system
        self.example_messages = example_messages or []
        self.system_reminder = system_reminder


class DummyModel:
    def __init__(
        self,
        examples_as_sys_msg=False,
        system_prompt_prefix="",
        use_system_prompt=True,
        reminder="sys",
        token_count_fn=None,
        info=None,
    ):
        self.examples_as_sys_msg = examples_as_sys_msg
        self.system_prompt_prefix = system_prompt_prefix
        self.use_system_prompt = use_system_prompt
        self.reminder = reminder
        # token_count_fn should be a callable(messages) -> int or None
        self._token_count_fn = token_count_fn or (lambda msgs: 1)
        self.info = info or {}

    def token_count(self, messages):
        return self._token_count_fn(messages)


class DummyCoder(Coder):
    """
    Minimal subclass to provide the attributes and methods used by format_chat_chunks.
    """

    def __init__(self, gpt_prompts, main_model, cur_messages=None):
        # do not call super().__init__; instead directly set attributes used by format_chat_chunks
        self.gpt_prompts = gpt_prompts
        self.main_model = main_model
        self.done_messages = [{"role": "assistant", "content": "done"}]
        self._cur_messages = list(cur_messages or [])
        # counters / placeholders for methods invoked
        self.repo_messages = [{"role": "system", "content": "repo"}]
        self.readonly_files_messages = [{"role": "system", "content": "ro"}]
        self.chat_files_messages = [{"role": "system", "content": "chat"}]

    # methods used inside format_chat_chunks
    def choose_fence(self):
        # no-op for tests
        pass

    def fmt_system_prompt(self, content):
        # mark formatted prompts clearly for assertions
        return f"[FMT:{content}]"

    @property
    def cur_messages(self):
        return list(self._cur_messages)

    def summarize_end(self):
        # ensure done_messages remains accessible (simulate summary)
        self.done_messages = list(self.done_messages)

    def get_repo_messages(self):
        return list(self.repo_messages)

    def get_readonly_files_messages(self):
        return list(self.readonly_files_messages)

    def get_chat_files_messages(self):
        return list(self.chat_files_messages)


def test_examples_as_sys_msg_with_sys_reminder_sets_reminder():
    # Arrange: examples_as_sys_msg True, one example message, system reminder present,
    # use_system_prompt True, small token counts so reminder gets included as 'sys'.
    prompts = DummyPrompts(
        main_system="Main system text",
        example_messages=[{"role": "assistant", "content": "example1"}],
        system_reminder="Please remember X",
    )

    def token_count_fn(msgs):
        # small counts to ensure total_tokens < max_input_tokens
        return 1

    model = DummyModel(
        examples_as_sys_msg=True,
        system_prompt_prefix="PREFIX",
        use_system_prompt=True,
        reminder="sys",
        token_count_fn=token_count_fn,
        info={"max_input_tokens": 100},
    )

    coder = DummyCoder(gpt_prompts=prompts, main_model=model, cur_messages=[])

    # Act
    chunks = coder.format_chat_chunks()

    # Assert: system chunk should be a single system role entry
    assert isinstance(chunks.system, list) and len(chunks.system) == 1
    sys_msg = chunks.system[0]
    assert sys_msg["role"] == "system"
    # should include prefix, the formatted main system, formatted example, and formatted reminder
    assert "PREFIX" in sys_msg["content"]
    assert "[FMT:Main system text]" in sys_msg["content"]
    assert "## ASSISTANT:" in sys_msg["content"]
    assert "[FMT:example1]" in sys_msg["content"]
    assert "[FMT:Please remember X]" in sys_msg["content"]

    # reminder should be set as system because model.reminder == 'sys'
    assert chunks.reminder == [{"role": "system", "content": "[FMT:Please remember X]"}]

    # examples should not be returned in chunks.examples when examples_as_sys_msg is True
    assert chunks.examples == []


def test_examples_as_user_and_user_reminder_appended_and_token_counts_none():
    # Arrange: examples_as_sys_msg False, example_messages non-empty so extra two example messages appended,
    # use_system_prompt False to hit the user/assistant system path, token_count returns None so total_tokens = 0,
    # reminder == 'user' and cur_messages last role is 'user' so reminder is appended into the user message.
    prompts = DummyPrompts(
        main_system="Main system text A",
        example_messages=[{"role": "user", "content": "ex-u"}, {"role": "assistant", "content": "ex-a"}],
        system_reminder="Don't forget Y",
    )

    def token_count_fn(msgs):
        # Return None to exercise the total_tokens=0 branch
        return None

    model = DummyModel(
        examples_as_sys_msg=False,
        system_prompt_prefix="",
        use_system_prompt=False,
        reminder="user",
        token_count_fn=token_count_fn,
        info={"max_input_tokens": 0},  # zero triggers 'not max_input_tokens' truthy
    )

    # cur_messages with a final user message to trigger the 'user' reminder insertion
    cur_messages = [{"role": "user", "content": "current question"}]

    coder = DummyCoder(gpt_prompts=prompts, main_model=model, cur_messages=cur_messages)

    # Act
    chunks = coder.format_chat_chunks()

    # Assert: system should be user + assistant when use_system_prompt is False
    assert len(chunks.system) == 2
    assert chunks.system[0]["role"] == "user"
    assert "[FMT:Main system text A]" in chunks.system[0]["content"]
    assert chunks.system[1]["role"] == "assistant"
    assert chunks.system[1]["content"] == "Ok."

    # examples should include the formatted examples and the appended "I switched..." and "Ok." pair
    assert isinstance(chunks.examples, list)
    # original two examples plus two appended => 4
    assert len(chunks.examples) == 4
    assert chunks.examples[-2]["role"] == "user"
    assert "I switched to a new code base" in chunks.examples[-2]["content"]
    assert chunks.examples[-1]["role"] == "assistant"
    assert chunks.examples[-1]["content"] == "Ok."

    # Because token_count returned None -> total_tokens = 0 and max_input_tokens == 0 -> condition true,
    # and model.reminder == 'user' and final role == 'user' -> last cur message should have appended reminder
    assert chunks.cur  # cur_messages should exist
    last = chunks.cur[-1]
    assert last["role"] == "user"
    assert "[FMT:Don't forget Y]" in last["content"]
    # ensure the original content is preserved at the start
    assert last["content"].startswith("current question")


def test_no_system_reminder_results_in_empty_reminder_and_skips_insertion_when_tokens_exceed_limit():
    # Arrange: no system_reminder -> reminder_message = [] branch, cur_messages empty so final is None,
    # token_count returns large numbers so total_tokens >= max_input_tokens and no reminder inserted.
    prompts = DummyPrompts(
        main_system="MS",
        example_messages=[],
        system_reminder=None,  # No reminder
    )

    def token_count_fn(msgs):
        # Large token counts to ensure total_tokens > max_input_tokens
        return 1000

    model = DummyModel(
        examples_as_sys_msg=False,
        system_prompt_prefix="",
        use_system_prompt=False,
        reminder="sys",
        token_count_fn=token_count_fn,
        info={"max_input_tokens": 10},  # small limit so total_tokens > max_input_tokens
    )

    coder = DummyCoder(gpt_prompts=prompts, main_model=model, cur_messages=[])

    # Act
    chunks = coder.format_chat_chunks()

    # Assert: reminder_message should have been set to [] internally resulting in no reminder added
    assert chunks.reminder == []
    # cur is empty as provided
    assert chunks.cur == []
    # system must be user + assistant because use_system_prompt False
    assert len(chunks.system) == 2 and chunks.system[0]["role"] == "user" and chunks.system[1]["role"] == "assistant"
    # examples empty as provided
    assert chunks.examples == []
