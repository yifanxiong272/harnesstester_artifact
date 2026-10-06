def test_probe_001():
    from browser_use.llm.anthropic.serializer import AnthropicMessageSerializer

    # Uppercase media type per the probe activation condition
    url = 'data:IMAGE/PNG;base64,Zm9v'

    # Exercise the target static method reachable via the public class symbol
    media_type, data = AnthropicMessageSerializer._parse_base64_url(url)

    # Independent semantic invariant: MIME type tokens are case-insensitive.
    # Expect normalization/recognition to the supported lowercase form.
    assert (media_type, data) == ('image/png', 'Zm9v')
