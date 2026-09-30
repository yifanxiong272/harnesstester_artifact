import types
import builtins
import pytest

import aider.coders.base_coder as base_coder


class DummyChatChunks:
    """Minimal ChatChunks replacement used to exercise format_chat_chunks behavior.

    The real ChatChunks has many conveniences; format_chat_chunks only expects
    that the constructed chunks object supports assignment to attributes and an
    all_messages() method returning a list of message dicts. We implement that
    deterministically here.
    """

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
        # deterministically combine lists in a predictable order
        out = []
        out.extend(self.system or [])
        out.extend(self.examples or [])
        out.extend(self.done or [])
        out.extend(self.repo or [])
        out.extend(self.readonly_files or [])
        out.extend(self.chat_files or [])
        out.extend(self.cur or [])
        return out


def make_fake_self(
    *,
    fmt_system_prompt=lambda x: x,
    example_messages=None,
    main_system="MAIN",
    system_reminder=None,
    system_prompt_prefix=None,
    examples_as_sys_msg=False,
    use_system_prompt=True,
    reminder_mode=None,
    token_count_impl=None,
    cur_messages=None,
    done_messages=None,
):
    """Return a simple object with attributes expected by format_chat_chunks.

    We don't instantiate the full Coder; instead we call the unbound
    Coder.format_chat_chunks function with this object as self.
    """
    gpt_prompts = types.SimpleNamespace(
        main_system=main_system,
        example_messages=example_messages or [],
        system_reminder=system_reminder,
    )

    # Provide a main_model with necessary attributes and a token_count method.
    main_model = types.SimpleNamespace(
        system_prompt_prefix=system_prompt_prefix,
        examples_as_sys_msg=examples_as_sys_msg,
        use_system_prompt=use_system_prompt,
        reminder=reminder_mode,
        info={"max_input_tokens": None},
    )

    # token_count default: sum of len(contents) to produce deterministic integers
    def default_token_count(messages):
        try:
            return sum(len(m.get("content", "")) for m in (messages or []))
        except Exception:
            return 0

    main_model.token_count = token_count_impl or default_token_count

    obj = types.SimpleNamespace()
    obj.choose_fence = lambda: None
    obj.fmt_system_prompt = fmt_system_prompt
    obj.gpt_prompts = gpt_prompts
    obj.main_model = main_model
    obj.cur_messages = list(cur_messages or [])
    obj.done_messages = list(done_messages or [])

    # Provide no-op implementations for methods used by format_chat_chunks
    obj.summarize_end = lambda: None
    obj.get_repo_messages = lambda: []
    obj.get_readonly_files_messages = lambda: []
    obj.get_chat_files_messages = lambda: []

    return obj


@pytest.fixture(autouse=True)
def patch_chatchunks(monkeypatch):
    # Patch the ChatChunks symbol where the function resolves it.
    monkeypatch.setattr(base_coder, "ChatChunks", DummyChatChunks)
    yield


def test_examples_as_sys_msg_and_use_system_prompt_round_062():
    """Case: examples_as_sys_msg True, use_system_prompt True, reminder present,
    main_model.reminder == 'sys'. Assert system message includes examples and
    reminder gets placed into chunks.reminder.
    """

    # fmt_system_prompt will annotate content so we can assert it propagated.
    fmt = lambda s: f"FMT:{s}"

    example_msgs = [{"role": "assistant", "content": "egcontent"}]

    # token_count returns small deterministic ints so total_tokens < max_input_tokens
    def token_count(messages):
        # return positive int based on total content length
        return sum(len(m.get("content", "")) for m in (messages or []))

    fake = make_fake_self(
        fmt_system_prompt=fmt,
        example_messages=example_msgs,
        main_system="mainsys",
        system_reminder="rem_sys",
        system_prompt_prefix="PREFIX",
        examples_as_sys_msg=True,
        use_system_prompt=True,
        reminder_mode="sys",
        token_count_impl=token_count,
        cur_messages=[{"role": "user", "content": "hi"}],
    )

    # ensure some max_input_tokens large enough to allow including the reminder
    fake.main_model.info["max_input_tokens"] = 1000

    chunks = base_coder.Coder.format_chat_chunks(fake)

    # system should be set to a single system message and contain prefix
    assert isinstance(chunks.system, list)
    assert len(chunks.system) == 1
    system_content = chunks.system[0]["content"]
    assert "PREFIX" in system_content
    # examples rendered into the system prompt with the fmt wrapper
    assert "# Example conversations" in system_content
    assert "## ASSISTANT" in system_content
    assert "FMT:egcontent" in system_content

    # reminder should be set because main_model.reminder == 'sys'
    assert chunks.reminder == [{"role": "system", "content": fmt("rem_sys")}]


def test_examples_as_user_and_no_system_reminder_and_token_none_round_062():
    """Case: examples_as_sys_msg False, example messages exist -> examples list
    built; system_reminder is falsy so reminder_message empty; token_count returns
    None for the messages_tokens call to force total_tokens = 0 branch.
    """

    # fmt_system_prompt will insert a marker so token_count can detect it
    def fmt(s):
        return f"MARKER:{s}"

    example_msgs = [
        {"role": "user", "content": "ucontent"},
    ]

    # token_count returns None when encountering our MARKER to simulate an
    # inability to compute tokens for the full messages list.
    def token_count(messages):
        for m in (messages or []):
            if "MARKER:" in m.get("content", ""):
                return None
        # otherwise return deterministic small value
        return 1

    fake = make_fake_self(
        fmt_system_prompt=fmt,
        example_messages=example_msgs,
        main_system="mainsys",
        system_reminder=None,
        system_prompt_prefix=None,
        examples_as_sys_msg=False,
        use_system_prompt=False,
        reminder_mode=None,
        token_count_impl=token_count,
        cur_messages=[],
    )

    # Make the formatted system contain the MARKER so token_count returns None on
    # the first token_count call (messages_tokens), triggering total_tokens = 0.
    fake.gpt_prompts.main_system = "willbeformatted"

    chunks = base_coder.Coder.format_chat_chunks(fake)

    # When use_system_prompt is False, chunks.system should contain a user and
    # assistant message pair
    assert isinstance(chunks.system, list)
    assert len(chunks.system) == 2
    assert chunks.system[0]["role"] == "user"
    assert chunks.system[1]["role"] == "assistant"

    # examples should be built as a list of dicts and include the appended user
    # and assistant messages from the code path
    assert isinstance(chunks.examples, list)
    # original example present
    assert any(e["role"] == "user" and "ucontent" in e["content"] for e in chunks.examples)
    # the appended 'I switched to a new code base...' message exists
    assert any(e["role"] == "user" and "Please don't consider the above files" in e["content"] for e in chunks.examples)
    assert any(e["role"] == "assistant" and e["content"] == "Ok." for e in chunks.examples)

    # system_reminder was None -> reminder_message should be an empty list
    assert chunks.reminder == []


def test_user_reminder_merge_into_last_user_message_round_062():
    """Case: main_model.reminder == 'user' and final message exists and is a
    user message; system_reminder should be merged into the last user message
    content (with formatting).
    """

    def fmt(s):
        return f"FMT:{s}"

    example_msgs = []

    # token_count small numbers to ensure total_tokens < max_input_tokens
    def token_count(messages):
        return 1

    # last message in cur_messages is a user message
    cur = [{"role": "assistant", "content": "assistant here"}, {"role": "user", "content": "orig user"}]

    fake = make_fake_self(
        fmt_system_prompt=fmt,
        example_messages=example_msgs,
        main_system="mainsys",
        system_reminder="reminder text",
        system_prompt_prefix=None,
        examples_as_sys_msg=False,
        use_system_prompt=True,
        reminder_mode="user",
        token_count_impl=token_count,
        cur_messages=cur,
    )

    fake.main_model.info["max_input_tokens"] = 100

    chunks = base_coder.Coder.format_chat_chunks(fake)

    # The last cur message content should have the reminder appended via fmt
    assert chunks.cur[-1]["role"] == "user"
    assert "orig user" in chunks.cur[-1]["content"]
    assert "FMT:reminder text" in chunks.cur[-1]["content"]

    # reminder list itself should remain empty because we merged into the user
    assert chunks.reminder == []
