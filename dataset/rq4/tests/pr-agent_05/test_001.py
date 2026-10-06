import yaml
from pr_agent.algo.utils import load_yaml


def test_probe_001():
    # inner YAML payload (valid mapping)
    inner = "name: John Smith\nage: 35"
    # Use an upper-case language tag in the fenced code block to exercise case-sensitivity
    fenced = "```YAML\n" + inner + "\n```"

    expected = yaml.safe_load(inner)
    result = load_yaml(fenced)

    # Primary behavioral oracle: load_yaml should behave equivalently to yaml.safe_load on the inner content
    assert result == expected
