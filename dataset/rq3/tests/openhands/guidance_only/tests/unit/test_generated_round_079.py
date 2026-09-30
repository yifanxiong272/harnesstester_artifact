import pytest
from types import MethodType, SimpleNamespace
from openhands.integrations.github.service.repos import GitHubReposMixin
from openhands.server.types import AppMode

# All test functions/classes end with _round_079 per contract

@pytest.mark.asyncio
async def test_public_short_query_round_079():
    """Public search with too-short URL parts should return empty list (len(split) < 4).
    Covers branch: if public: -> short-split -> return []
    """
    class Dummy:
        pass

    self = Dummy()
    self.BASE_URL = "https://api.github.com"

    # Attach minimal required callables (not used for this branch)
    async def _make_request(url, params):
        # should not be called for this test
        raise AssertionError("_make_request should not be called for short public query")

    self._make_request = _make_request

    # Bind and call the async method
    bound_search = MethodType(GitHubReposMixin.search_repositories, self)

    result = await bound_search("org/repo", per_page=5, sort="stars", order="desc", public=True, app_mode=AppMode.SAAS)
    assert result == []


@pytest.mark.asyncio
async def test_public_long_query_triggers_request_and_parsing_round_079():
    """Public search with long URL (>=4 parts) should build q with is:public and return parsed items.
    Covers branch: public True -> set params['q'] -> default request path
    """
    class Dummy:
        pass

    self = Dummy()
    self.BASE_URL = "https://api.github.com"

    recorded = {"calls": []}

    async def _make_request(url, params):
        # Record call for assertions
        recorded["calls"].append((url, dict(params)))
        # Return a response containing items that will be parsed
        return {"items": [{"name": "repo-one"}]}, None

    def _parse_repository(repo):
        # deterministic parse behavior for test
        return {"parsed": repo.get("name")}

    self._make_request = _make_request
    self._parse_repository = _parse_repository

    bound_search = MethodType(GitHubReposMixin.search_repositories, self)

    # Use a URL-like query so split('/') has >=4 parts
    query = "https://github.com/acme/repo"
    result = await bound_search(query, per_page=7, sort="updated", order="asc", public=True, app_mode=AppMode.SAAS)

    # Assert we got parsed result from returned item
    assert result == [{"parsed": "repo-one"}]

    # Assert the _make_request was called once and the params included the is:public modifier
    assert len(recorded["calls"]) == 1
    _, params_sent = recorded["calls"][0]
    assert "q" in params_sent
    assert "is:public" in params_sent["q"]


@pytest.mark.asyncio
async def test_private_query_with_slash_uses_org_query_round_079():
    """Private search where query contains a slash should set q to org:... in:name ... and call _make_request once.
    Covers branch: not public and '/' in query
    """
    class Dummy:
        pass

    self = Dummy()
    self.BASE_URL = "https://api.github.com"

    recorded = {"calls": []}

    async def _make_request(url, params):
        recorded["calls"].append(dict(params))
        return {"items": [{"name": "org-repo"}]}, None

    def _parse_repository(repo):
        return (repo.get("name"),)

    self._make_request = _make_request
    self._parse_repository = _parse_repository

    bound_search = MethodType(GitHubReposMixin.search_repositories, self)

    # Use AppMode.SAAS here; the slash-handling branch does not depend on app_mode value
    result = await bound_search("acme/project-x", per_page=3, sort="stars", order="desc", public=False, app_mode=AppMode.SAAS)

    # Should parse the single returned repo
    assert result == [("org-repo",)]
    # Ensure only one request happened and query was set to org:acme in:name project-x
    assert len(recorded["calls"]) == 1
    sent = recorded["calls"][0]
    assert sent.get("q") == "org:acme in:name project-x"


@pytest.mark.asyncio
async def test_private_no_slash_saas_with_user_orgs_and_fuzzy_repos_round_079():
    """Private search without slash in SAAS mode: exercises get_user, get_organizations_from_installations, and fuzzy-match True branch.
    This covers many branches in the not-public flow including user search, org search, and org repos (fuzzy True).
    """
    class Dummy:
        pass

    self = Dummy()
    self.BASE_URL = "https://api.github.com"

    # Provide a deterministic user
    async def get_user():
        return SimpleNamespace(login="alice")

    # SAAS path uses get_organizations_from_installations
    async def get_organizations_from_installations():
        return ["acme"]

    # Sequence of responses for successive _make_request calls:
    # 1) user search -> items: u1
    # 2) org search -> items: o1
    # 3) org repos top -> items: top1
    responses = [({"items": [{"name": "u1"}]}, None), ({"items": [{"name": "o1"}]}, None), ({"items": [{"name": "top1"}]}, None)]

    recorded_params = []

    async def _make_request(url, params):
        # record and pop next response
        recorded_params.append(dict(params))
        try:
            return responses.pop(0)
        except IndexError:
            # Should not happen; fail deterministically
            raise AssertionError("Unexpected extra _make_request call")

    def _parse_repository(repo):
        return repo.get("name")

    def _fuzzy_match_org_name(query, org_name):
        # Force fuzzy True to exercise the branch that fetches top repos
        return True

    self.get_user = get_user
    self.get_organizations_from_installations = get_organizations_from_installations
    self.get_user_organizations = lambda: []  # not used in SAAS path
    self._make_request = _make_request
    self._parse_repository = _parse_repository
    self._fuzzy_match_org_name = _fuzzy_match_org_name

    bound_search = MethodType(GitHubReposMixin.search_repositories, self)

    result = await bound_search("searchname", per_page=5, sort="stars", order="desc", public=False, app_mode=AppMode.SAAS)

    # Should combine parsed results from user_items, org_items, and top org repos
    assert set(result) == {"u1", "o1", "top1"}

    # Validate that three requests were made in the expected order and that the last call had sort=stars and per_page=2
    assert len(recorded_params) == 3
    assert recorded_params[-1]["sort"] == "stars"
    assert recorded_params[-1]["per_page"] == 2


@pytest.mark.asyncio
async def test_private_no_slash_user_and_org_search_exceptions_round_079():
    """If user search fails and org search fails, the function should handle exceptions and return an empty list.
    This covers the exception branches that log warnings for user and org searches.
    """
    class Dummy:
        pass

    self = Dummy()
    self.BASE_URL = "https://api.github.com"

    async def get_user():
        return SimpleNamespace(login="bob")

    async def get_user_organizations():
        return ["broken-org"]

    # Make user search raise, and org search raise, so all_repos remains empty
    async def _make_request(url, params):
        raise RuntimeError("simulated request failure")

    # fuzzy should not be invoked (but provide it anyway)
    def _fuzzy_match_org_name(query, org):
        return False

    self.get_user = get_user
    self.get_user_organizations = get_user_organizations
    self.get_organizations_from_installations = lambda: []
    self._make_request = _make_request
    self._parse_repository = lambda repo: repo  # not used
    self._fuzzy_match_org_name = _fuzzy_match_org_name

    bound_search = MethodType(GitHubReposMixin.search_repositories, self)

    # Use a non-SAAS sentinel to force the else branch that calls get_user_organizations
    result = await bound_search("searchname", per_page=4, sort="updated", order="desc", public=False, app_mode="NON_SAAS")

    # On repeated failures, should return an empty list rather than propagating
    assert result == []
