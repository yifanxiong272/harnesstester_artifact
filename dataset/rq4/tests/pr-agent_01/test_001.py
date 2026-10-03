from pr_agent.algo.utils import ticket_markdown_logic


def test_probe_001():
    # Construct the ticket that only requests further human verification
    ticket = {
        "ticket_url": "https://example.com/ISSUE-123",
        "fully_compliant_requirements": "   ",  # whitespace-only
        "not_compliant_requirements": "",
        "requires_further_human_verification": "Please confirm security implications."
    }

    # Call the public entrypoint under test
    output = ticket_markdown_logic("🔍", "", [ticket], gfm_supported=False)

    # Observable pieces we expect to see if the function preserves verification requests
    ticket_id = ticket["ticket_url"].split("/")[-1]
    expected_phrase = "Requires further human verification"
    expected_text = ticket["requires_further_human_verification"]

    # Primary oracle: all three substrings must be present in the returned markdown
    assert (ticket_id in output) and (expected_phrase in output) and (expected_text in output), (
        f"Expected verification note for ticket {ticket_id} not found in output.\nOutput:\n{output!r}"
    )
