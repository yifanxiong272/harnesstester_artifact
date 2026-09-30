import pytest
from types import SimpleNamespace

import rdagent.oai.backend.deprec as deprec

# Grab the unbound function object so we can call it with a fake `self`
_calc = getattr(deprec.DeprecBackend, "_calculate_token_from_messages")


class FakeEncoder:
    """Deterministic fake encoder: encode(value) -> list of characters of str(value)

    This makes len(encode(value)) == len(str(value)) and is fully deterministic.
    """

    def encode(self, value):
        return list(str(value))


def test_chat_use_azure_deepseek_round_094():
    fake_self = SimpleNamespace(
        chat_use_azure_deepseek=True,
        encoder=None,
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_model="",
    )

    # When azure deepseek is enabled the function should short-circuit to 0
    assert _calc(fake_self, []) == 0


def test_encoder_none_raises_round_094():
    fake_self = SimpleNamespace(
        chat_use_azure_deepseek=False,
        encoder=None,  # should trigger ValueError
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_model="",
    )

    with pytest.raises(ValueError):
        _calc(fake_self, [])


def test_use_llama2_returns_zero_round_094(monkeypatch):
    # Ensure logger.warning doesn't produce noisy output during the test
    monkeypatch.setattr(deprec, "logger", SimpleNamespace(warning=lambda *a, **k: None))

    fake_self = SimpleNamespace(
        chat_use_azure_deepseek=False,
        encoder=FakeEncoder(),
        use_llama2=True,  # should trigger warning + return 0
        use_gcr_endpoint=False,
        chat_model="something",
    )

    assert _calc(fake_self, [{"role": "user", "content": "hi"}]) == 0


def test_counts_gpt4_with_name_round_094():
    # Use chat_model containing 'gpt-4' to take the gpt4 branch (tokens_per_message=3, tokens_per_name=1)
    fake_self = SimpleNamespace(
        chat_use_azure_deepseek=False,
        encoder=FakeEncoder(),
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_model="gpt-4-x",
    )

    messages = [
        {"role": "user", "content": "hello"},
        {"name": "alice", "content": "x"},
    ]

    # Manually compute expected token count with our FakeEncoder:
    # For first message: tokens_per_message=3 + len('user') + len('hello') = 3 + 4 + 5 = 12
    # For second message: tokens_per_message=3 + len('alice') + len('x') + tokens_per_name(1) = 3 + 5 + 1 + 1 = 10
    # Sum = 12 + 10 = 22; plus 3 final priming tokens = 25
    expected = 25
    assert _calc(fake_self, messages) == expected


def test_counts_non_gpt4_with_name_round_094():
    # Use a non-gpt4 model (tokens_per_message=4, tokens_per_name=-1)
    fake_self = SimpleNamespace(
        chat_use_azure_deepseek=False,
        encoder=FakeEncoder(),
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_model="gpt-3.5-turbo",
    )

    messages = [
        {"role": "user", "content": "hello"},
        {"name": "alice", "content": "x"},
    ]

    # Manually compute expected token count:
    # First message: 4 + len('user') + len('hello') = 4 + 4 + 5 = 13
    # Second message: 4 + len('alice') + len('x') + tokens_per_name(-1) = 4 + 5 + 1 -1 = 9
    # Sum = 13 + 9 = 22; plus 3 final priming tokens = 25
    expected = 25
    assert _calc(fake_self, messages) == expected
