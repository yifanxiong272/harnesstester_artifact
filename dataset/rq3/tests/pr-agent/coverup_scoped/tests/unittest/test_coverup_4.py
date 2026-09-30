# file: pr_agent/tools/ticket_pr_compliance_check.py:108-221
# asked: {"lines": [112, 113, 114, 116, 117, 118, 120, 121, 122, 123, 124, 125, 126, 127, 128, 130, 131, 133, 135, 136, 138, 139, 140, 141, 142, 143, 145, 146, 147, 150, 151, 152, 153, 154, 155, 156, 158, 159, 160, 162, 163, 164, 165, 167, 168, 170, 171, 174, 175, 176, 177, 178, 179, 180, 182, 183, 184, 185, 186, 187, 188, 191, 194, 195, 196, 197, 198, 199, 200, 202, 203, 204, 205, 206, 207, 208, 209, 212, 213, 214, 215, 217, 219, 220, 221], "branches": [[111, 112], [122, 123], [122, 126], [123, 122], [123, 124], [126, 127], [126, 130], [133, 0], [133, 135], [135, 136], [135, 191], [146, 147], [146, 150], [153, 154], [153, 174], [159, 160], [159, 162], [176, 177], [176, 182], [193, 194], [196, 197], [196, 217], [199, 200], [199, 202]]}
# gained: {"lines": [112, 113, 114, 116, 117, 118, 120, 121, 122, 123, 124, 125, 126, 127, 128, 131, 133, 135, 136, 138, 139, 140, 141, 142, 143, 145, 146, 147, 150, 151, 152, 153, 154, 155, 156, 158, 159, 162, 163, 164, 165, 170, 171, 174, 175, 176, 177, 178, 179, 180, 182, 183, 184, 185, 186, 187, 188, 191, 194, 195, 196, 197, 198, 199, 200, 202, 203, 204, 205, 206, 207, 208, 209, 212, 213, 214, 215, 217, 219, 220, 221], "branches": [[111, 112], [122, 123], [122, 126], [123, 124], [126, 127], [133, 135], [135, 136], [135, 191], [146, 147], [146, 150], [153, 154], [153, 174], [159, 162], [176, 177], [176, 182], [193, 194], [196, 197], [196, 217], [199, 200]]}

import asyncio
import types
import pytest

import pr_agent.tools.ticket_pr_compliance_check as tpc


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.warnings = []

    def info(self, msg, *args, **kwargs):
        self.infos.append((msg, args, kwargs))

    def error(self, msg, *args, **kwargs):
        self.errors.append((msg, args, kwargs))

    def warning(self, msg, *args, **kwargs):
        self.warnings.append((msg, args, kwargs))


@pytest.mark.asyncio
async def test_extract_tickets_github_various_branches(monkeypatch):
    """
    Exercises:
    - dedup and trimming when >3 tickets (info log)
    - skipping ticket when repo_obj.get_issue raises (error log)
    - truncation of issue body when > MAX_TICKET_CHARACTERS
    - fetching sub-issues success for one, fetch_sub_issues raising for another (warning)
    - labels extraction raising an exception (error)
    - overall returned tickets_content fields correctness
    """

    logger = DummyLogger()
    monkeypatch.setattr(tpc, "get_logger", lambda: logger)

    # Patch the ticket extraction helpers to return specific links
    monkeypatch.setattr(tpc, "extract_ticket_links_from_pr_description", lambda desc, repo, base: [
        "http://fake/1",
        "http://fake/2",
    ])
    monkeypatch.setattr(tpc, "extract_ticket_links_from_branch_name", lambda branch, repo, base: [
        "http://fake/3",
        "http://fake/4",
    ])

    # Build a fake GithubProvider type for isinstance checks
    class FakeGithubProvider:
        repo = "org/repo"
        base_url_html = "http://base"
        repo_obj = None

        def get_user_description(self):
            return "some description"

        def get_pr_branch(self):
            return "feature/branch"

        def _parse_issue_url(self, url):
            # url like http://fake/<num>
            return ("org/repo", int(url.rsplit("/", 1)[-1]))

        def fetch_sub_issues(self, ticket):
            # For ticket 2 return a sub issue, for 3 raise
            if ticket.endswith("/2"):
                return ["http://fake/5"]
            if ticket.endswith("/3"):
                raise Exception("failed fetch subs")
            return []

    provider = FakeGithubProvider()

    # Create fake issue objects and repo_obj.get_issue behavior
    class FakeIssue:
        def __init__(self, number, title, body, labels):
            self.number = number
            self.title = title
            self.body = body
            self.labels = labels

    # labels that raise when iterated for issue 3
    class BadLabels:
        def __iter__(self):
            raise Exception("labels broken")

    # Normal label objects with .name
    class LabelObj:
        def __init__(self, name):
            self.name = name

    def get_issue(num):
        if num == 1:
            raise Exception("no such issue")  # should trigger error and continue
        if num == 2:
            # long body to force truncation (> MAX_TICKET_CHARACTERS 10000)
            return FakeIssue(2, "Issue Two", "x" * 10001, [LabelObj("bug"), LabelObj("urgent")])
        if num == 3:
            # will trigger fetch_sub_issues raising, and labels iteration raising
            return FakeIssue(3, "Issue Three", "short body", BadLabels())
        if num == 5:
            return FakeIssue(5, "Sub Issue", "sub body", [])

        raise Exception("unexpected")

    provider.repo_obj = types.SimpleNamespace(get_issue=get_issue)

    # Ensure isinstance check in function treats our class as GithubProvider
    monkeypatch.setattr(tpc, "GithubProvider", FakeGithubProvider)

    result = await tpc.extract_tickets(provider)

    # After dedupe and trimming, tickets are first 3 ([1,2,3]). Issue 1 raises -> skipped.
    # So we expect items for issue 2 and 3 only.
    assert isinstance(result, list)
    assert len(result) == 2

    # Find ticket entries by id
    ids = {item["ticket_id"] for item in result}
    assert ids == {2, 3}

    # Verify truncation happened for issue 2
    item2 = next(item for item in result if item["ticket_id"] == 2)
    assert item2["title"] == "Issue Two"
    assert item2["ticket_url"].endswith("/2")
    assert item2["body"].endswith("...")  # truncated
    # Labels were normal for issue 2
    assert "bug" in item2["labels"]
    assert "urgent" in item2["labels"]

    # Issue 3 had labels iteration raising; labels should be empty string
    item3 = next(item for item in result if item["ticket_id"] == 3)
    assert item3["title"] == "Issue Three"
    assert item3["body"] == "short body"
    assert item3["labels"] == ""

    # Sub-issues: for issue 2 we returned one sub issue
    assert any(si["ticket_url"].endswith("/5") for si in item2["sub_issues"])
    # For issue 3, fetch_sub_issues raised; sub_issues should be empty list
    assert item3["sub_issues"] == []

    # Check logger captured info for too many tickets and error for issue 1 and label extraction error and warning for sub fetch
    assert any("Too many tickets" in msg for msg, *_ in logger.infos)
    # error for getting main issue 1
    assert any("Error getting main issue" in msg for msg, *_ in logger.errors)
    # error extracting labels should be present
    assert any("Error extracting labels" in msg for msg, *_ in logger.errors)
    # warning for failed to fetch sub-issues for ticket 3
    assert any("Failed to fetch sub-issues" in msg for msg, *_ in logger.warnings)


@pytest.mark.asyncio
async def test_extract_tickets_azuredevops_and_error_branch(monkeypatch):
    """
    Exercises:
    - AzureDevopsProvider branch: normal processing and truncation of body > MAX
    - handling of an Azure ticket object that raises inside .get to trigger the inner except
    - outer try/except branch when get_user_description raises (to hit lines 219-221)
    """

    logger = DummyLogger()
    monkeypatch.setattr(tpc, "get_logger", lambda: logger)

    # First: Azure path
    class FakeAzureProvider:
        pass

    provider_azure = FakeAzureProvider()

    long_body = "y" * 10001

    # Good ticket dict should be processed and truncated
    good_ticket = {
        "id": "AZ1",
        "url": "http://az/1",
        "title": "AZ Title",
        "body": long_body,
        "acceptance_criteria": "must do",
        "labels": ["alpha", "beta"],
    }

    # Bad ticket object where get raises
    class BadTicket:
        def get(self, key, default=None):
            raise Exception("bad ticket access")

    # Attach get_linked_work_items to provider
    provider_azure.get_linked_work_items = lambda: [good_ticket, BadTicket()]

    # Ensure isinstance check maps to AzureDevopsProvider
    monkeypatch.setattr(tpc, "AzureDevopsProvider", FakeAzureProvider)

    result = await tpc.extract_tickets(provider_azure)

    # Only the good ticket should be in result (bad one triggers logged error)
    assert isinstance(result, list)
    assert len(result) == 1
    r = result[0]
    assert r["ticket_id"] == "AZ1"
    assert r["ticket_url"] == "http://az/1"
    assert r["title"] == "AZ Title"
    assert r["body"].endswith("...")  # truncated
    assert r["requirements"] == "must do"
    assert r["labels"] == "alpha, beta"

    # Ensure logger captured an error for the bad ticket
    assert any("Error processing Azure DevOps ticket" in msg for msg, *_ in logger.errors)

    # Now: trigger outer exception branch (lines ~219-221)
    # Make a fake GithubProvider class in module so isinstance sees it, and its get_user_description raises
    class BadGithubForOuter:
        def get_user_description(self):
            raise Exception("outer boom")

    monkeypatch.setattr(tpc, "GithubProvider", BadGithubForOuter)

    bad_provider = BadGithubForOuter()
    # Running should not raise; should be caught and logged, returning None
    res = await tpc.extract_tickets(bad_provider)
    assert res is None
    assert any("Error extracting tickets error=" in msg for msg, *_ in logger.errors)
