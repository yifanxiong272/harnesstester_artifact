import pytest

from openhands.integrations import service_types as st


class DummyService(st.BaseGitService):
    # implement all abstract members so the class can be instantiated
    @property
    def provider(self):
        return "dummy"

    async def _get_cursorrules_url(self, repository):
        return "cursorrules://url"

    async def _get_microagents_directory_url(self, repository, microagents_path):
        return "fake://default"

    def _get_microagents_directory_params(self, microagents_path):
        return {}

    def _is_valid_microagent_file(self, item):
        return False

    def _get_file_name_from_item(self, item):
        # basic default behavior
        return item.get("name") if isinstance(item, dict) else None

    def _get_file_path_from_item(self, item, microagents_path):
        return item.get("path") if isinstance(item, dict) else None

    async def _make_request(self, url, params, method=None):
        # default safe response
        return ([], None)


@pytest.mark.asyncio
async def test_values_dict_processing_round_060():
    ds = DummyService()

    # Response uses 'values' branch
    async def fake_get_microagents_directory_url(repository, microagents_path):
        return "fake://url"

    def fake_get_microagents_directory_params(microagents_path):
        return {"p": 1}

    async def fake_make_request(directory_url, directory_params, method=None):
        return ({"values": [{"name": "a", "path": "p"}]}, None)

    def fake_is_valid(item):
        return True

    def fake_get_file_name(item):
        return item["name"]

    def fake_get_file_path(item, microagents_path):
        return item["path"]

    def fake_create_resp(name, path):
        return {"name": name, "path": path}

    ds._get_microagents_directory_url = fake_get_microagents_directory_url
    ds._get_microagents_directory_params = fake_get_microagents_directory_params
    ds._make_request = fake_make_request
    ds._is_valid_microagent_file = fake_is_valid
    ds._get_file_name_from_item = fake_get_file_name
    ds._get_file_path_from_item = fake_get_file_path
    ds._create_microagent_response = fake_create_resp

    result = await ds._process_microagents_directory("repo", "microagents")
    assert result == [{"name": "a", "path": "p"}]


@pytest.mark.asyncio
async def test_nodes_dict_processing_round_060():
    ds = DummyService()

    async def fake_get_microagents_directory_url(repository, microagents_path):
        return "fake://url2"

    def fake_get_microagents_directory_params(microagents_path):
        return None

    async def fake_make_request(directory_url, directory_params, method=None):
        return ({"nodes": [{"name": "b", "path": "q"}]}, None)

    def fake_is_valid(item):
        return True

    def fake_get_file_name(item):
        return item["name"]

    def fake_get_file_path(item, microagents_path):
        return item["path"]

    def fake_create_resp(name, path):
        return (name, path)

    ds._get_microagents_directory_url = fake_get_microagents_directory_url
    ds._get_microagents_directory_params = fake_get_microagents_directory_params
    ds._make_request = fake_make_request
    ds._is_valid_microagent_file = fake_is_valid
    ds._get_file_name_from_item = fake_get_file_name
    ds._get_file_path_from_item = fake_get_file_path
    ds._create_microagent_response = fake_create_resp

    result = await ds._process_microagents_directory("repo", "microagents")
    assert result == [("b", "q")]


@pytest.mark.asyncio
async def test_list_response_and_skip_invalid_round_060():
    ds = DummyService()

    async def fake_get_microagents_directory_url(repository, microagents_path):
        return "fake://url3"

    def fake_get_microagents_directory_params(microagents_path):
        return {}

    async def fake_make_request(directory_url, directory_params, method=None):
        # return a plain list; items will be iterated
        return ([{"name": "c", "path": "r"}], None)

    def fake_is_valid(item):
        # mark as invalid so nothing is appended
        return False

    ds._get_microagents_directory_url = fake_get_microagents_directory_url
    ds._get_microagents_directory_params = fake_get_microagents_directory_params
    ds._make_request = fake_make_request
    ds._is_valid_microagent_file = fake_is_valid

    result = await ds._process_microagents_directory("repo", "microagents")
    assert result == []


@pytest.mark.asyncio
async def test_inner_processing_exception_logs_warning_round_060():
    ds = DummyService()

    async def fake_get_microagents_directory_url(repository, microagents_path):
        return "fake://url4"

    def fake_get_microagents_directory_params(microagents_path):
        return {}

    async def fake_make_request(directory_url, directory_params, method=None):
        return ([{"name": "bad_item", "path": "x"}], None)

    def fake_is_valid(item):
        return True

    def fake_get_file_name(item):
        raise ValueError("bad file")

    # capture warning messages
    called = {"warnings": []}

    def fake_warning(msg):
        called["warnings"].append(msg)

    # replace logger.warning used by the module
    original_warning = st.logger.warning
    st.logger.warning = fake_warning

    try:
        ds._get_microagents_directory_url = fake_get_microagents_directory_url
        ds._get_microagents_directory_params = fake_get_microagents_directory_params
        ds._make_request = fake_make_request
        ds._is_valid_microagent_file = fake_is_valid
        ds._get_file_name_from_item = fake_get_file_name

        result = await ds._process_microagents_directory("repo", "microagents")
        # On exception during processing the item, it should be skipped and warning logged
        assert result == []
        assert any("bad_item" in w or "unknown" in w or "bad file" in w for w in called["warnings"]) 
    finally:
        st.logger.warning = original_warning


@pytest.mark.asyncio
async def test_resource_not_found_and_generic_exception_round_060():
    # Test ResourceNotFoundError path
    ds1 = DummyService()

    async def raise_not_found(repository, microagents_path):
        raise st.ResourceNotFoundError("no dir")

    info_called = {"msgs": []}

    def fake_info(msg):
        info_called["msgs"].append(msg)

    original_info = st.logger.info
    st.logger.info = fake_info

    try:
        ds1._get_microagents_directory_url = raise_not_found
        result = await ds1._process_microagents_directory("repo", "microagents")
        # Should return empty list and log info
        assert result == []
        assert any("No microagents directory" in m for m in info_called["msgs"]) 
    finally:
        st.logger.info = original_info

    # Test generic exception path from _make_request
    ds2 = DummyService()

    async def good_url(repository, microagents_path):
        return "url"

    def params(p):
        return {}

    async def raise_generic(directory_url, directory_params, method=None):
        raise Exception("boom")

    warn_called = {"msgs": []}

    def fake_warn(msg):
        warn_called["msgs"].append(msg)

    original_warn = st.logger.warning
    st.logger.warning = fake_warn

    try:
        ds2._get_microagents_directory_url = good_url
        ds2._get_microagents_directory_params = params
        ds2._make_request = raise_generic

        result = await ds2._process_microagents_directory("repo", "microagents")
        assert result == []
        assert any("Error fetching microagents directory" in m for m in warn_called["msgs"]) 
    finally:
        st.logger.warning = original_warn
