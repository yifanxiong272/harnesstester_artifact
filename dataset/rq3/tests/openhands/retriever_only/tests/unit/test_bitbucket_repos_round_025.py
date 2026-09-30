import pytest

from openhands.integrations.bitbucket.service.repos import BitBucketReposMixin


class DummySelf:
    """Minimal stand-in for the real mixin 'self' used by the method under test.

    It provides the attributes and methods the function reads/writes:
    - BASE_URL used to build workspace_repos_url
    - async _make_request(url, params) to return a fake response and capture params
    - _parse_repository(repo, link_header) to return an easily-assertable value
    """

    def __init__(self, base_url="https://api.bitbucket.org/2.0"):
        self.BASE_URL = base_url
        self.last_called = None
        self._response = {}
        self._headers = {}

    async def _make_request(self, url, params):
        # record the request for assertions in tests
        self.last_called = (url, params.copy())
        return self._response, self._headers

    def _parse_repository(self, repo, link_header=""):
        # return a simple, deterministic representation so tests can assert on it
        return {"name": repo.get("name"), "link_header": link_header}


@pytest.mark.asyncio
async def test_return_empty_when_no_installation_round_025():
    """If installation_id is falsy, the function should immediately return an empty list."""
    dummy = DummySelf()

    # Call the unbound async function on the class, supplying our dummy as self
    result = await BitBucketReposMixin.get_paginated_repos(
        dummy, page=1, per_page=10, sort="updated", installation_id=None, query=None
    )

    assert result == []
    # Ensure that no request was made when installation_id is falsy
    assert dummy.last_called is None


@pytest.mark.asyncio
async def test_sort_mappings_with_query_and_next_page_extraction_round_025():
    """Covers sort mappings (pushed/updated/created/full_name/other), query param inclusion,
    and next link that contains a page parameter (page extraction branch).
    """
    sort_cases = [
        ("pushed", "-updated_on"),
        ("updated", "-updated_on"),
        ("created", "-created_on"),
        ("full_name", "name"),
        ("something_else", "-updated_on"),
    ]

    for sort_input, expected_sort in sort_cases:
        dummy = DummySelf()
        # Response contains one repo and a next URL with a page number so the page-match branch is taken
        workspace_slug = "my-workspace"
        next_url = f"https://api.bitbucket.org/2.0/repositories/{workspace_slug}?page=5"
        dummy._response = {"values": [{"name": f"repo-{sort_input}"}], "next": next_url}
        dummy._headers = {"x-fake": "header"}

        result = await BitBucketReposMixin.get_paginated_repos(
            dummy,
            page=2,
            per_page=7,
            sort=sort_input,
            installation_id=workspace_slug,
            query="needle",
        )

        # Ensure _make_request was called with the expected URL and parameters
        expected_url = f"{dummy.BASE_URL}/repositories/{workspace_slug}"
        called_url, called_params = dummy.last_called
        assert called_url == expected_url
        # pagelen and page should be forwarded unchanged
        assert called_params["pagelen"] == 7
        assert called_params["page"] == 2
        # sort should be mapped according to the implementation
        assert called_params["sort"] == expected_sort
        # when query is provided, q parameter should be present and formatted
        assert called_params["q"] == 'name~"needle"'

        # The returned repositories come from _parse_repository; verify they contain expected info
        assert result == [{"name": f"repo-{sort_input}", "link_header": f'<{expected_url}?page=5>; rel="next"'}]


@pytest.mark.asyncio
async def test_next_link_without_page_param_round_025():
    """When the 'next' URL exists but contains no page query parameter, the fallback branch
    that uses the raw next URL should run.
    """
    dummy = DummySelf()
    workspace_slug = "some-ws"
    # Next link without ?page= param
    next_url = "https://example.com/some/path/without_page"
    dummy._response = {"values": [{"name": "no-page-repo"}], "next": next_url}

    result = await BitBucketReposMixin.get_paginated_repos(
        dummy,
        page=1,
        per_page=1,
        sort="updated",
        installation_id=workspace_slug,
        query=None,
    )

    expected_url = f"{dummy.BASE_URL}/repositories/{workspace_slug}"
    # Ensure link header was formatted with the raw next URL when no page param is present
    assert result == [{"name": "no-page-repo", "link_header": f'<{next_url}>; rel="next"'}]

    # Verify that when query is None, no 'q' param is present in the outgoing request
    _, called_params = dummy.last_called
    assert "q" not in called_params


@pytest.mark.asyncio
async def test_no_next_link_results_in_empty_link_header_round_025():
    """When the response has no 'next' entry (empty or missing), the formatted link header
    should be an empty string and still produce parsed repository results.
    """
    dummy = DummySelf()
    workspace_slug = "ws-empty-next"
    dummy._response = {"values": [{"name": "just-one"}], "next": ""}

    result = await BitBucketReposMixin.get_paginated_repos(
        dummy,
        page=3,
        per_page=5,
        sort="created",
        installation_id=workspace_slug,
        query=None,
    )

    # The parse should receive an empty link header
    assert result == [{"name": "just-one", "link_header": ""}]

    # Confirm that the outgoing request included the expected pagelen and page
    _, called_params = dummy.last_called
    assert called_params["pagelen"] == 5
    assert called_params["page"] == 3
