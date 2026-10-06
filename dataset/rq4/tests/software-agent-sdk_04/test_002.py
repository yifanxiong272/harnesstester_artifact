from openhands.sdk.utils.redact import redact_text_secrets


def test_probe_001():
    """Probe: case-insensitive dict-key redaction for single- and double-quoted keys.

    Input is a compact Python-style dict fragment containing:
    - 'api_key' (single-quoted, lowercase)
    - "token" (double-quoted, lowercase)
    - 'UserPassword' (single-quoted, mixed-case)
    - 'normal' (non-sensitive control)

    The independent invariant: values whose keys contain key|secret|token|password
    (case-insensitive) must be replaced by the literal '<redacted>'.
    """

    text = "{'api_key': 's3cr3t', \"token\": \"tok-XYZ\", 'UserPassword': 'p@ssw0rd', 'normal': 'keep-me'}"

    result = redact_text_secrets(text)

    # Primary oracle: exact replacements expected for each sensitive dict entry
    assert "'api_key': '<redacted>'" in result, "api_key value was not redacted as expected"
    assert '"token": "<redacted>"' in result, "token value was not redacted as expected"
    assert "'UserPassword': '<redacted>'" in result, "UserPassword value was not redacted as expected"

    # Strong negative assertions: original secret literals must not appear
    assert 's3cr3t' not in result
    assert 'tok-XYZ' not in result
    assert 'p@ssw0rd' not in result

    # Non-sensitive data must be preserved verbatim
    assert "'normal': 'keep-me'" in result
