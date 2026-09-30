import pytest
import types

from openhands.integrations.forgejo.service.features import ForgejoFeaturesMixin
from openhands.integrations.service_types import ResourceNotFoundError


class DummyFeatures(ForgejoFeaturesMixin):
    # avoid any base-class initialization; mixin methods only rely on patched attributes
    def __init__(self):
        pass


@pytest.mark.asyncio
async def test_valid_item_and_cursorrules_round_078():
    inst = DummyFeatures()

    # synchronous helpers
    inst._determine_microagents_path = lambda repository: "microagents_path"

    def is_valid(item):
        return item.get("name") == "a"

    inst._is_valid_microagent_file = is_valid
    inst._get_file_name_from_item = lambda item: f"{item['name']}.py"
    inst._get_file_path_from_item = lambda item, path: f"{path}/{item['name']}.py"

    created_calls = []

    def create_microagent_response(file_name, file_path):
        # record calls and return a simple dict as the MicroagentResponse
        created_calls.append((file_name, file_path))
        return {"file_name": file_name, "file_path": file_path}

    inst._create_microagent_response = create_microagent_response

    # async helpers
    async def fake_get_microagents_directory_url(repository, microagents_path):
        assert repository == "owner/repo"
        assert microagents_path == "microagents_path"
        return "http://fake/directory"

    async def fake_make_request(directory_url):
        # return a list with one valid and one invalid item, plus a ignored second return
        return [{"name": "a"}, {"name": "b"}], None

    async def fake_check_cursorrules_file(repository):
        return {"cursor": "value"}

    inst._get_microagents_directory_url = fake_get_microagents_directory_url
    inst._make_request = fake_make_request
    inst._check_cursorrules_file = fake_check_cursorrules_file

    result = await inst.get_microagents("owner/repo")

    # Expect one created microagent (for item 'a') and then the cursorrules dict appended
    assert isinstance(result, list)
    assert result[0] == {"file_name": "a.py", "file_path": "microagents_path/a.py"}
    assert result[1] == {"cursor": "value"}
    # ensure create_microagent_response was invoked with expected values
    assert created_calls == [("a.py", "microagents_path/a.py")]


@pytest.mark.asyncio
async def test_non_list_items_and_no_cursorrules_round_078():
    inst = DummyFeatures()

    inst._determine_microagents_path = lambda repository: "microagents_path"

    async def fake_get_microagents_directory_url(repository, microagents_path):
        return "http://fake/directory"

    async def fake_make_request(directory_url):
        # Return a dict -> items is not a list, so the loop should be skipped
        return {"not": "a list"}, None

    async def fake_check_cursorrules_file(repository):
        return False

    inst._get_microagents_directory_url = fake_get_microagents_directory_url
    inst._make_request = fake_make_request
    inst._check_cursorrules_file = fake_check_cursorrules_file

    result = await inst.get_microagents("owner/repo")

    # items was not a list and cursorrules returned False => empty list
    assert result == []


@pytest.mark.asyncio
async def test_directory_not_found_resource_error_round_078():
    inst = DummyFeatures()

    inst._determine_microagents_path = lambda repository: "microagents_path"

    async def raising_get_microagents_directory_url(repository, microagents_path):
        raise ResourceNotFoundError("not found")

    # mark if make_request is (incorrectly) called
    called = {"make_request": False}

    async def fake_make_request(directory_url):
        called["make_request"] = True
        return [], None

    async def fake_check_cursorrules_file(repository):
        return False

    inst._get_microagents_directory_url = raising_get_microagents_directory_url
    inst._make_request = fake_make_request
    inst._check_cursorrules_file = fake_check_cursorrules_file

    result = await inst.get_microagents("owner/repo")

    # ResourceNotFoundError should set items = [] and not call _make_request
    assert result == []
    assert called["make_request"] is False


@pytest.mark.asyncio
async def test_general_exception_logs_and_graceful_round_078():
    inst = DummyFeatures()

    inst._determine_microagents_path = lambda repository: "microagents_path"

    async def raising_get_microagents_directory_url(repository, microagents_path):
        raise RuntimeError("boom")

    # capture log calls
    log_calls = []

    def fake_log_microagent_warning(repository, message):
        log_calls.append((repository, message))

    async def fake_check_cursorrules_file(repository):
        return False

    inst._get_microagents_directory_url = raising_get_microagents_directory_url
    inst._log_microagent_warning = fake_log_microagent_warning
    inst._make_request = lambda url: (_ for _ in ()).throw(AssertionError("should not be called"))
    inst._check_cursorrules_file = fake_check_cursorrules_file

    result = await inst.get_microagents("owner/repo")

    # general exception should be caught, logged, and result be empty list (no cursorrules)
    assert result == []
    assert len(log_calls) == 1
    # message should include the original exception text
    assert log_calls[0][0] == "owner/repo"
    assert "boom" in log_calls[0][1]
