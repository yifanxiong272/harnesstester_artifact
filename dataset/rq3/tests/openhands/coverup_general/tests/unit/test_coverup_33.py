# file: openhands/integrations/bitbucket/service/repos.py:110-190
# asked: {"lines": [129, 130, 133, 134, 137, 138, 140, 141, 142, 143, 144, 145, 146, 149, 151, 152, 153, 154, 157, 158, 160, 163, 166, 171, 172, 174, 175, 176, 178, 179, 183, 185, 186, 187, 190], "branches": [[129, 130], [129, 133], [138, 140], [138, 141], [141, 142], [141, 143], [143, 144], [143, 145], [145, 146], [145, 149], [157, 158], [157, 160], [172, 174], [172, 185], [175, 176], [175, 183]]}
# gained: {"lines": [129, 130, 133, 134, 137, 138, 140, 141, 142, 143, 144, 145, 146, 149, 151, 152, 153, 154, 157, 158, 160, 163, 166, 171, 172, 174, 175, 176, 178, 179, 183, 185, 186, 187, 190], "branches": [[129, 130], [129, 133], [138, 140], [138, 141], [141, 142], [141, 143], [143, 144], [143, 145], [145, 146], [145, 149], [157, 158], [157, 160], [172, 174], [175, 176], [175, 183]]}

import pytest

from openhands.integrations.bitbucket.service.repos import BitBucketReposMixin


@pytest.mark.asyncio
async def test_get_paginated_repos_no_installation_id():
    class Dummy(BitBucketReposMixin):
        BASE_URL = "https://api.bitbucket.org/2.0"

    inst = Dummy()
    # installation_id is falsy -> should return empty list without calling anything else
    result = await inst.get_paginated_repos(page=1, per_page=10, sort="updated", installation_id=None, query=None)
    assert result == []


@pytest.mark.asyncio
async def test_get_paginated_repos_with_query_and_next_page(monkeypatch):
    class Dummy(BitBucketReposMixin):
        BASE_URL = "https://api.bitbucket.org/2.0"

    inst = Dummy()

    captured = {}

    workspace_slug = "workspace-123"
    expected_url = f"{inst.BASE_URL}/repositories/{workspace_slug}"

    async def fake_make_request(url, params):
        # capture inputs for assertions
        captured['url'] = url
        captured['params'] = params
        # return a response that contains a next link with a page query parameter
        return (
            {"values": [{"slug": "repo1"}], "next": f"{expected_url}?page=5"},
            {"x-some-header": "value"},
        )

    # Track what parse_repository receives and return a transformed result
    parsed_calls = []

    def fake_parse_repository(repo, link_header=""):
        parsed_calls.append((repo, link_header))
        return {"slug": repo["slug"], "link": link_header}

    # Monkeypatch instance methods
    inst._make_request = fake_make_request
    inst._parse_repository = fake_parse_repository

    # Call with a query and sort 'pushed' to exercise that branch (maps to -updated_on)
    result = await inst.get_paginated_repos(
        page=2, per_page=42, sort="pushed", installation_id=workspace_slug, query="searchterm"
    )

    # Assertions for _make_request call
    assert captured["url"] == expected_url
    assert captured["params"]["pagelen"] == 42
    assert captured["params"]["page"] == 2
    assert captured["params"]["sort"] == "-updated_on"
    assert captured["params"]["q"] == 'name~"searchterm"'

    # Ensure parse_repository was called and returned values are propagated
    assert len(parsed_calls) == 1
    repo_arg, link_header_arg = parsed_calls[0]
    assert repo_arg == {"slug": "repo1"}
    assert link_header_arg == f"<{expected_url}?page=5>; rel=\"next\""
    assert result == [{"slug": "repo1", "link": f"<{expected_url}?page=5>; rel=\"next\""}]


@pytest.mark.asyncio
async def test_get_paginated_repos_sorts_and_next_without_page(monkeypatch):
    class Dummy(BitBucketReposMixin):
        BASE_URL = "https://api.bitbucket.org/2.0"

    inst = Dummy()

    # Map input sort -> expected Bitbucket API sort
    sort_expectations = {
        "updated": "-updated_on",
        "created": "-created_on",
        "full_name": "name",
        "unknown_sort": "-updated_on",  # default branch
    }

    # For each sort, ensure params['sort'] is what we expect and handle next link without page param
    for input_sort, expected_sort in sort_expectations.items():

        captured = {}

        async def fake_make_request(url, params):
            captured['url'] = url
            captured['params'] = params
            # next link without a page parameter should trigger the else branch that uses the next URL as-is
            return ({"values": [], "next": "https://other.example.com/next/resource"}, {})

        inst._make_request = fake_make_request

        # When there are no repos, _parse_repository won't be called; result should be an empty list
        result = await inst.get_paginated_repos(
            page=1, per_page=5, sort=input_sort, installation_id="ws", query=None
        )

        assert captured["url"] == f"{inst.BASE_URL}/repositories/ws"
        assert captured["params"]["pagelen"] == 5
        assert captured["params"]["page"] == 1
        assert captured["params"]["sort"] == expected_sort
        # No query provided so 'q' should not be in params
        assert "q" not in captured["params"]
        # No repository values -> empty result
        assert result == []
