# file: openhands/server/conversation_manager/docker_nested_conversation_manager.py:547-628
# asked: {"lines": [547, 548, 549, 553, 554, 557, 558, 559, 560, 561, 562, 563, 564, 566, 567, 568, 569, 571, 572, 573, 574, 576, 577, 579, 580, 581, 583, 584, 585, 586, 587, 590, 591, 593, 594, 597, 599, 600, 603, 604, 607, 608, 609, 612, 614, 615, 616, 617, 618, 619, 620, 621, 622, 626, 628], "branches": [[590, 591], [590, 593], [597, 599], [597, 607], [608, 609], [608, 612]]}
# gained: {"lines": [547, 548, 549, 553, 554, 557, 558, 559, 560, 561, 562, 563, 564, 566, 567, 568, 569, 571, 572, 573, 574, 576, 577, 579, 580, 581, 583, 584, 585, 586, 587, 590, 591, 593, 594, 597, 599, 600, 603, 604, 607, 608, 609, 612, 614, 615, 616, 617, 618, 619, 620, 621, 622, 626, 628], "branches": [[590, 591], [590, 593], [597, 599], [597, 607], [608, 609], [608, 612]]}

import os
import types
import asyncio
import pytest

import openhands.server.conversation_manager.docker_nested_conversation_manager as dncm_module


class FakeSandbox:
    def __init__(self, runtime_startup_env_vars=None, volumes=None, runtime_container_image=None, user_id=42):
        self.runtime_startup_env_vars = runtime_startup_env_vars or {}
        self.volumes = volumes
        self.runtime_container_image = runtime_container_image
        self.user_id = user_id


class FakeConfig:
    def __init__(
        self,
        default_agent="fake_agent",
        run_as_openhands=True,
        file_store="local",
        file_store_path="~/fake_store",
        sandbox=None,
    ):
        self.default_agent = default_agent
        self.run_as_openhands = run_as_openhands
        self.file_store = file_store
        self.file_store_path = file_store_path
        self.sandbox = sandbox or FakeSandbox()
        # store for checking later
        self._copied = False

    def get_agent_config(self, agent_cls):
        # return a simple config object to be passed to Agent
        return {"agent_cls": agent_cls}

    def model_copy(self, deep=False):
        # return a shallow copy-like object for mutation inside _create_runtime
        new = FakeConfig(
            default_agent=self.default_agent,
            run_as_openhands=self.run_as_openhands,
            file_store=self.file_store,
            file_store_path=self.file_store_path,
            sandbox=FakeSandbox(
                runtime_startup_env_vars=dict(self.sandbox.runtime_startup_env_vars),
                volumes=self.sandbox.volumes,
                runtime_container_image=self.sandbox.runtime_container_image,
                user_id=self.sandbox.user_id,
            ),
        )
        new._copied = True
        return new


class FakeSession:
    def __init__(self, sid, llm_registry, conversation_stats, file_store, config, sio, user_id):
        # mimic signature used in the method
        self.sid = sid
        self.llm_registry = llm_registry
        self.conversation_stats = conversation_stats
        self.file_store = file_store
        self.config = config
        self.sio = sio
        self.user_id = user_id
        self.notified = False

    def _notify_on_llm_retry(self, *args, **kwargs):
        self.notified = True


class FakeAgent:
    def __init__(self, agent_config, llm_registry):
        self.agent_config = agent_config
        self.llm_registry = llm_registry
        self.sandbox_plugins = ["pluginA"]


class FakeDockerRuntime:
    def __init__(self, *, config, event_stream, sid, plugins, headless_mode, attach_to_existing, main_module, llm_registry):
        # capture all parameters for assertions
        self.config = config
        self.event_stream = event_stream
        self.sid = sid
        self.plugins = plugins
        self.headless_mode = headless_mode
        self.attach_to_existing = attach_to_existing
        self.main_module = main_module
        self.llm_registry = llm_registry
        # default behavior; will be overridden by manager
        self.setup_initial_env_called = False

    def setup_initial_env(self):
        self.setup_initial_env_called = True


class FakeEventStream:
    def __init__(self, sid, file_store, user_id):
        self.sid = sid
        self.file_store = file_store
        self.user_id = user_id


@pytest.mark.asyncio
async def test_create_runtime_with_local_file_store_and_no_runtime_image(monkeypatch, tmp_path):
    # Prepare module under test
    mod = dncm_module

    # Monkeypatch dependencies used in _create_runtime
    # create_registry_and_conversation_stats -> returns llm_registry, conversation_stats, config
    llm_registry = types.SimpleNamespace()
    conversation_stats = {"stats": 1}
    # create a config with no sandbox.volumes set (None) and runtime_container_image None
    fake_config = FakeConfig(
        default_agent="fake_agent",
        run_as_openhands=True,
        file_store="local",
        file_store_path=str(tmp_path / "store_path"),
        sandbox=FakeSandbox(runtime_startup_env_vars={"EXISTING": "1"}, volumes=None, runtime_container_image=None, user_id=99),
    )

    def fake_create_registry_and_conversation_stats(cfg, sid, user_id, settings):
        # return copies to simulate creation
        return llm_registry, conversation_stats, fake_config

    monkeypatch.setattr(mod, "create_registry_and_conversation_stats", fake_create_registry_and_conversation_stats)

    # Session replacement
    monkeypatch.setattr(mod, "Session", FakeSession)

    # Agent.get_cls replacement
    class AgentWrapper:
        @staticmethod
        def get_cls(name):
            return FakeAgent

    monkeypatch.setattr(mod, "Agent", AgentWrapper)

    # EventStream replacement
    monkeypatch.setattr(mod, "EventStream", FakeEventStream)

    # DockerRuntime replacement
    monkeypatch.setattr(mod, "DockerRuntime", FakeDockerRuntime)

    # get_conversation_dir replacement
    monkeypatch.setattr(mod, "get_conversation_dir", lambda sid, user_id: f"conv_{sid}")

    # Create manager instance
    manager = mod.DockerNestedConversationManager(
        sio="sio_dummy",
        config=fake_config,
        server_config="server_cfg",
        file_store="local",
    )
    # set a runtime container image string on the manager to be used if config doesn't have one
    manager._runtime_container_image = "manager_image:latest"

    # ensure _get_session_api_key_for_conversation returns a known key
    monkeypatch.setattr(manager, "_get_session_api_key_for_conversation", lambda sid: "API_KEY_123")

    # call the coroutine
    settings = types.SimpleNamespace(agent=None)
    runtime = await manager._create_runtime("SID1", "user1", settings)

    # Assertions about returned runtime and mutated config
    assert isinstance(runtime, FakeDockerRuntime)
    # sandbox.volumes should have been updated to include the local file_store mapping
    # expected mapping: <realpath file_store_path>/conv_SID1:/root/.openhands/conv_SID1:rw
    expanded_path = os.path.realpath(os.path.expanduser(fake_config.file_store_path))
    expected_mapping = f"{expanded_path}/conv_SID1:/root/.openhands/conv_SID1:rw"
    assert expected_mapping in runtime.config.sandbox.volumes.split(",")
    # runtime_container_image should be set from manager when initially None
    assert runtime.config.sandbox.runtime_container_image == "manager_image:latest"
    # plugins should come from the FakeAgent instance
    assert runtime.plugins == ["pluginA"]
    # ensure setup_initial_env has been replaced with a lambda (callable) and does not set flag
    # After replacement it should be a lambda doing nothing; calling it should not set the FakeDockerRuntime flag
    runtime.setup_initial_env()
    assert not getattr(runtime, "setup_initial_env_called", False)


@pytest.mark.asyncio
async def test_create_runtime_with_existing_volumes_and_nonlocal_file_store(monkeypatch):
    mod = dncm_module

    # Prepare fake config where sandbox.volumes is a comma-separated string with spaces
    orig_volumes = " /mnt/vol1 , /opt/vol2 "
    fake_config = FakeConfig(
        default_agent="agentX",
        run_as_openhands=False,  # test USER env var becomes 'root' when False
        file_store="s3",  # non-local should not add file_store mapping
        file_store_path="~/should_not_be_used",
        sandbox=FakeSandbox(runtime_startup_env_vars={}, volumes=orig_volumes, runtime_container_image="preset_image:1.0", user_id=7),
    )

    llm_registry = types.SimpleNamespace()
    conversation_stats = {"cs": 2}

    def fake_create_registry_and_conversation_stats(cfg, sid, user_id, settings):
        return llm_registry, conversation_stats, fake_config

    monkeypatch.setattr(mod, "create_registry_and_conversation_stats", fake_create_registry_and_conversation_stats)
    monkeypatch.setattr(mod, "Session", FakeSession)

    class AgentWrapper:
        @staticmethod
        def get_cls(name):
            return FakeAgent

    monkeypatch.setattr(mod, "Agent", AgentWrapper)
    monkeypatch.setattr(mod, "EventStream", FakeEventStream)
    monkeypatch.setattr(mod, "DockerRuntime", FakeDockerRuntime)
    monkeypatch.setattr(mod, "get_conversation_dir", lambda sid, user_id: f"conv_{sid}")

    manager = mod.DockerNestedConversationManager(
        sio="sio_dummy2",
        config=fake_config,
        server_config="server_cfg2",
        file_store="s3",
    )
    # Set runtime image on manager to a different value to ensure existing image is preserved
    manager._runtime_container_image = "should_not_use_this:latest"
    monkeypatch.setattr(manager, "_get_session_api_key_for_conversation", lambda sid: "KEY_XYZ")

    settings = types.SimpleNamespace(agent="agent_override")
    runtime = await manager._create_runtime("SID2", None, settings)

    # Confirm that volumes string was split, stripped, and rejoined
    expected_joined = ",".join([v.strip() for v in orig_volumes.split(",") if v.strip()])
    assert runtime.config.sandbox.volumes == expected_joined
    # Because file_store != 'local', no mapping with conversation dir should be appended
    assert "conv_SID2" not in runtime.config.sandbox.volumes
    # runtime_container_image should be preserved from config (not overwritten by manager)
    assert runtime.config.sandbox.runtime_container_image == "preset_image:1.0"
    # Check env vars were set correctly in the copied config
    env = runtime.config.sandbox.runtime_startup_env_vars
    assert env["CONVERSATION_MANAGER_CLASS"].endswith("StandaloneConversationManager")
    assert env["SERVE_FRONTEND"] == "0"
    assert env["RUNTIME"] == "local"
    # run_as_openhands False => USER should be 'root'
    assert env["USER"] == "root"
    # SANDBOX_USER_ID should be the sandbox user_id string
    assert env["SANDBOX_USER_ID"] == str(fake_config.sandbox.user_id)
    # SESSION_API_KEY should match the monkeypatched method
    assert env["SESSION_API_KEY"] == "KEY_XYZ"
    # Other env flags set
    assert env["ALLOW_SET_CONVERSATION_ID"] == "1"
    assert env["WORKSPACE_BASE"] == "/workspace"
    assert env["SANDBOX_CLOSE_DELAY"] == "0"
    assert env["SKIP_DEPENDENCY_CHECK"] == "1"
    assert env["INITIAL_NUM_WARM_SERVERS"] == "1"
    # plugins should be passed through
    assert runtime.plugins == ["pluginA"]
