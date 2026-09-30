import types
import pytest

from openhands.integrations.bitbucket.service import repos as repos_mod

# We will bind the original method to lightweight dummy instances so we can
# patch the attribute lookups the method performs (BASE_URL, _make_request,
# _parse_repository) without instantiating the mixin's real base class.

async_get_paginated = repos_mod.BitBucketReposMixin.get_paginated_repos

class Dummy:
    pass

@pytest.mark.asyncio
async def test_no_installation_round_025():
    """When installation_id is falsy the method should return an empty list.

    Covers early-return branch for missing installation_id (line ~129).
    """
    dummy = Dummy()
    # Bind method to dummy
    bound = types.MethodType(async_get_paginated, dummy)

    result = await bound(page=1, per_page=10, sort='updated', installation_id=None)
    assert result == []


@pytest.mark.asyncio
async def test_sort_pushed_with_query_and_next_page_round_025():
    """Covers:
    - mapping of sort 'pushed' -> '-updated_on'
    - adding query param
    - next link containing a page query param (extraction branch)
    - parse_repository called with formatted link header that contains workspace url and extracted page
    """
    dummy = Dummy()
    dummy.BASE_URL = 'https://api.bitbucket.org/2.0'

    workspace_slug = 'workspace1'
    expected_workspace_url = f'{dummy.BASE_URL}/repositories/{workspace_slug}'

    # Prepare response with a next link that contains a page parameter
    response = {
        'values': [
            {'name': 'repo-alpha'},
        ],
        'next': f'https://api.bitbucket.org/2.0/repositories/{workspace_slug}?page=3&pagelen=10'
    }
    headers = {}

    async def mock_make_request(url, params):
        # The code under test should call with the workspace repos url
        assert url == expected_workspace_url
        # For sort 'pushed' the implementation uses '-updated_on'
        assert params['sort'] == '-updated_on'
        # page and pagelen passed through
        assert params['page'] == 2
        assert params['pagelen'] == 5
        # query should be formatted with name~"{query}"
        assert params['q'] == 'name~"search-term"'
        return response, headers

    # parse_repository should receive the formatted header with extracted page=3
    def mock_parse_repository(repo, link_header=''):
        assert repo['name'] == 'repo-alpha'
        assert link_header == f'<{expected_workspace_url}?page=3>; rel="next"'
        return {'parsed_name': repo['name'], 'link': link_header}

    dummy._make_request = mock_make_request
    dummy._parse_repository = mock_parse_repository

    bound = types.MethodType(async_get_paginated, dummy)
    repos = await bound(page=2, per_page=5, sort='pushed', installation_id=workspace_slug, query='search-term')

    assert isinstance(repos, list)
    assert repos == [{'parsed_name': 'repo-alpha', 'link': f'<{expected_workspace_url}?page=3>; rel="next"'}]


@pytest.mark.asyncio
async def test_sort_full_name_next_without_page_round_025():
    """Covers:
    - mapping of sort 'full_name' -> 'name'
    - handling of next link that does NOT contain a page parameter (uses next as-is)
    """
    dummy = Dummy()
    dummy.BASE_URL = 'https://api.bitbucket.org/2.0'
    workspace_slug = 'ws-2'
    expected_workspace_url = f'{dummy.BASE_URL}/repositories/{workspace_slug}'

    response = {
        'values': [
            {'name': 'repo-beta'},
        ],
        # next link without a page query parameter
        'next': 'https://external.service/some/continuation-token'
    }
    headers = {}

    async def mock_make_request(url, params):
        assert url == expected_workspace_url
        # 'full_name' must map to 'name'
        assert params['sort'] == 'name'
        # no query provided in this test
        assert 'q' not in params
        return response, headers

    def mock_parse_repository(repo, link_header=''):
        # When page cannot be parsed from next, the next URL should be used as-is
        assert link_header == f'<{response["next"]}>; rel="next"'
        return {'parsed': repo['name'], 'link': link_header}

    dummy._make_request = mock_make_request
    dummy._parse_repository = mock_parse_repository

    bound = types.MethodType(async_get_paginated, dummy)
    repos = await bound(page=1, per_page=2, sort='full_name', installation_id=workspace_slug)

    assert repos == [{'parsed': 'repo-beta', 'link': f'<{response["next"]}>; rel="next"'}]


@pytest.mark.asyncio
async def test_sort_created_default_round_025():
    """Covers mapping for 'created' -> '-created_on' as well as default fallback behavior.

    This test invokes 'created' mapping and asserts that the returned parsed
    repo list comes from _parse_repository even when there's no next link.
    """
    dummy = Dummy()
    dummy.BASE_URL = 'https://api.bitbucket.org/2.0'
    workspace_slug = 'ws-created'
    expected_workspace_url = f'{dummy.BASE_URL}/repositories/{workspace_slug}'

    response = {
        'values': [
            {'name': 'repo-gamma'},
        ],
        # no next link, so formatted_link_header should remain empty
    }
    headers = {}

    async def mock_make_request(url, params):
        assert url == expected_workspace_url
        # created mapping should set '-created_on'
        assert params['sort'] == '-created_on'
        return response, headers

    def mock_parse_repository(repo, link_header=''):
        # no next link -> link_header should be empty string
        assert link_header == ''
        return {'n': repo['name']}

    dummy._make_request = mock_make_request
    dummy._parse_repository = mock_parse_repository

    bound = types.MethodType(async_get_paginated, dummy)
    repos = await bound(page=1, per_page=1, sort='created', installation_id=workspace_slug)

    assert repos == [{'n': 'repo-gamma'}]
