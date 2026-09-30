import pytest
import asyncio
from types import SimpleNamespace

import pr_agent.tools.ticket_pr_compliance_check as tpc


class FakeIssue:
    def __init__(self, number, title, body, labels):
        self.number = number
        self.title = title
        self.body = body
        self.labels = labels


class FakeLabel:
    def __init__(self, name):
        self.name = name


class FakeGithubProvider:
    def __init__(self):
        self.repo = "org/repo"
        self.base_url_html = "https://example.com"
        # simple in-memory mapping of issue_number -> Issue
        self._issues = {}
        self.repo_obj = SimpleNamespace(get_issue=self._get_issue)

    def get_user_description(self):
        # not used because we patch extractor functions in tests, but keep for completeness
        return ""

    def get_pr_branch(self):
        return "feature/branch"

    def _parse_issue_url(self, url):
        # Expect URLs that end with a number
        if not isinstance(url, str) or not url.rstrip().split("/")[-1].isdigit():
            raise ValueError("bad url")
        return (self.repo, int(url.rstrip().split("/")[-1]))

    def _get_issue(self, number):
        if number not in self._issues:
            raise Exception("not found")
        return self._issues[number]

    def fetch_sub_issues(self, ticket_url):
        # Return different lists depending on ticket id for testing
        if ticket_url.endswith("/1"):
            # Good subissue and a bad url to trigger inner exception path
            return [f"https://github.com/{self.repo}/issues/10", "not-a-url"]
        return []


class FakeAzureProvider:
    def __init__(self, tickets):
        self._tickets = tickets

    def get_linked_work_items(self):
        return list(self._tickets)


@pytest.mark.asyncio
async def test_extract_tickets_github_round_015(monkeypatch):
    # Patch the type symbol used in isinstance checks to our fake class
    monkeypatch.setattr(tpc, "GithubProvider", FakeGithubProvider)

    provider = FakeGithubProvider()

    # Prepare issues in repo_obj
    # Issue 1 has labels as mix of FakeLabel and raw string
    long_sub_body = "x" * 10005  # longer than MAX_TICKET_CHARACTERS to trigger truncation
    provider._issues[1] = FakeIssue(1, "Issue One", "body one", [FakeLabel("bug"), "legacy-label"])
    provider._issues[2] = FakeIssue(2, "Issue Two", "body two", [])
    provider._issues[3] = FakeIssue(3, "Issue Three", "body three", [FakeLabel("enhancement")])
    provider._issues[10] = FakeIssue(10, "Sub Issue Ten", long_sub_body, [])

    # Force the description and branch extraction functions to return specific lists
    monkeypatch.setattr(
        tpc,
        "extract_ticket_links_from_pr_description",
        lambda desc, repo, base: [f"https://github.com/{provider.repo}/issues/1", f"https://github.com/{provider.repo}/issues/2"],
    )
    monkeypatch.setattr(
        tpc,
        "extract_ticket_links_from_branch_name",
        lambda branch, repo, base: [f"https://github.com/{provider.repo}/issues/2", f"https://github.com/{provider.repo}/issues/3", f"https://github.com/{provider.repo}/issues/4"],
    )

    # Now call the async function
    result = await tpc.extract_tickets(provider)

    # Because merged unique tickets will be [1,2,3,4] and code limits to first 3 when >3
    assert isinstance(result, list) and len(result) == 3

    # Validate first returned ticket corresponds to issue 1 and has expected structure
    first = result[0]
    assert first["ticket_id"] == 1
    assert first["ticket_url"].endswith("/1")
    assert first["title"] == "Issue One"
    # body preserved (short)
    assert first["body"] == "body one"
    # labels joined: FakeLabel('bug') and 'legacy-label' -> 'bug, legacy-label'
    assert first["labels"] in ("bug, legacy-label", "legacy-label, bug")  # order depending on iteration
    # sub_issues should include the parsed good sub-issue with truncated body
    assert isinstance(first["sub_issues"], list)
    # Find sub issue url 10
    sub_urls = [s["ticket_url"] for s in first["sub_issues"]]
    assert any(url.endswith("/10") for url in sub_urls)
    # The sub-issue body should have been truncated to end with "..."
    sub_item = next(s for s in first["sub_issues"] if s["ticket_url"].endswith("/10"))
    assert sub_item["body"].endswith("...")
    # Ensure ticket 4 that does not exist in provider._issues was skipped (so not present in result list)
    ids = [r["ticket_id"] for r in result]
    assert 4 not in ids


@pytest.mark.asyncio
async def test_extract_tickets_azure_round_015(monkeypatch):
    # Patch AzureDevopsProvider symbol
    monkeypatch.setattr(tpc, "AzureDevopsProvider", FakeAzureProvider)

    # Create a ticket with a very long body to test truncation
    long_body = "A" * 10050
    ticket = {
        "id": 42,
        "url": "https://dev.azure.com/org/_workitems/42",
        "title": "Azure Ticket",
        "body": long_body,
        "acceptance_criteria": "OK",
        "labels": ["area:infra", "priority:high"],
    }

    provider = FakeAzureProvider([ticket])

    result = await tpc.extract_tickets(provider)

    # Azure path should return a list with one ticket
    assert isinstance(result, list) and len(result) == 1
    out = result[0]
    # ticket_id and url preserved
    assert out["ticket_id"] == 42
    assert out["ticket_url"] == "https://dev.azure.com/org/_workitems/42"
    # title preserved
    assert out["title"] == "Azure Ticket"
    # body should be truncated to 10000 + '...'
    assert out["body"].endswith("...")
    assert len(out["body"]) == 10003
    # requirements and labels fields present
    assert out["requirements"] == "OK"
    assert "area:infra" in out["labels"] and "priority:high" in out["labels"]
