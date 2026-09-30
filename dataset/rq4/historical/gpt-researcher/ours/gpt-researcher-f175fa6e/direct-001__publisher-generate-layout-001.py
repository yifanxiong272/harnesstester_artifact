def test_probe_001():
    # Import the public entrypoint class
    from multi_agents.agents.publisher import PublisherAgent

    # Deterministic headers and other fields; intentionally omit 'sources'
    headers = {
        'title': 'Test Title',
        'date': '2026-01-01',
        'introduction': 'Introduction Header',
        'table_of_contents': 'Table of Contents',
        'conclusion': 'Conclusion Header',
        'references': 'References'
    }

    research_state = {
        'headers': headers,
        # non-empty research_data to exercise sections assembly
        'research_data': [
            {'section_a': 'Content A'},
            {'section_b': 'Content B'}
        ],
        # other optional text fields referenced by generate_layout
        'date': '2026-01-01',
        'introduction': 'Intro text',
        'table_of_contents': '1. A\n2. B',
        'conclusion': 'Conclusion text'
        # Note: 'sources' is intentionally omitted to trigger the edge case
    }

    # Create an instance without invoking __init__ in case constructor requires args
    agent = object.__new__(PublisherAgent)

    # Call the target entrypoint. The intended invariant is that this does not raise
    # and that the references section header is rendered with an empty body.
    layout = agent.generate_layout(research_state)

    # Locate the references header and assert the following body is empty (only whitespace)
    header_line = f"## {headers['references']}\n"
    idx = layout.find(header_line)
    assert idx != -1, f"References header {header_line!r} not found in generated layout: {layout!r}"

    after = layout[idx + len(header_line):]
    # The expected behavior: no non-whitespace characters after the header when 'sources' is absent
    assert after.strip() == "", (
        "Expected empty references body when 'sources' is missing, but found:"
        f" {after!r}"
    )
