import yaml
from pr_agent.algo.utils import load_yaml

def test_probe_001_case_insensitive_fence():
    """
    Oracle: load_yaml should handle an opening fence language tag in uppercase (```YAML) identically
    to yaml.safe_load applied to the inner YAML content.
    """
    inner_yaml = "name: Alice\nage: 30"
    fenced = "```YAML\n" + inner_yaml + "\n```"

    expected = yaml.safe_load(inner_yaml)
    result = load_yaml(fenced)

    # Primary behavioral assertion: parsed equivalence with yaml.safe_load for case-insensitive fence
    assert result == expected, f"load_yaml returned {result!r}, expected {expected!r} for fenced input starting with '```YAML'"
