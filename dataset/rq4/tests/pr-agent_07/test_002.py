def test_probe_001():
    """
    Probe the try_fix_yaml fallback that extracts a substring between first_key and last_key.

    Independent invariant: when a valid YAML snippet is correctly extracted and parsed, the parsed mapping must include the original top-level key (first_key).

    This test builds a deterministic response_text that contains a deliberately malformed YAML-like preface (to make earlier fallbacks fail) and then a contiguous valid YAML snippet whose first top-level key is 'analysis' (which starts with 'a' — a character present in the buggy .strip('```yaml') character set). The snippet is followed by a blank line so the function's index_end selection is exercised.
    """
    from pr_agent.algo.utils import try_fix_yaml

    # Use a preface known to cause yaml.safe_load to raise (copied form known test fixture) so earlier fallbacks fail.
    invalid_preface = (
        "PR Analysis:\n"
        "  Main theme: Enhancing the `/describe` command prompt by adding title and description\n"
        "  Type of PR: Enhancement\n"
        "  Relevant tests: No\n"
        "  Focused PR: Yes, the PR is focused on enhancing the `/describe` command prompt.\n\n"
        "PR Feedback:\n"
        "  General suggestions: The PR seems to be well-structured and focused on a specific enhancement. However, it would be beneficial to add tests to ensure the new feature works as expected.\n"
        "  Code feedback:\n"
        "    - relevant file: pr_agent/settings/pr_description_prompts.toml\n"
        "      suggestion: Consider using a more descriptive variable name than 'user' for the command prompt. A more descriptive name would make the code more readable and maintainable. [medium]\n"
        "      relevant line: user=\"\"\"PR Info: aaa\n\n"
    )

    # The YAML snippet to be extracted — starts with 'analysis' (first_key) and contains last_key 'lastkey'.
    # The snippet is followed by a blank line to exercise the index_end selection.
    snippet = (
        "analysis:\n"
        "  summary: 'preserve-me'\n"
        "lastkey:\n"
        "  note: 'end'\n"
        "\n"
    )

    response_text = invalid_preface + "\n" + snippet + "Trailing text that should not be parsed."

    first_key = "analysis"
    last_key = "lastkey"

    result = try_fix_yaml(response_text, first_key=first_key, last_key=last_key)

    # Primary oracle: the parsed result must be a mapping and must contain the original top-level first_key.
    assert isinstance(result, dict), f"try_fix_yaml must return a mapping when a YAML snippet is extractable; got {type(result)!r} with value: {result!r}"
    assert first_key in result, (
        f"Parsed mapping is missing the top-level key {first_key!r}. Keys found: {list(result.keys())}. "
        "This reveals that extracting the substring between first_key and last_key corrupted the boundary or key names."
    )
