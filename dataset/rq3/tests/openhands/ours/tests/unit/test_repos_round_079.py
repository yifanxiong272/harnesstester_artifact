import pytest
import types

from openhands.integrations.github.service import repos as repos_mod
from openhands.server.types import AppMode

# Helpers

def make_instance():
    # Provide a minimal concrete subclass to satisfy abstract methods on GitHubReposMixin
    class Dummy(repos_mod.GitHubReposMixin):
        # Implement required abstract methods with minimal deterministic behavior
        def _get_cursorrules_url(self):
            return ""

        def _get_file_name_from_item(self, item):
            return ""

        def _get_file_path_from_item(self, item):
            return ""

        def _get_microagents_directory_params(self):
            return {}

        def _get_microagents_directory_url(self):
            return ""

        def _is_valid_microagent_file(self, name):
            return False

    # Create instance without running any real __init__ side effects
    inst = object.__new__(Dummy)
    inst.BASE_URL = "https://api.github.com"
    return inst


@pytest.mark.asyncio
async def test_public_short_query_round_079():
    """
    public=True and query parts < 4 -> early return [] (covers lines 222-225)
    """
    inst = make_instance()

    result = await repos_mod.GitHubReposMixin.search_repositories(
        inst, query="a/b", per_page=10, sort="stars", order="desc", public=True, app_mode=AppMode.SAAS
    )

    assert result == []


@pytest.mark.asyncio
async def test_public_long_query_round_079():
    """
    public=True and query contains enough '/' parts -> ensure params['q'] is set and
    _make_request is called with that param (covers lines 227-231 and default case 293-296)
    """
    inst = make_instance()

    # Prepare a long query so url_parts[3] and url_parts[4] exist
    query = "one/two/three/myorg/myrepo"

    captured = {}

    async def fake_make_request(url, params):
        # capture call for assertion
        captured['url'] = url
        captured['params'] = dict(params)
        return ({'items': [{'id': 1}, {'id': 2}]}, None)

    def fake_parse(repo):
        # deterministic parse shape
        return {"parsed": repo['id']}

    inst._make_request = fake_make_request
    inst._parse_repository = fake_parse

    result = await repos_mod.GitHubReposMixin.search_repositories(
        inst, query=query, per_page=5, sort="updated", order="asc", public=True, app_mode=AppMode.SAAS
    )

    # Validate the constructed query parameter included is:public and the org/repo
    assert captured['params']['q'] == f"in:name myorg/myrepo is:public"
    # Assert returned parsed items preserved order and mapping
    assert result == [{"parsed": 1}, {"parsed": 2}]


@pytest.mark.asyncio
async def test_not_public_with_slash_round_079():
    """
    not public and query contains '/' -> should set q to 'org:... in:name ...' and call _make_request
    (covers lines 233-236 and default case)
    """
    inst = make_instance()

    async def fake_make_request(url, params):
        # Return a single item showing the org-based query path was used
        return ({'items': [{'name': params['q']}]}, None)

    def fake_parse(repo):
        return repo['name']

    inst._make_request = fake_make_request
    inst._parse_repository = fake_parse

    res = await repos_mod.GitHubReposMixin.search_repositories(
        inst, query="acme/special", per_page=3, sort="stars", order="desc", public=False, app_mode=AppMode.SAAS
    )

    # Expect we parsed back the q string into result
    assert res == [f"org:acme in:name special"]


@pytest.mark.asyncio
async def test_not_public_saas_mixed_responses_round_079():
    """
    not public, no slash, app_mode=SAAS: exercise the user search, per-org search, and per-org-top-repos
    paths including exceptions to hit warning branches (covers lines 237-291, including exception branches 253-258, 266-271, 283-289, and fuzzy match branch 275-281)
    """
    inst = make_instance()

    # Provide a user object with login
    user_obj = types.SimpleNamespace(login="alice")

    async def fake_get_user():
        return user_obj

    # Two orgs: first will behave normally, second will cause an exception in org search
    user_orgs = ["org_good", "org_bad"]

    async def fake_get_organizations_from_installations():
        return user_orgs

    # Capture the sequence of q values requested to determine behavior
    calls = []

    async def fake_make_request(url, params):
        q = params.get('q', '')
        calls.append(q)
        # user search q starts with 'in:name'
        if q.startswith('in:name') and 'user:alice' in q:
            return ({'items': [{'id': 'u1'}]}, None)
        # org search for org_good
        if q.endswith(' org:org_good') or q.startswith('special org:org_good'):
            return ({'items': [{'id': 'o1'}]}, None)
        # org search for org_bad -> simulate exception
        if q.endswith(' org:org_bad'):
            raise RuntimeError("org search failure")
        # org_repos search for fuzzy-match orgs (org_good only)
        if q == 'org:org_good':
            return ({'items': [{'id': 'r1'}]}, None)
        # Default: return empty
        return ({'items': []}, None)

    # Fuzzy match: only org_good matches
    def fake_fuzzy(q, org):
        return org == 'org_good'

    def fake_parse(repo):
        return repo.get('id', None)

    inst.get_user = fake_get_user
    inst.get_organizations_from_installations = fake_get_organizations_from_installations
    inst._make_request = fake_make_request
    inst._fuzzy_match_org_name = fake_fuzzy
    inst._parse_repository = fake_parse

    result = await repos_mod.GitHubReposMixin.search_repositories(
        inst, query="special", per_page=10, sort="stars", order="desc", public=False, app_mode=AppMode.SAAS
    )

    # Expect parsed ids from user search (u1), org_good search (o1), and org_good top repos (r1)
    # org_bad search raised and should not prevent others
    assert set(result) == {"u1", "o1", "r1"}
    # Ensure we called for the user query and organization queries and top-repos query
    assert any('user:alice' in q or q.startswith('in:name') for q in calls)
    assert any('org:org_good' in q for q in calls)
    assert any(q == 'org:org_good' or q.startswith('org:org_good') for q in calls)


@pytest.mark.asyncio
async def test_not_public_non_saas_uses_user_orgs_round_079():
    """
    not public, no slash, non-SAAS app_mode -> uses get_user_organizations path (covers lines 240-244 branching to get_user_organizations)
    """
    inst = make_instance()

    user_obj = types.SimpleNamespace(login="bob")

    async def fake_get_user():
        return user_obj

    async def fake_get_user_organizations():
        return ["orgx"]

    async def fake_make_request(url, params):
        q = params.get('q', '')
        # user search uses user: login
        if 'user:bob' in q:
            return ({'items': [{'id': 'uu'}]}, None)
        if 'org:orgx' in q:
            return ({'items': [{'id': 'oo'}]}, None)
        return ({'items': []}, None)

    def fake_parse(repo):
        return repo['id']

    inst.get_user = fake_get_user
    inst.get_user_organizations = fake_get_user_organizations
    inst._make_request = fake_make_request
    inst._parse_repository = fake_parse

    result = await repos_mod.GitHubReposMixin.search_repositories(
        inst, query="findme", per_page=5, sort="stars", order="desc", public=False, app_mode=AppMode.SELF_HOSTED
    )

    # Should have parsed entries from user search and orgx search
    assert set(result) == {"uu", "oo"}
