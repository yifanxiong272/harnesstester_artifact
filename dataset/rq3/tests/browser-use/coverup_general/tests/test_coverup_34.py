# file: browser_use/skills/service.py:39-138
# asked: {"lines": [39, 45, 46, 47, 50, 52, 54, 55, 56, 57, 59, 61, 62, 63, 64, 66, 68, 69, 70, 74, 77, 78, 79, 81, 82, 83, 84, 85, 87, 90, 91, 92, 95, 96, 97, 99, 100, 102, 105, 107, 110, 111, 112, 115, 118, 119, 120, 121, 124, 125, 126, 127, 128, 129, 130, 132, 133, 135, 136, 137, 138], "branches": [[45, 46], [45, 50], [59, 61], [59, 77], [68, 69], [68, 74], [81, 82], [81, 99], [91, 92], [91, 95], [95, 96], [95, 97], [99, 100], [99, 102], [110, 111], [110, 115], [120, 121], [120, 124], [124, 125], [124, 132]]}
# gained: {"lines": [39, 45, 46, 47, 50, 52, 54, 55, 56, 57, 59, 61, 62, 63, 64, 66, 68, 69, 70, 74, 77, 78, 79, 81, 82, 83, 84, 85, 87, 90, 91, 95, 96, 97, 99, 100, 102, 105, 107, 110, 111, 112, 115, 118, 119, 120, 121, 124, 125, 126, 127, 128, 129, 130, 132, 133, 135, 136, 137, 138], "branches": [[45, 46], [45, 50], [59, 61], [59, 77], [68, 69], [81, 82], [81, 99], [91, 95], [95, 96], [95, 97], [99, 100], [99, 102], [110, 111], [110, 115], [120, 121], [124, 125], [124, 132]]}

import pytest
from types import SimpleNamespace

@pytest.mark.asyncio
async def test_async_init_wildcard_fetches_and_caches(monkeypatch):
    # Prepare 100 skill responses to trigger the wildcard single-page path and the page_size warning branch
    page_size = 100
    items = [SimpleNamespace(id=i, status='finished') for i in range(page_size)]

    class FakeSkillsAPI:
        async def list_skills(self, page_size, page_number, is_enabled=True):
            # ignore page_number, always return the single page
            return SimpleNamespace(items=items)

    class FakeAsyncBrowserUse:
        def __init__(self, api_key):
            self.skills = FakeSkillsAPI()

    # Monkeypatch the AsyncBrowserUse used in the service module
    monkeypatch.setattr('browser_use.skills.service.AsyncBrowserUse', FakeAsyncBrowserUse)

    # Monkeypatch Skill.from_skill_response to produce simple objects with id and title attributes
    def fake_from_skill_response(response):
        return SimpleNamespace(id=str(response.id), title=f"title-{response.id}")

    monkeypatch.setattr('browser_use.skills.service.Skill.from_skill_response', fake_from_skill_response)

    # Import here to ensure monkeypatch replacements are used by service
    from browser_use.skills.service import SkillService

    svc = SkillService(skill_ids=['*'], api_key='test-key')
    assert not svc._initialized

    await svc.async_init()

    # After initialization, should be marked initialized and cache should contain 100 skills
    assert svc._initialized is True
    assert len(svc._skills) == page_size
    # verify a couple of keys exist and mapping used str(id)
    assert '0' in svc._skills
    assert '99' in svc._skills
    assert svc._skills['0'].title == 'title-0'

    # Call async_init again to exercise early-return branch (should not recreate client)
    # Mark _initialized True to ensure immediate return path
    svc._initialized = True

    # Make a client that would raise if created (to ensure it is not called)
    created = {'flag': False}
    class ExplodingClient:
        def __init__(self, api_key):
            created['flag'] = True
            raise RuntimeError("should not be created")

    monkeypatch.setattr('browser_use.skills.service.AsyncBrowserUse', ExplodingClient)
    await svc.async_init()
    # Ensure the exploding client was not instantiated during the early return
    assert created['flag'] is False


@pytest.mark.asyncio
async def test_async_init_explicit_pagination_and_conversion_error(monkeypatch):
    # Test explicit IDs path with pagination and conversion error for one item
    requested = {'1', '2', '3'}

    page_size = 100

    # Prepare pages: page 1 contains id '1' plus filler items of length == page_size to force another page
    page1_items = [SimpleNamespace(id=1, status='finished')] + [
        SimpleNamespace(id=100 + i, status='finished') for i in range(page_size - 1)
    ]
    # page 2 contains id '2' which will raise during conversion, plus filler to make it full page
    page2_items = [SimpleNamespace(id=2, status='finished')] + [
        SimpleNamespace(id=200 + i, status='finished') for i in range(page_size - 1)
    ]
    # page 3 will be empty to break pagination
    page3_items = []

    class FakeSkillsAPI:
        async def list_skills(self, page_size, page_number, is_enabled=True):
            if page_number == 1:
                return SimpleNamespace(items=page1_items)
            elif page_number == 2:
                return SimpleNamespace(items=page2_items)
            else:
                return SimpleNamespace(items=page3_items)

    class FakeAsyncBrowserUse:
        def __init__(self, api_key):
            self.skills = FakeSkillsAPI()

    monkeypatch.setattr('browser_use.skills.service.AsyncBrowserUse', FakeAsyncBrowserUse)

    # from_skill_response: for id == 2 raise an exception to hit conversion error branch
    def maybe_raise(response):
        if str(response.id) == '2' or response.id == 2:
            raise ValueError("conversion failed")
        return SimpleNamespace(id=str(response.id), title=f"title-{response.id}")

    monkeypatch.setattr('browser_use.skills.service.Skill.from_skill_response', maybe_raise)

    from browser_use.skills.service import SkillService

    svc = SkillService(skill_ids=['1', '2', '3'], api_key='test-key')

    await svc.async_init()

    # conversion for id '2' should have failed and not been cached
    assert svc._initialized is True
    assert '1' in svc._skills
    assert '2' not in svc._skills
    assert '3' not in svc._skills  # missing and should not be cached
    # ensure the cached item has expected title
    assert svc._skills['1'].title == 'title-1'


@pytest.mark.asyncio
async def test_async_init_pagination_limit_warning(monkeypatch):
    # Test the case where pagination reaches max_pages and no requested IDs found
    # Use a requested id that will never appear
    requested_ids = ['9']
    page_size = 100

    # Produce full pages for pages 1..5 to trigger the "page > max_pages" warning branch
    def items_for_page(page_number):
        # produce page_size items none of which have id '9'
        base = 1000 * page_number
        return [SimpleNamespace(id=base + i, status='finished') for i in range(page_size)]

    class FakeSkillsAPI:
        async def list_skills(self, page_size, page_number, is_enabled=True):
            return SimpleNamespace(items=items_for_page(page_number))

    class FakeAsyncBrowserUse:
        def __init__(self, api_key):
            self.skills = FakeSkillsAPI()

    monkeypatch.setattr('browser_use.skills.service.AsyncBrowserUse', FakeAsyncBrowserUse)

    # conversion simple pass-through
    def from_skill_response(response):
        return SimpleNamespace(id=str(response.id), title=f"title-{response.id}")

    monkeypatch.setattr('browser_use.skills.service.Skill.from_skill_response', from_skill_response)

    from browser_use.skills.service import SkillService

    svc = SkillService(skill_ids=requested_ids, api_key='test-key')

    await svc.async_init()

    # Because '9' was never found, no skills cached and initialization completed
    assert svc._initialized is True
    assert svc._skills == {}


@pytest.mark.asyncio
async def test_async_init_raises_during_fetch_and_sets_initialized(monkeypatch):
    # Simulate an exception raised during the skills.list_skills call;
    # outer except should set _initialized True and re-raise the exception.

    class ExplodingSkillsAPI:
        async def list_skills(self, page_size, page_number, is_enabled=True):
            raise RuntimeError("fetch failed")

    class FakeAsyncBrowserUse:
        def __init__(self, api_key):
            self.skills = ExplodingSkillsAPI()

    monkeypatch.setattr('browser_use.skills.service.AsyncBrowserUse', FakeAsyncBrowserUse)

    from browser_use.skills.service import SkillService

    svc = SkillService(skill_ids=['*'], api_key='test-key')

    with pytest.raises(RuntimeError, match="fetch failed"):
        await svc.async_init()

    # Even though exception was raised, the service should be marked as initialized to avoid retry loops
    assert svc._initialized is True
