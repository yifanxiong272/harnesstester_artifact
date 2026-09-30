import pytest

from openhands.integrations.bitbucket.service.repos import BitBucketReposMixin


class DummyRepos(BitBucketReposMixin):
    """A minimal concrete class to exercise BitBucketReposMixin.get_paginated_repos.

    This dummy implements the async _make_request and synchronous _parse_repository
    used by the mixin. It also records the last request URL and params for assertions.
    """

    BASE_URL = "https://api.bitbucket.org/2.0"

    def __init__(self, response):
        # response is a dict that will be returned from _make_request
        self._response = response
        self.last_url = None
        self.last_params = None

    async def _make_request(self, url, params):
        # Record what was requested and return the configured response
        self.last_url = url
        # make a shallow copy to avoid accidental mutation in tests
        self.last_params = dict(params)
        # _make_request in the real class returns (response, headers)
        return self._response, {}

    def _parse_repository(self, repo: dict, link_header: str = ""):
        # Return a deterministic structure so tests can assert on it.
        return {"parsed_slug": repo.get("slug"), "link_header": link_header}


@pytest.mark.asyncio
async def test_returns_empty_when_no_installation_id_round_025():
    dummy = DummyRepos(response={"values": []})

    # installation_id falsy should immediately return an empty list
    result = await dummy.get_paginated_repos(page=1, per_page=10, sort="pushed", installation_id=None)

    assert result == []


@pytest.mark.asyncio
async def test_pushed_with_query_and_next_page_round_025():
    # Prepare a next URL that contains a page parameter to hit the page-match branch
    response = {
        "values": [{"slug": "r1"}],
        "next": f"{DummyRepos.BASE_URL}/repositories/workspace123?page=5"
    }
    dummy = DummyRepos(response=response)

    result = await dummy.get_paginated_repos(
        page=1,
        per_page=20,
        sort="pushed",
        installation_id="workspace123",
        query="testq",
    )

    # Ensure the request was targeted at the workspace URL
    expected_workspace_url = f"{DummyRepos.BASE_URL}/repositories/workspace123"
    assert dummy.last_url == expected_workspace_url

    # 'pushed' should map to '-updated_on'
    assert dummy.last_params["sort"] == "-updated_on"

    # query should be transformed into the Bitbucket q param with name~"..."
    assert dummy.last_params["q"] == 'name~"testq"'

    # We returned one repo; ensure _parse_repository was used and received the formatted link
    assert len(result) == 1
    expected_formatted = f"<{expected_workspace_url}?page=5>; rel=\"next\""
    assert result[0]["parsed_slug"] == "r1"
    assert result[0]["link_header"] == expected_formatted


@pytest.mark.asyncio
async def test_next_link_without_page_round_025():
    # Next link that does NOT contain a page parameter should go through the else branch
    next_url = "https://external.example.com/next-resource"
    response = {"values": [{"slug": "external"}], "next": next_url}
    dummy = DummyRepos(response=response)

    result = await dummy.get_paginated_repos(
        page=2,
        per_page=5,
        sort="updated",
        installation_id="ws",
        query=None,
    )

    # 'updated' should map to '-updated_on'
    assert dummy.last_params["sort"] == "-updated_on"

    # The link header should embed the raw next URL when a page param cannot be extracted
    assert result[0]["link_header"] == f"<{next_url}>; rel=\"next\""


@pytest.mark.asyncio
async def test_full_name_sort_and_no_next_round_025():
    # When sort == 'full_name' it should map to 'name'. Also cover the branch where there's no next link.
    response = {"values": [], "next": ""}
    dummy = DummyRepos(response=response)

    repos = await dummy.get_paginated_repos(page=1, per_page=10, sort="full_name", installation_id="ws1")

    # No repositories present -> empty list
    assert repos == []
    # Confirm sort mapping
    assert dummy.last_params["sort"] == "name"


@pytest.mark.asyncio
async def test_default_sort_unknown_round_025():
    # Unknown sort should hit the else/default branch and become '-updated_on'
    response = {"values": [{"slug": "one"}], "next": ""}
    dummy = DummyRepos(response=response)

    repos = await dummy.get_paginated_repos(page=3, per_page=1, sort="something_unknown", installation_id="ws2")

    assert dummy.last_params["sort"] == "-updated_on"
    assert repos[0]["parsed_slug"] == "one"
    # No next -> empty link header
    assert repos[0]["link_header"] == ""
