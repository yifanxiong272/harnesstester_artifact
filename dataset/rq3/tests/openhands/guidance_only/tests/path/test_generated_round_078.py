import pytest

from openhands.integrations.forgejo.service.features import ForgejoFeaturesMixin
from openhands.integrations.service_types import ResourceNotFoundError


class DummyForgejoValid(ForgejoFeaturesMixin):
    # synchronous method in real class
    def _determine_microagents_path(self, repository):
        return "microagents_dir"

    async def _get_microagents_directory_url(self, repository, microagents_path):
        return "http://fake.url/directory"

    async def _make_request(self, directory_url):
        # return a list with one valid and one invalid item
        return ([{"name": "valid"}, {"name": "invalid"}], None)

    def _is_valid_microagent_file(self, item):
        return item.get("name") == "valid"

    def _get_file_name_from_item(self, item):
        return item["name"]

    def _get_file_path_from_item(self, item, microagents_path):
        return f"{microagents_path}/{item['name']}"

    def _create_microagent_response(self, file_name, file_path):
        # return a plain dict as the MicroagentResponse shape substitute
        return {"file_name": file_name, "file_path": file_path}

    async def _check_cursorrules_file(self, repository):
        # No cursorrules present for this test
        return None


class DummyForgejoResourceNotFound(ForgejoFeaturesMixin):
    def _determine_microagents_path(self, repository):
        return "microagents_dir"

    async def _get_microagents_directory_url(self, repository, microagents_path):
        # Simulate the directory not existing
        raise ResourceNotFoundError()

    # These shouldn't be called when ResourceNotFoundError is raised, but provide them anyway
    async def _make_request(self, directory_url):
        return ([], None)

    async def _check_cursorrules_file(self, repository):
        # Simulate a cursorrules presence
        return {"cursorrules": True}


class DummyForgejoGenericError(ForgejoFeaturesMixin):
    def _determine_microagents_path(self, repository):
        return "microagents_dir"

    async def _get_microagents_directory_url(self, repository, microagents_path):
        # Simulate an unexpected generic error
        raise RuntimeError("boom")

    async def _make_request(self, directory_url):
        return ([], None)

    async def _check_cursorrules_file(self, repository):
        return False

    def _log_microagent_warning(self, repository, message):
        # record the last log call for assertions
        self._last_warning = (repository, message)


class DummyForgejoItemsNotList(ForgejoFeaturesMixin):
    def _determine_microagents_path(self, repository):
        return "microagents_dir"

    async def _get_microagents_directory_url(self, repository, microagents_path):
        return "http://fake.url/directory"

    async def _make_request(self, directory_url):
        # return a non-list to trigger the branch that skips iteration
        return ({"not": "a list"}, None)

    async def _check_cursorrules_file(self, repository):
        return False


@pytest.mark.asyncio
async def test_get_microagents_with_valid_and_invalid_items_round_078():
    inst = object.__new__(DummyForgejoValid)
    # call the async method under test
    result = await inst.get_microagents("some/repo")

    # Should only include the valid item transformed by _create_microagent_response
    assert isinstance(result, list)
    assert any(isinstance(r, dict) for r in result)
    assert {"file_name": "valid", "file_path": "microagents_dir/valid"} in result
    # invalid entry must not be present
    assert not any(r.get("file_name") == "invalid" for r in result)


@pytest.mark.asyncio
async def test_get_microagents_resource_not_found_and_cursorrules_round_078():
    inst = object.__new__(DummyForgejoResourceNotFound)
    result = await inst.get_microagents("some/repo")

    # When ResourceNotFoundError is raised, items should be treated as empty list
    # and cursorrules (if present) should be appended as-is
    assert result == [{"cursorrules": True}]


@pytest.mark.asyncio
async def test_get_microagents_generic_exception_logs_warning_round_078():
    inst = object.__new__(DummyForgejoGenericError)
    # ensure no previous warning recorded
    assert not hasattr(inst, "_last_warning")

    result = await inst.get_microagents("some/repo")

    # Generic exception should cause a warning to be logged and return an empty list
    assert hasattr(inst, "_last_warning")
    repo_logged, message = inst._last_warning
    assert repo_logged == "some/repo"
    assert "boom" in message
    assert result == []


@pytest.mark.asyncio
async def test_get_microagents_items_not_list_round_078():
    inst = object.__new__(DummyForgejoItemsNotList)
    result = await inst.get_microagents("some/repo")

    # When items is not a list, iteration branch should be skipped and no microagents created
    assert result == []
