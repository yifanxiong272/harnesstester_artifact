def test_probe_001():
    from openhands.sdk.utils.redact import redact_text_secrets

    secret = 'secret_value_12345'

    def run_case(input_text: str, expected_substring: str):
        result = redact_text_secrets(input_text)
        assert expected_substring in result, (
            f"Expected redaction substring {expected_substring!r} not found in result: {result!r}"
        )
        assert secret not in result, f"Original secret leaked in output: {result!r}"

    s1 = "prefix api_key = '{s}' suffix".format(s=secret)
    run_case(s1, "api_key = '<redacted>'")
