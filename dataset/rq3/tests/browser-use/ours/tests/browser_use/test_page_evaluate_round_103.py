import types
import json
import pytest
from types import SimpleNamespace

from browser_use.actor.page import Page

# All tests are async and deterministic by providing fake self with patched collaborators.

@pytest.mark.asyncio
async def test_non_arrow_raises_round_103():
    """If the provided JS does not begin with '(' and contain '=>', a ValueError is raised."""
    fake_self = SimpleNamespace()

    async def _ensure_session():
        return "session-1"

    # _fix_javascript_string must be synchronous because evaluate calls it without awaiting
    def _fix_js(s):
        return "function foo() { return 1 }"

    fake_self._ensure_session = _ensure_session
    fake_self._fix_javascript_string = _fix_js

    # We don't need a _client for this test because it should raise before send is invoked.

    evaluate = types.MethodType(Page.evaluate, fake_self)

    with pytest.raises(ValueError) as exc:
        await evaluate("function foo() { return 1 }")
    assert "JavaScript code must start with (...args) => format" in str(exc.value)


@pytest.mark.asyncio
async def test_evaluate_no_args_none_value_round_103():
    """When evaluate returns result.value None, the method should return an empty string and the built expression should call with no args."""
    fake_self = SimpleNamespace()

    async def _ensure_session():
        return "sess-42"

    # synchronous fixer
    def _fix_js(s):
        # return unchanged arrow function
        return "(...args) => null"

    recorded = {}

    async def fake_runtime_evaluate(params, session_id=None):
        # record the params that were passed in for assertions
        recorded['params'] = params
        recorded['session_id'] = session_id
        return { 'result': { 'value': None } }

    fake_self._ensure_session = _ensure_session
    fake_self._fix_javascript_string = _fix_js
    fake_self._client = SimpleNamespace(send=SimpleNamespace(Runtime=SimpleNamespace(evaluate=fake_runtime_evaluate)))

    evaluate = types.MethodType(Page.evaluate, fake_self)

    out = await evaluate("(...args) => null")
    assert out == ""  # None maps to empty string

    # Assert the expression was built as (page_function)()
    assert recorded['params']['expression'] == "((...args) => null)()"
    assert recorded['session_id'] == "sess-42"


@pytest.mark.asyncio
async def test_evaluate_with_args_string_result_round_103():
    """With args provided, they are JSON-encoded and the returned string value is forwarded unchanged."""
    fake_self = SimpleNamespace()

    async def _ensure_session():
        return "S"

    def _fix_js(s):
        return "(a, b) => a + b"

    recorded = {}

    async def fake_runtime_evaluate(params, session_id=None):
        recorded['params'] = params
        recorded['session_id'] = session_id
        return {'result': {'value': 'concat-result'}}

    fake_self._ensure_session = _ensure_session
    fake_self._fix_javascript_string = _fix_js
    fake_self._client = SimpleNamespace(send=SimpleNamespace(Runtime=SimpleNamespace(evaluate=fake_runtime_evaluate)))

    evaluate = types.MethodType(Page.evaluate, fake_self)

    result = await evaluate("(a, b) => a + b", "x", 7)
    assert result == 'concat-result'

    # Args should be JSON serialized: "x" and 7 should appear in the expression
    expr = recorded['params']['expression']
    assert '"x"' in expr and '7' in expr
    # Ensure the overall expression starts with a '(' and contains the arrow function
    assert expr.startswith('(') and '=>' in expr


@pytest.mark.asyncio
async def test_evaluate_exception_details_round_103():
    """If the runtime returns 'exceptionDetails', a RuntimeError is raised containing that payload."""
    fake_self = SimpleNamespace()

    async def _ensure_session():
        return "sess-exc"

    def _fix_js(s):
        return "(...args) => { throw new Error('boom') }"

    async def fake_runtime_evaluate(params, session_id=None):
        return {'exceptionDetails': {'text': 'boom at runtime'}}

    fake_self._ensure_session = _ensure_session
    fake_self._fix_javascript_string = _fix_js
    fake_self._client = SimpleNamespace(send=SimpleNamespace(Runtime=SimpleNamespace(evaluate=fake_runtime_evaluate)))

    evaluate = types.MethodType(Page.evaluate, fake_self)

    with pytest.raises(RuntimeError) as exc:
        await evaluate("(...args) => { throw new Error('boom') }")
    assert 'JavaScript evaluation failed' in str(exc.value)
    assert 'boom at runtime' in str(exc.value)


@pytest.mark.asyncio
async def test_evaluate_dict_serialization_and_unserializable_round_103():
    """When the evaluated value is a dict/list it's JSON-dumped; if dumping fails it falls back to str(value)."""
    fake_self = SimpleNamespace()

    async def _ensure_session():
        return "sess-json"

    def _fix_js(s):
        return "(...args) => ({})"

    # First call: serializable dict
    async def fake_eval_serializable(params, session_id=None):
        return {'result': {'value': {'a': 1}}}

    # Second call: unserializable dict (contains raw object) -> json.dumps will raise TypeError
    obj = object()

    async def fake_eval_unserializable(params, session_id=None):
        return {'result': {'value': {'a': obj}}}

    # Test serializable case
    fake_self._ensure_session = _ensure_session
    fake_self._fix_javascript_string = _fix_js
    fake_self._client = SimpleNamespace(send=SimpleNamespace(Runtime=SimpleNamespace(evaluate=fake_eval_serializable)))
    evaluate = types.MethodType(Page.evaluate, fake_self)

    out_serializable = await evaluate("(...args) => ({})")
    # Should be JSON string of the dict
    assert out_serializable == json.dumps({'a': 1})

    # Test unserializable case by swapping the runtime evaluate
    fake_self._client = SimpleNamespace(send=SimpleNamespace(Runtime=SimpleNamespace(evaluate=fake_eval_unserializable)))
    evaluate = types.MethodType(Page.evaluate, fake_self)

    out_unserializable = await evaluate("(...args) => ({})")
    # Should fall back to python str(dict) representation which includes the key and the word 'object'
    assert out_unserializable.startswith("{'a':")
    assert 'object' in out_unserializable
