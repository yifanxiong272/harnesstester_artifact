import pytest

from openhands.integrations.bitbucket.service.repos import BitBucketReposMixin


class DummyRepos(BitBucketReposMixin):
    BASE_URL = "https://api.bitbucket.org/2.0"

    def __init__(self, response):
        # response should be a dict that will be returned by _make_request
        self._response = response
        self.requests = []
        self.parsed_args = []

    async def _make_request(self, url, params):
        # Record the call and return the canned response
        # copy params to avoid accidental mutation affecting tests
        self.requests.append((url, params.copy()))
        return (self._response, {})

    def _parse_repository(self, repo, link_header=""):
        # Record parse calls and return a simple parsed representation
        self.parsed_args.append((repo, link_header))
        return {"repo": repo.get("name"), "link": link_header}


@pytest.mark.asyncio
async def test_no_installation_id_round_025():
    """If installation_id is falsy, the method should immediately return an empty list."""
    dummy = DummyRepos({"values": [], "next": ""})

    result = await dummy.get_paginated_repos(page=1, per_page=10, sort="updated", installation_id=None)

    assert result == []
    # Ensure no network-like call was attempted
    assert dummy.requests == []


@pytest.mark.asyncio
async def test_next_link_with_page_round_025():
    """When the response 'next' URL contains a page parameter, the formatted link header
    uses the workspace_repos_url with that page value."""
    # craft response that includes a next URL with a page parameter
    response = {"values": [{"name": "repo1"}], "next": "https://api.bitbucket.org/2.0/repositories/ws1?page=9"}
    dummy = DummyRepos(response)

    result = await dummy.get_paginated_repos(page=2, per_page=5, sort="updated", installation_id="ws1")

    # One repository parsed and returned
    assert isinstance(result, list) and len(result) == 1
    assert result[0]["repo"] == "repo1"

    # The request URL should be built from BASE_URL and the workspace slug
    expected_url = f"{dummy.BASE_URL}/repositories/ws1"
    assert dummy.requests[0][0] == expected_url

    # params sanity checks
    params = dummy.requests[0][1]
    assert params["page"] == 2
    assert params["pagelen"] == 5
    # 'updated' maps to '-updated_on'
    assert params["sort"] == "-updated_on"

    # The parse function should have received the formatted header with extracted page
    expected_header = f"<{expected_url}?page=9>; rel=\"next\""
    assert dummy.parsed_args[0][1] == expected_header


@pytest.mark.asyncio
async def test_next_link_without_page_and_various_sorts_and_query_round_025():
    """Exercise different sort mappings, the default branch, and the 'q' parameter when query is provided.
    Also cover the branch where next exists but no page parameter can be extracted.
    """
    sorts_expected = {
        "pushed": "-updated_on",
        "updated": "-updated_on",
        "created": "-created_on",
        "full_name": "name",
        "other": "-updated_on",  # default branch
    }

    for sort_key, expected_sort in sorts_expected.items():
        # Response with a next link that does NOT contain a page parameter
        response = {"values": [{"name": f"{sort_key}_repo"}], "next": "https://example.com/next"}
        dummy = DummyRepos(response)

        # Provide a query for all but the 'other' key to test presence/absence of 'q'
        query_val = "term" if sort_key != "other" else None

        result = await dummy.get_paginated_repos(page=3, per_page=2, sort=sort_key, installation_id="ws42", query=query_val)

        # Ensure the sort parameter was mapped as expected
        sent_params = dummy.requests[0][1]
        assert sent_params["sort"] == expected_sort

        # Check 'q' presence only when query was provided
        if query_val is not None:
            assert sent_params["q"] == 'name~"term"'
        else:
            assert "q" not in sent_params

        # Because next didn't contain a page, the formatted header should include the raw next URL
        assert dummy.parsed_args[0][1] == f"<{response['next']}>; rel=\"next\""

        # Ensure parsed repository payload corresponds to the response
        assert result[0]["repo"] == f"{sort_key}_repo"
