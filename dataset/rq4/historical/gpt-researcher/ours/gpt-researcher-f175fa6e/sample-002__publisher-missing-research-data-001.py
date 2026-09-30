import pytest

from multi_agents.agents.publisher import PublisherAgent


def _make_agent():
    # deterministic construction using a harmless output_dir string
    return PublisherAgent(output_dir=".")


def test_probe_001():
    """Probe: calling generate_layout with no top-level 'research_data' must not raise and must render an empty sections area.

    Activation: provide headers mapping and scalar fields; omit 'research_data'.
    Primary oracle: the substring between the table_of_contents content and the conclusion header is empty (only whitespace).
    """
    headers = {
        "title": "Test Title",
        "date": "2026-01-01",
        "introduction": "Introduction Header",
        "table_of_contents": "Table of Contents Header",
        "conclusion": "Conclusion Header",
        "references": "References Header"
    }

    research_state = {
        "headers": headers,
        # scalar display values
        "date": "2026-01-01",
        "introduction": "Intro body content",
        # use a distinct TOC body to locate region reliably
        "table_of_contents": "UNIQUE_TOC_BODY_42",
        "conclusion": "Conclusion body content",
        # include sources so references rendering path is exercised
        "sources": ["ref-A", "ref-B"]
        # NOTE: intentionally omit 'research_data' to exercise the boundary condition
    }

    agent = _make_agent()

    # Call the public entrypoint under test
    layout = agent.generate_layout(research_state)

    # Basic observable checks
    assert isinstance(layout, str), "generate_layout must return a string, not raise or return None"
    assert f"# {headers['title']}" in layout, "Title header must be present in the layout"
    assert f"## {headers['references']}" in layout, "References header must be present in the layout"

    # Locate the region between the table_of_contents body and the conclusion header
    toc_body = research_state["table_of_contents"]
    concl_header = f"## {headers['conclusion']}"

    idx_toc = layout.find(toc_body)
    assert idx_toc != -1, "Table of contents body must appear in the rendered layout"
    start_after_toc = idx_toc + len(toc_body)

    idx_concl = layout.find(concl_header, start_after_toc)
    assert idx_concl != -1, "Conclusion header must appear after the table of contents in the layout"

    middle_region = layout[start_after_toc:idx_concl]

    # PRIMARY ORACLE: section area must be empty (only whitespace/newlines) when 'research_data' is absent
    assert middle_region.strip() == "", (
        "Expected an empty sections area when 'research_data' is missing, but found content: {!r}".format(middle_region)
    )
