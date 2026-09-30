import json
import importlib
import pytest

mod = importlib.import_module('openhands.llm.fn_call_converter')

# Helper simple stubs used in multiple tests
def _setup_basic_env(monkeypatch):
    # deterministic tool description and system prompt suffix
    monkeypatch.setattr(mod, 'convert_tools_to_description', lambda tools: 'TOOL_DESC')
    monkeypatch.setattr(
        mod,
        'SYSTEM_PROMPT_SUFFIX_TEMPLATE',
        '{description}-SUFFIX'
    )
    # in-context example prefix and suffix
    monkeypatch.setattr(mod, 'IN_CONTEXT_LEARNING_EXAMPLE_PREFIX', lambda tools: 'EXAMPLE:')
    monkeypatch.setattr(mod, 'IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX', '::END')


def test_system_message_list_append_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # system content is a list whose last element is not a text -> should append a text element
    messages = [{'role': 'system', 'content': [{'type': 'image', 'url': 'u'}]}]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]['role'] == 'system'
    content = out[0]['content']
    # last element should be appended text node with suffix
    assert isinstance(content, list)
    assert content[-1]['type'] == 'text'
    assert content[-1]['text'] == 'TOOL_DESC-SUFFIX'


def test_system_message_str_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    messages = [{'role': 'system', 'content': 'hello'}]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]['role'] == 'system'
    assert out[0]['content'].endswith('TOOL_DESC-SUFFIX')
    assert out[0]['content'].startswith('hello')


def test_user_message_add_example_str_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # first user message should get the example prepended/appended for str content
    messages = [{'role': 'user', 'content': 'hi there'}]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=['toolA'])
    assert out[0]['role'] == 'user'
    assert out[0]['content'] == 'EXAMPLE:' + 'hi there' + '::END'


def test_user_message_add_example_list_else_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # content is a list whose first element is not 'text' -> should create text wrapper elements
    orig = [{'type': 'image', 'url': 'u'}]
    messages = [{'role': 'user', 'content': orig}]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=['t'])
    assert out[0]['role'] == 'user'
    content = out[0]['content']
    # should have text node at beginning and end created by example wrapper
    assert isinstance(content, list)
    assert content[0]['type'] == 'text'
    assert content[0]['text'] == 'EXAMPLE:'
    assert content[-1]['type'] == 'text'
    assert content[-1]['text'] == '::END'


def test_user_message_unexpected_content_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # user content that is neither str nor list should raise FunctionCallConversionError
    messages = [{'role': 'user', 'content': 123}]
    with pytest.raises(mod.FunctionCallConversionError) as exc:
        mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=['t'])
    assert 'Unexpected content type' in str(exc.value)


def test_assistant_tool_calls_multiple_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # assistant with multiple tool_calls should raise
    messages = [
        {'role': 'assistant', 'content': 'ok', 'tool_calls': ['a', 'b']}
    ]
    with pytest.raises(mod.FunctionCallConversionError) as exc:
        mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert 'Expected exactly one tool call' in str(exc.value)


def test_assistant_tool_call_conversion_failed_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # convert_tool_call_to_string raises -> should re-raise new FunctionCallConversionError including raw messages
    def raise_conv(tool_call):
        raise mod.FunctionCallConversionError('inner failure')

    monkeypatch.setattr(mod, 'convert_tool_call_to_string', raise_conv)
    messages = [
        {'role': 'assistant', 'content': 'resp', 'tool_calls': [{'tool': 'x'}]}
    ]
    with pytest.raises(mod.FunctionCallConversionError) as exc:
        mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    msg = str(exc.value)
    assert 'Failed to convert tool call to string.' in msg
    # raw messages JSON should be included
    assert 'Current tool call' in msg or json.dumps(messages)[:5] in msg


def test_assistant_tool_call_append_to_list_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # convert_tool_call_to_string returns text; content is list with last element not text -> append
    monkeypatch.setattr(mod, 'convert_tool_call_to_string', lambda tc: 'RESULT_TEXT')
    messages = [
        {'role': 'assistant', 'content': [{'type': 'image', 'url': 'u'}], 'tool_calls': [{'tool': 'x'}]}
    ]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]['role'] == 'assistant'
    content = out[0]['content']
    assert content[-1]['type'] == 'text'
    assert content[-1]['text'] == 'RESULT_TEXT'


def test_assistant_tool_call_modify_last_text_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # last element is text -> it should be appended to and then left-stripped
    monkeypatch.setattr(mod, 'convert_tool_call_to_string', lambda tc: 'TOOLX')
    messages = [
        {'role': 'assistant', 'content': [{'type': 'text', 'text': '   leading'}, {'type': 'text', 'text': '  prevlast'}], 'tool_calls': [{'tool': 'x'}]}
    ]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    content = out[0]['content']
    # last element text should include TOOLX and should have no leading whitespace (due to lstrip)
    assert 'TOOLX' in content[-1]['text']
    assert not content[-1]['text'].startswith(' ')


def test_tool_role_list_first_text_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # tool with a first text element -> prefix should be injected into that text
    messages = [
        {'role': 'tool', 'name': 'mytool', 'content': [{'type': 'text', 'text': 'RESULT'}], 'cache_control': True}
    ]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]['role'] == 'user'
    content = out[0]['content']
    assert content[0]['text'].startswith('EXECUTION RESULT of [mytool]:\n')
    # cache_control should be added to the last element
    assert content[-1].get('cache_control') == {'type': 'ephemeral'}


def test_tool_role_list_no_text_and_str_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # case when list has no text -> prefix inserted as first element
    messages = [
        {'role': 'tool', 'name': 'T1', 'content': [{'type': 'image', 'url': 'u'}]}
    ]
    out = mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    content = out[0]['content']
    assert content[0]['type'] == 'text'
    assert content[0]['text'].startswith('EXECUTION RESULT of [T1]:\n')

    # case when content is str -> prefix + string
    messages2 = [{'role': 'tool', 'name': 'T2', 'content': 'plain text'}]
    out2 = mod.convert_fncall_messages_to_non_fncall_messages(messages2, tools=[])
    assert out2[0]['content'].startswith('EXECUTION RESULT of [T2]:\n')
    assert out2[0]['content'].endswith('plain text')


def test_tool_role_unexpected_content_type_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    # content is neither str nor list -> raise
    messages = [{'role': 'tool', 'name': 'x', 'content': 999}]
    with pytest.raises(mod.FunctionCallConversionError) as exc:
        mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert 'Unexpected content type' in str(exc.value)


def test_unexpected_role_round_048(monkeypatch):
    _setup_basic_env(monkeypatch)
    messages = [{'role': 'unknown', 'content': 'x'}]
    with pytest.raises(mod.FunctionCallConversionError) as exc:
        mod.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert 'Unexpected role' in str(exc.value)
