from openhands.sdk.extensions.fetch import parse_extension_source


def test_probe_001():
    """Probe: ensure a github: shorthand that already includes '.git' canonicalizes to a single '.git' suffix.

    This exercises the github: branch of parse_extension_source with an input that could trigger '.git' duplication
    if the implementation appends '.git' unconditionally.
    """
    source = "github:owner/repo.git"

    result = parse_extension_source(source)

    # Basic structural expectations: a 2-tuple (source_type, url)
    assert isinstance(result, tuple) and len(result) == 2

    url = result[1]

    # Primary oracle: exact canonical URL (one .git) and explicitly not ending with '.git.git'
    assert url == "https://github.com/owner/repo.git"
    assert not url.endswith(".git.git")
