from gpt_researcher.skills.deep_research import parse_search_queries_response


def test_parse_search_queries_response_rejects_whitespace_only_fields():
    """Probe: inputs with whitespace-only fields must not produce returned entries with empty trimmed fields.

    The implementation uses truthiness checks on raw JSON values but .strip() when constructing returns; a whitespace-only value can be truthy yet strip to empty. This test asserts the independent invariant that every returned entry has non-empty 'query' and 'researchGoal' after trimming.
    """
    cases = [
        # query is whitespace-only -> should be excluded
        '[{"query": "   ", "researchGoal": "g1"}]',
        # researchGoal is whitespace-only -> should be excluded
        '[{"query": "q1", "researchGoal": "   "}]',
        # both whitespace-only -> should be excluded
        '[{"query": "   ", "researchGoal": "   "}]',
        # control: valid entry -> may be returned
        '[{"query": "q_ok", "researchGoal": "g_ok"}]',
    ]

    num_queries = 3
    all_entries = []

    for resp in cases:
        result = parse_search_queries_response(resp, num_queries=num_queries)
        # collect returned entries from each invocation
        all_entries.extend(result)

    # Primary behavioral oracle: no returned entry has empty trimmed 'query' or 'researchGoal'
    assert all(
        entry.get("query", "").strip() != "" and entry.get("researchGoal", "").strip() != ""
        for entry in all_entries
    ), f"parse_search_queries_response returned entry with empty trimmed field(s): {all_entries}"
