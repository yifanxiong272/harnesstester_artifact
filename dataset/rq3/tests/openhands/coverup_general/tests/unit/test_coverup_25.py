# file: openhands/server/services/conversation_service.py:80-164
# asked: {"lines": [92, 93, 94, 95, 96, 97, 100, 101, 102, 103, 105, 106, 107, 110, 111, 112, 115, 116, 118, 119, 122, 123, 124, 126, 127, 130, 131, 133, 134, 135, 136, 137, 138, 139, 140, 142, 144, 145, 146, 149, 150, 151, 152, 153, 156, 157, 158, 159, 160, 161, 163, 164], "branches": [[106, 107], [106, 130], [114, 122], [114, 126], [126, 127], [126, 133], [139, 140], [139, 142], [150, 151], [150, 156]]}
# gained: {"lines": [92, 93, 94, 95, 96, 97, 100, 101, 102, 103, 105, 106, 107, 110, 111, 112, 115, 116, 118, 122, 123, 124, 126, 127, 130, 131, 133, 134, 135, 136, 137, 138, 139, 140, 142, 144, 145, 146, 149, 150, 151, 152, 153, 156, 157, 158, 159, 160, 161, 163, 164], "branches": [[106, 107], [106, 130], [114, 122], [114, 126], [126, 127], [139, 140], [150, 151]]}

import pytest
from types import SimpleNamespace

from pydantic import SecretStr

from openhands.server.services import conversation_service
from openhands.server.services.conversation_service import start_conversation
from openhands.server.types import LLMAuthenticationError, MissingSettingsError
from openhands.storage.data_models.conversation_metadata import ConversationMetadata
from openhands.server.data_models.agent_loop_info import AgentLoopInfo

from openhands.integrations.service_types import ProviderType
from openhands.integrations.provider import ProviderToken, CustomSecret
from openhands.core.config.mcp_config import MCPConfig


class _FakeStore:
    def __init__(self, settings):
        self._settings = settings

    async def load(self):
        return self._settings


class _FakeSecret:
    def __init__(self, val: str | None):
        self._val = val

    def get_secret_value(self):
        return self._val


class _FakeSettings:
    def __init__(self, llm_model: str | None, llm_api_key: _FakeSecret | None, **kwargs):
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.mark.asyncio
async def test_missing_settings_raises(monkeypatch):
    async def fake_get_instance(cfg, user_id):
        return _FakeStore(None)

    monkeypatch.setattr(
        conversation_service.SettingsStoreImpl,
        "get_instance",
        fake_get_instance,
    )

    conv_meta = ConversationMetadata(conversation_id="c1", selected_repository=None)

    with pytest.raises(MissingSettingsError):
        await start_conversation(
            user_id="user1",
            git_provider_tokens=None,
            custom_secrets=None,
            initial_user_msg=None,
            image_urls=None,
            replay_json=None,
            conversation_id="conv-123",
            conversation_metadata=conv_meta,
            conversation_instructions=None,
            mcp_config=None,
        )


@pytest.mark.asyncio
async def test_missing_api_key_raises_when_not_bedrock_or_lemonade(monkeypatch):
    fake_settings = _FakeSettings(llm_model="gpt-test", llm_api_key=None, some_setting="x")

    async def fake_get_instance(cfg, user_id):
        return _FakeStore(fake_settings)

    monkeypatch.setattr(
        conversation_service.SettingsStoreImpl,
        "get_instance",
        fake_get_instance,
    )

    conv_meta = ConversationMetadata(conversation_id="c2", selected_repository="repo2")

    with pytest.raises(LLMAuthenticationError):
        await start_conversation(
            user_id="user2",
            git_provider_tokens=None,
            custom_secrets=None,
            initial_user_msg=None,
            image_urls=None,
            replay_json=None,
            conversation_id="conv-456",
            conversation_metadata=conv_meta,
            conversation_instructions="instr",
            mcp_config=None,
        )


@pytest.mark.asyncio
async def test_bedrock_model_starts_agent_loop_and_passes_args(monkeypatch):
    fake_settings = _FakeSettings(llm_model="bedrock/awesome", llm_api_key=None, extra_setting="y")

    async def fake_get_instance(cfg, user_id):
        return _FakeStore(fake_settings)

    captured = {}

    async def fake_maybe_start_agent_loop(conversation_id, conversation_init_data, user_id_arg, initial_user_msg=None, replay_json=None):
        captured["conversation_id"] = conversation_id
        captured["conversation_init_data"] = conversation_init_data
        captured["user_id_arg"] = user_id_arg
        captured["initial_user_msg"] = initial_user_msg
        captured["replay_json"] = replay_json
        return AgentLoopInfo(conversation_id=conversation_id, url="http://x", session_api_key="key", event_store=None)

    monkeypatch.setattr(
        conversation_service.SettingsStoreImpl,
        "get_instance",
        fake_get_instance,
    )

    # monkeypatch the conversation_manager to use our fake coroutine
    monkeypatch.setattr(
        conversation_service,
        "conversation_manager",
        SimpleNamespace(maybe_start_agent_loop=fake_maybe_start_agent_loop),
    )

    conv_meta = ConversationMetadata(conversation_id="c3", selected_repository="repo3", selected_branch="branch1", git_provider=None)

    # create valid provider token and custom secret objects
    provider_token = ProviderToken(token=SecretStr("val"))
    git_provider_tokens = {ProviderType.GITHUB: provider_token}
    custom_secret = CustomSecret(secret=SecretStr("s"))
    custom_secrets = {"mysecret": custom_secret}

    mcp = MCPConfig()  # valid MCPConfig instance

    result = await start_conversation(
        user_id="user3",
        git_provider_tokens=git_provider_tokens,
        custom_secrets=custom_secrets,
        initial_user_msg="Hello there",
        image_urls=["http://img"],
        replay_json='{"replay": true}',
        conversation_id="conv-789",
        conversation_metadata=conv_meta,
        conversation_instructions="do things",
        mcp_config=mcp,
    )

    assert isinstance(result, AgentLoopInfo)
    assert result.conversation_id == "conv-789"
    assert result.url == "http://x"
    assert result.session_api_key == "key"

    assert captured["conversation_id"] == "conv-789"
    init_data = captured["conversation_init_data"]

    # verify repository and branch
    assert getattr(init_data, "selected_repository") == "repo3"
    assert getattr(init_data, "selected_branch") == "branch1"

    # verify provider token was preserved
    gpt = getattr(init_data, "git_provider_tokens")
    assert gpt is not None
    # mappingproxy or dict: access with ProviderType.GITHUB
    token_obj = gpt[ProviderType.GITHUB]
    assert isinstance(token_obj, ProviderToken)
    assert token_obj.token.get_secret_value() == "val"

    # verify custom secrets
    cs = getattr(init_data, "custom_secrets")
    assert cs is not None
    secret_obj = cs["mysecret"]
    assert isinstance(secret_obj, CustomSecret)
    assert secret_obj.secret.get_secret_value() == "s"

    # verify mcp_config included
    assert getattr(init_data, "mcp_config") is not None
    assert isinstance(getattr(init_data, "mcp_config"), MCPConfig)

    # verify initial message action attributes
    initial_msg = captured["initial_user_msg"]
    assert initial_msg is not None
    assert getattr(initial_msg, "content") == "Hello there"
    assert getattr(initial_msg, "image_urls") == ["http://img"]
    assert captured["replay_json"] == '{"replay": true}'
