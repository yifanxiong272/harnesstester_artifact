def test_probe_001():
    import asyncio
    import json
    from types import SimpleNamespace
    from browser_use.llm.openai.chat import ChatOpenAI, OpenAIMessageSerializer

    # Replace serializer with a deterministic implementation to avoid constructing BaseMessage
    orig_serialize = OpenAIMessageSerializer.serialize_messages
    OpenAIMessageSerializer.serialize_messages = lambda messages: [{'role': 'user', 'content': 'ping'}]

    try:
        # Create instance with explicit numeric hyperparameters
        chat = ChatOpenAI(model='o3', temperature=0.7, frequency_penalty=0.5)
        # Edge case: reasoning_models contains empty-string entry which must NOT match all models
        chat.reasoning_models = ['']

        captured = {}

        async def create_stub(*args, **kwargs):
            # Capture kwargs forwarded by ainvoke to the provider
            captured.update(kwargs)
            # Only encode the keys we care about to keep the returned content deterministic
            body = {
                'temperature': kwargs.get('temperature'),
                'frequency_penalty': kwargs.get('frequency_penalty'),
            }
            choice = SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(body)),
                finish_reason='completed',
            )
            return SimpleNamespace(choices=[choice])

        # Build a dummy client with completions.create stub
        completions = SimpleNamespace(create=create_stub)
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

        # Monkeypatch instance methods to avoid network and nondeterminism
        chat.get_client = lambda: client
        chat._get_usage = lambda response: None

        # Invoke the async entrypoint deterministically
        result = asyncio.run(chat.ainvoke(messages=[], output_format=None))

        # Parse the provider-encoded completion to observe forwarded kwargs
        forwarded = json.loads(result.completion)

        # Primary assertions: explicit numeric hyperparameters must be forwarded unchanged
        assert forwarded.get('temperature') == chat.temperature, (
            "temperature was not forwarded to provider call; reasoning_models=[''] should not match all models"
        )
        assert forwarded.get('frequency_penalty') == chat.frequency_penalty, (
            "frequency_penalty was not forwarded to provider call; reasoning_models=[''] should not match all models"
        )

    finally:
        # Restore original serializer to avoid side effects
        OpenAIMessageSerializer.serialize_messages = orig_serialize
