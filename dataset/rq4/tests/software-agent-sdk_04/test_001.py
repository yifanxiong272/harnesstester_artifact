from openhands.sdk.utils.redact import redact_text_secrets


def test_probe_001():
    text = "{'apiKey': 'secret123', \"apiKey\": \"secret456\", 'other': 'value'}"
    result = redact_text_secrets(text)
    assert 'secret123' not in result
    assert 'secret456' not in result
    assert result.count('<redacted>') >= 2
