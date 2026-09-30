import types
import asyncio
from types import SimpleNamespace
import pytest

from browser_use.agent import service

# Helper to bind the unbound coroutine to a fake self
def bind_coroutine(fn, self_obj):
    return types.MethodType(fn, self_obj)

@pytest.mark.asyncio
async def test_no_skill_service_round_052():
    """If self.skill_service is falsy, the coroutine should return an empty string."""
    fake = SimpleNamespace()
    fake.skill_service = None
    # other attributes not needed for this branch
    coro = bind_coroutine(service.Agent._get_unavailable_skills_info, fake)()
    result = await coro
    assert result == ""

@pytest.mark.asyncio
async def test_empty_skills_round_052():
    """If get_all_skills returns an empty list, should return empty string."""
    async def get_all_skills():
        return []

    async def cookies():
        # shouldn't be consulted in this branch, but provide a valid return
        return [{"name": "irrelevant", "value": "x"}]

    fake = SimpleNamespace()
    fake.skill_service = SimpleNamespace(get_all_skills=get_all_skills)
    fake.browser_session = SimpleNamespace(cookies=cookies)
    fake._get_skill_slug = lambda skill_obj, all_skills: "unused-slug"
    fake.logger = SimpleNamespace(error=lambda *a, **k: None)

    coro = bind_coroutine(service.Agent._get_unavailable_skills_info, fake)()
    result = await coro
    assert result == ""

@pytest.mark.asyncio
async def test_unavailable_skills_formatting_round_052():
    """When required cookies are missing, formats an informative multi-line message.

    This covers: detection of cookie params, required defaulting when None, description fallback,
    and use of _get_skill_slug to produce the slug in the formatted output.
    """
    class Param:
        def __init__(self, type, name, required=None, description=None):
            self.type = type
            self.name = name
            self.required = required
            self.description = description

    # Skill s1 needs a 'session' cookie (required default None -> treated as True)
    s1 = SimpleNamespace(
        id="s1",
        title="Skill One",
        description="Desc1",
        parameters=[Param(type="cookie", name="session", required=None, description=None)],
    )

    # Skill s2 needs a 'token' cookie but it's marked not required -> should not be reported
    s2 = SimpleNamespace(
        id="s2",
        title="Skill Two",
        description="Desc2",
        parameters=[Param(type="cookie", name="token", required=False, description="Token desc")],
    )

    async def get_all_skills():
        return [s1, s2]

    # Browser has only the 'token' cookie present
    async def cookies():
        return [{"name": "token", "value": "present"}]

    # _get_skill_slug should be used for s1
    def _get_skill_slug(skill_obj, all_skills):
        # ensure function receives the skill object we expect and returns a deterministic slug
        assert skill_obj is s1
        assert any(s.id == skill_obj.id for s in all_skills)
        return "skill-one-slug"

    fake = SimpleNamespace()
    fake.skill_service = SimpleNamespace(get_all_skills=get_all_skills)
    fake.browser_session = SimpleNamespace(cookies=cookies)
    fake._get_skill_slug = _get_skill_slug
    fake.logger = SimpleNamespace(error=lambda *a, **k: None)

    coro = bind_coroutine(service.Agent._get_unavailable_skills_info, fake)()
    result = await coro

    # Build expected output exactly as the function formats it
    lines = [
        "Unavailable Skills (missing required cookies):",
        "\n  \u2022 skill-one-slug (\"Skill One\")",
        "    Description: Desc1",
        "    Missing cookies:",
        "      - session: No description provided",
    ]
    expected = "\n".join(lines)
    assert result == expected

@pytest.mark.asyncio
async def test_get_all_skills_exception_logs_and_returns_empty_round_052():
    """If get_all_skills raises, the exception should be logged and an empty string returned."""
    async def get_all_skills():
        raise RuntimeError("boom")

    async def cookies():
        return []

    # capture calls to logger.error
    logged = {}

    def capture_error(msg):
        # store last message for assertion
        logged['msg'] = msg

    fake = SimpleNamespace()
    fake.skill_service = SimpleNamespace(get_all_skills=get_all_skills)
    fake.browser_session = SimpleNamespace(cookies=cookies)
    fake._get_skill_slug = lambda skill_obj, all_skills: "unused"
    fake.logger = SimpleNamespace(error=capture_error)

    coro = bind_coroutine(service.Agent._get_unavailable_skills_info, fake)()
    result = await coro

    assert result == ""
    # logger.error should have been called with a message containing the exception name
    assert 'RuntimeError' in logged.get('msg', '')
