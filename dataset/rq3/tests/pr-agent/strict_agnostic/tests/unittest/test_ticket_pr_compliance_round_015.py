import asyncio

import pr_agent.tools.ticket_pr_compliance_check as tmod
from pr_agent.git_providers import GithubProvider, AzureDevopsProvider


class FakeIssue:
    def __init__(self, number, title="t", body="", labels=None):
        self.number = number
        self.title = title
        self.body = body
        self.labels = labels or []


class FakeRepoObj:
    def __init__(self, issues_map):
        # issues_map: number -> FakeIssue or Exception
        self._issues = issues_map

    def get_issue(self, number):
        val = self._issues.get(number)
        if isinstance(val, Exception):
            raise val
        return val


class DummyGithub(GithubProvider):
    def __init__(self, repo_obj_map=None, sub_issues_map=None):
        # do not call super to avoid any external side-effects
        self.repo = "owner/repo"
        self.base_url_html = "https://example.com"
        self.repo_obj = FakeRepoObj(repo_obj_map or {})
        # map ticket_url -> list of sub-ticket urls
        self._sub_issues_map = sub_issues_map or {}

    def get_user_description(self):
        return "pr description"

    def get_pr_branch(self):
        return "branch-name"

    def _parse_issue_url(self, url):
        # parse trailing numeric id
        try:
            issue_number = int(str(url).rstrip("/\n").split("/")[-1])
        except Exception:
            issue_number = 0
        return (self.repo, issue_number)

    def fetch_sub_issues(self, ticket_url):
        return self._sub_issues_map.get(ticket_url, [])


class DummyAzure(AzureDevopsProvider):
    def __init__(self, items):
        self._items = items

    def get_linked_work_items(self):
        return list(self._items)


def test_github_overflow_and_subissues_round_015():
    """
    - Force more than 3 merged tickets from description to exercise the "Too many tickets" branch and slicing.
    - Include one ticket whose repo_obj.get_issue raises to exercise the exception/continue branch.
    - Ensure the returned list is truncated to 3 and contains processed tickets.
    """
    # Prepare a description that extracts to 4 tickets
    ticket_urls = [
        "http://fake/issue/101",
        "http://fake/issue/102",
        "http://fake/issue/103",
        "http://fake/issue/104",
    ]

    # Prepare issues mapping: 102 will raise to hit the exception branch; others are valid
    issues_map = {
        101: FakeIssue(101, title="one", body="body101", labels=[type("L", (), {"name": "bug"})()]),
        102: Exception("boom fetching 102"),
        103: FakeIssue(103, title="three", body="body103", labels=["rawlabel"]),
        104: FakeIssue(104, title="four", body="body104", labels=[]),
    }

    provider = DummyGithub(repo_obj_map=issues_map, sub_issues_map={})

    # Monkeypatch the description/branch extractors to return our ticket urls and no branch tickets
    tmod.extract_ticket_links_from_pr_description = lambda desc, repo, base: list(ticket_urls)
    tmod.extract_ticket_links_from_branch_name = lambda branch, repo, base: []

    result = asyncio.run(tmod.extract_tickets(provider))

    # Should be truncated to at most 3 tickets (first 3 merged unique ones). Some of those may fail during fetch and be skipped.
    assert isinstance(result, list)
    assert len(result) <= 3

    # ticket_id should be the issue.number from the FakeIssue for succeeded fetches; 102 should be skipped
    returned_ids = [r["ticket_id"] for r in result]
    # 101 and 103 should be present (102 raises); 104 is not among the first three links so should not be present
    assert 101 in returned_ids
    assert 103 in returned_ids
    assert 104 not in returned_ids

    # Labels: for 101 we used an object with .name attribute, so it should be represented as a string
    found_101 = next((r for r in result if r["ticket_id"] == 101), None)
    assert found_101 is not None
    assert "bug" in found_101["labels"]


def test_github_labels_iteration_error_round_015():
    """
    - Exercise labels extraction error branch by providing an object that raises when iterated.
    - Expect labels string to be empty and function to return the ticket info.
    """
    class BadLabels:
        def __iter__(self):
            raise RuntimeError("cannot iterate labels")

    issues_map = {
        201: FakeIssue(201, title="badlabels", body="b", labels=BadLabels()),
    }
    provider = DummyGithub(repo_obj_map=issues_map)

    tmod.extract_ticket_links_from_pr_description = lambda desc, repo, base: ["http://fake/issue/201"]
    tmod.extract_ticket_links_from_branch_name = lambda branch, repo, base: []

    result = asyncio.run(tmod.extract_tickets(provider))

    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    # labels extraction failed, so labels should be empty string
    assert item["labels"] == ""
    assert item["ticket_id"] == 201


def test_azure_devops_truncation_round_015():
    """
    - Ensure Azure DevOps ticket body truncation and label joining logic is exercised.
    """
    long_body = "x" * 10050  # > MAX_TICKET_CHARACTERS (10000)
    items = [
        {
            "id": 500,
            "url": "https://ado/500",
            "title": "big",
            "body": long_body,
            "acceptance_criteria": "criteria",
            "labels": ["one", "two"],
        }
    ]

    provider = DummyAzure(items)

    result = asyncio.run(tmod.extract_tickets(provider))

    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    # body should be truncated to MAX_TICKET_CHARACTERS + '...'
    assert item["body"].endswith("...")
    assert len(item["body"]) == 10003
    assert item["labels"] == "one, two"
    assert item["ticket_id"] == 500
