import yaml
from pr_agent.algo.utils import load_yaml

def _inner_yaml_text():
    # Minimal valid YAML mapping used for deterministic equivalence check
    return "key: val"

def test_probe_001():
    """Invariant: load_yaml should accept common case-insensitive fenced 'yaml' tags.

    This test constructs a fenced code block whose opening fence uses uppercase
    letters for the language tag ("```YAML") and asserts that load_yaml
    returns the same mapping as yaml.safe_load applied to the inner content.
    """
    inner = _inner_yaml_text()
    fenced_input = "```YAML\n" + inner + "\n```"

    expected = yaml.safe_load(inner)

    result = load_yaml(fenced_input)

    # Primary oracle (single decisive assertion): exact parsed-equivalence
    assert result == expected, (
        f"load_yaml should strip a case-insensitive '```yaml' fence and parse the inner YAML.\n"
        f"Input: {fenced_input!r}\nExpected: {expected!r}\nGot: {result!r}"
    )
