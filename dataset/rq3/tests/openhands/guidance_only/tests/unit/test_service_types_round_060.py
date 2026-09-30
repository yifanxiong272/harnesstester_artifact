import pytest
from types import SimpleNamespace

import openhands.integrations.service_types as st
from openhands.integrations.service_types import BaseGitService, ResourceNotFoundError

# All tests in this module exercise BaseGitService._process_microagents_directory
# by calling the coroutine as an unbound function and providing a SimpleNamespace
# object with the attributes the implementation expects. Logger calls are
# captured by patching the module-level logger.

@pytest.mark.asyncio
async def test_process_microagents_list_round_060(monkeypatch):
    calls = {"warnings": [], "infos": []}

    def fake_warning(msg):
        calls["warnings"].append(msg)

    def fake_info(msg):
        calls["infos"].append(msg)

    monkeypatch.setattr(st, "logger", SimpleNamespace(warning=fake_warning, info=fake_info))

    # Prepare a response that's a plain list (items should be response itself)
    async def fake_get_dir_url(repository, microagents_path):
        return "http://example.com/dir"

    def fake_get_dir_params(microagents_path):
        return {"p": microagents_path}

    async def fake_make_request(directory_url, directory_params, method=None):
        # Return a list response and a dummy second value as the real function does
        return ([{"name": "microA"}], None)

    def fake_is_valid(item):
        # should be called for each item
        return True

    def fake_get_file_name(item):
        return item.get("name", "unknown")

    def fake_get_file_path(item, microagents_path):
        return f"{microagents_path}/{item.get('name')}"

    def fake_create_response(file_name, file_path):
        return {"file_name": file_name, "file_path": file_path}

    self_obj = SimpleNamespace(
        _get_microagents_directory_url=fake_get_dir_url,
        _get_microagents_directory_params=fake_get_dir_params,
        _make_request=fake_make_request,
        _is_valid_microagent_file=fake_is_valid,
        _get_file_name_from_item=fake_get_file_name,
        _get_file_path_from_item=fake_get_file_path,
        _create_microagent_response=fake_create_response,
    )

    result = await BaseGitService._process_microagents_directory(self_obj, "repo", "microagents")

    assert result == [{"file_name": "microA", "file_path": "microagents/microA"}]
    # no warnings or infos in the success path
    assert calls["warnings"] == []
    assert calls["infos"] == []


@pytest.mark.asyncio
async def test_process_microagents_values_round_060(monkeypatch):
    # response is a dict with 'values' key (Bitbucket style)
    collected = {"warns": []}

    def fake_warning(msg):
        collected["warns"].append(msg)

    monkeypatch.setattr(st, "logger", SimpleNamespace(warning=fake_warning, info=lambda *_: None))

    async def fake_get_dir_url(repository, microagents_path):
        return "url"

    def fake_get_dir_params(microagents_path):
        return {}

    async def fake_make_request(directory_url, directory_params, method=None):
        return ({"values": [{"name": "v1"}, {"name": "v2"}]}, None)

    # Mark only v2 as valid to force branching inside the loop
    def fake_is_valid(item):
        return item.get("name") == "v2"

    def fake_get_file_name(item):
        return item.get("name")

    def fake_get_file_path(item, microagents_path):
        return f"{microagents_path}/{item.get('name')}"

    def fake_create_response(file_name, file_path):
        return (file_name, file_path)

    self_obj = SimpleNamespace(
        _get_microagents_directory_url=fake_get_dir_url,
        _get_microagents_directory_params=fake_get_dir_params,
        _make_request=fake_make_request,
        _is_valid_microagent_file=fake_is_valid,
        _get_file_name_from_item=fake_get_file_name,
        _get_file_path_from_item=fake_get_file_path,
        _create_microagent_response=fake_create_response,
    )

    result = await BaseGitService._process_microagents_directory(self_obj, "repo", "mpath")

    assert result == [("v2", "mpath/v2")]
    assert collected["warns"] == []


@pytest.mark.asyncio
async def test_process_microagents_nodes_and_inner_exception_round_060(monkeypatch):
    # response is a dict with 'nodes' key (GraphQL style) and inner processing raises
    logged = {"warnings": [], "infos": []}

    def fake_warning(msg):
        logged["warnings"].append(msg)

    def fake_info(msg):
        logged["infos"].append(msg)

    monkeypatch.setattr(st, "logger", SimpleNamespace(warning=fake_warning, info=fake_info))

    async def fake_get_dir_url(repository, microagents_path):
        return "url"

    def fake_get_dir_params(microagents_path):
        return {}

    async def fake_make_request(directory_url, directory_params, method=None):
        # provide one node that is valid per _is_valid check
        return ({"nodes": [{"name": "bad"}]}, None)

    def fake_is_valid(item):
        return True

    def failing_get_file_name(item):
        # simulate a parsing error when extracting the name
        raise RuntimeError("parse failed")

    # _get_file_path_from_item exists but won't be called due to failure
    def fake_get_file_path(item, microagents_path):
        return "unused"

    def fake_create_response(file_name, file_path):
        return {"ok": True}

    self_obj = SimpleNamespace(
        _get_microagents_directory_url=fake_get_dir_url,
        _get_microagents_directory_params=fake_get_dir_params,
        _make_request=fake_make_request,
        _is_valid_microagent_file=fake_is_valid,
        _get_file_name_from_item=failing_get_file_name,
        _get_file_path_from_item=fake_get_file_path,
        _create_microagent_response=fake_create_response,
    )

    result = await BaseGitService._process_microagents_directory(self_obj, "repo", "mfolder")

    # Because the inner processing raised, the item should be skipped and a warning logged
    assert result == []
    assert any("Error processing microagent" in str(m) for m in logged["warnings"]) 


@pytest.mark.asyncio
async def test_process_microagents_resource_not_found_round_060(monkeypatch):
    # Simulate the directory URL lookup raising ResourceNotFoundError
    logged = {"infos": [], "warnings": []}

    def fake_info(msg):
        logged["infos"].append(msg)

    def fake_warning(msg):
        logged["warnings"].append(msg)

    monkeypatch.setattr(st, "logger", SimpleNamespace(info=fake_info, warning=fake_warning))

    async def raising_get_dir_url(repository, microagents_path):
        raise ResourceNotFoundError("no dir")

    self_obj = SimpleNamespace(
        _get_microagents_directory_url=raising_get_dir_url,
        # other attributes won't be touched when exception is raised early
    )

    result = await BaseGitService._process_microagents_directory(self_obj, "repo", "mp")

    assert result == []
    assert any("No microagents directory found" in str(m) for m in logged["infos"]) 


@pytest.mark.asyncio
async def test_process_microagents_outer_exception_round_060(monkeypatch):
    # Simulate an unexpected error while fetching the directory URL -> warning logged
    logs = {"warnings": []}

    def fake_warning(msg):
        logs["warnings"].append(msg)

    monkeypatch.setattr(st, "logger", SimpleNamespace(warning=fake_warning, info=lambda *_: None))

    async def raising_value_error(repository, microagents_path):
        raise ValueError("fail fetch")

    self_obj = SimpleNamespace(_get_microagents_directory_url=raising_value_error)

    result = await BaseGitService._process_microagents_directory(self_obj, "repo", "mp")

    assert result == []
    assert any("Error fetching microagents directory" in str(m) for m in logs["warnings"])
