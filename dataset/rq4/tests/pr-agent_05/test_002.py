def test_probe_001():
    from pr_agent.algo.utils import load_yaml

    # Uppercase fenced YAML opening tag to test case-insensitive fence stripping
    input_text = "```YAML\nkey: value\n```"
    expected = {"key": "value"}

    # Primary behavioral oracle: load_yaml should parse the inner YAML despite uppercase fence tag
    assert load_yaml(input_text) == expected
