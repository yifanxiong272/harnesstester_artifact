import yaml
from pr_agent.algo.utils import load_yaml


def test_probe_001():
    """Probe: ensure load_yaml strips a fenced YAML block even when the fence language tag is uppercase (e.g. '```YAML').

    Invariant: yaml.safe_load applied to the inner YAML (the text between the opening and closing fences) is the authoritative result; load_yaml must return the same object.
    """

    def _inner_from_fenced(s: str) -> str:
        # Deterministically extract the inner content between the first opening fence line
        # and the last closing fence line. Do not rely on external behavior.
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            # Find the last line that looks like a closing fence
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].startswith("```"):
                    return "\n".join(lines[1:i])
        # If not fenced as expected, return the original string so the oracle still applies deterministically
        return s

    fenced = "```YAML\na: 1\n```"
    inner = _inner_from_fenced(fenced)

    # Independent authoritative parse of the inner YAML fragment
    expected = yaml.safe_load(inner)

    # Exercise the single public entrypoint under test
    actual = load_yaml(fenced)

    # Primary assertion: load_yaml must return the same structure as yaml.safe_load on the inner content
    assert actual == expected, (
        f"Case-insensitive fence handling failed: expected={expected!r}, actual={actual!r}, input={fenced!r}"
    )
