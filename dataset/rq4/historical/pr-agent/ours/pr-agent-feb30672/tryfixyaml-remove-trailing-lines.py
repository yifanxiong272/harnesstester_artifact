def test_probe_001():
    # Exercise the public entrypoint try_fix_yaml with trailing invalid lines
    from pr_agent.algo.utils import try_fix_yaml

    # Leading valid YAML mapping followed by a single trailing line '[' which will
    # make the full text invalid for yaml.safe_load but the leading lines alone
    # are valid YAML and should be recovered by the 'remove last lines' fallback.
    response_text = "name: John\nage: 35\n[\n"

    expected = {'name': 'John', 'age': 35}

    result = try_fix_yaml(response_text)

    # Primary behavioral oracle: the function should recover and return the mapping
    assert result == expected, f"try_fix_yaml should recover leading YAML mapping, got: {result}"
