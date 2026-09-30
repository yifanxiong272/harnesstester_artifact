# file: openhands/app_server/app_conversation/live_status_app_conversation_service.py:1976-2061
# asked: {"lines": [1979, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2008, 2009, 2010, 2011, 2013, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2026, 2027, 2029, 2031, 2036, 2037, 2039, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060], "branches": [[2009, 2010], [2009, 2013], [2017, 2018], [2017, 2022], [2018, 2019], [2018, 2022], [2036, 2037], [2036, 2039]]}
# gained: {"lines": [1979, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2008, 2009, 2010, 2011, 2013, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2026, 2027, 2036, 2037, 2039, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060], "branches": [[2009, 2010], [2017, 2018], [2017, 2022], [2018, 2019], [2036, 2037], [2036, 2039]]}

import sys
import types
from types import SimpleNamespace
import pytest

from pydantic import SecretStr

import openhands.app_server.app_conversation.live_status_app_conversation_service as mod
import openhands.app_server.config as config_mod

# Helper async context manager
class AsyncCM:
    def __init__(self, obj):
        self.obj = obj

    async def __aenter__(self):
        return self.obj

    async def __aexit__(self, exc_type, exc, tb):
        return False

@pytest.mark.asyncio
async def test_inject_yields_with_docker_web_url_and_tavily_included(monkeypatch):
    """
    Exercise the branch where:
    - get_global_config().web_url is None
    - sandbox_service is instance of DockerSandboxService -> web_url uses host.docker.internal:host_port
    - openhands.server.shared import fails -> app_mode None -> tavily_api_key is included
    Ensure access_token_hard_timeout is converted to timedelta and tavily_api_key string passed.
    """

    # Prepare dummy objects to be yielded by the various get_* context managers
    user_context_obj = object()
    # Create sandbox object as instance of a DummyDocker class with host_port
    class DummyDocker:
        pass
    sandbox_obj = DummyDocker()
    sandbox_obj.host_port = 54321

    sandbox_spec_obj = object()
    app_conversation_info_obj = object()
    app_conversation_start_task_obj = object()
    event_callback_obj = object()
    event_service_obj = object()
    jwt_service_obj = object()
    httpx_client_obj = object()
    pending_message_obj = object()

    # Monkeypatch the config functions used inside inject (config module)
    monkeypatch.setattr(config_mod, "get_user_context", lambda state, request: AsyncCM(user_context_obj))
    monkeypatch.setattr(config_mod, "get_sandbox_service", lambda state, request: AsyncCM(sandbox_obj))
    monkeypatch.setattr(config_mod, "get_sandbox_spec_service", lambda state, request: AsyncCM(sandbox_spec_obj))
    monkeypatch.setattr(config_mod, "get_app_conversation_info_service", lambda state, request: AsyncCM(app_conversation_info_obj))
    monkeypatch.setattr(config_mod, "get_app_conversation_start_task_service", lambda state, request: AsyncCM(app_conversation_start_task_obj))
    monkeypatch.setattr(config_mod, "get_event_callback_service", lambda state, request: AsyncCM(event_callback_obj))
    monkeypatch.setattr(config_mod, "get_event_service", lambda state, request: AsyncCM(event_service_obj))
    monkeypatch.setattr(config_mod, "get_jwt_service", lambda state, request: AsyncCM(jwt_service_obj))
    monkeypatch.setattr(config_mod, "get_httpx_client", lambda state, request: AsyncCM(httpx_client_obj))
    monkeypatch.setattr(config_mod, "get_pending_message_service", lambda state, request: AsyncCM(pending_message_obj))

    # Also patch the symbol referenced at module level in the target module (it may have been imported earlier)
    monkeypatch.setattr(mod, "get_event_callback_service", lambda state, request: AsyncCM(event_callback_obj))

    # get_global_config is a plain callable returning config object with no web_url
    global_cfg = SimpleNamespace(web_url=None, openhands_provider_base_url="https://provider.example")
    monkeypatch.setattr(config_mod, "get_global_config", lambda: global_cfg)

    # Ensure that importing openhands.server.shared inside inject will FAIL -> triggers except ImportError branch
    monkeypatch.delitem(sys.modules, "openhands.server.shared", raising=False)

    # Replace LiveStatusAppConversationService in module with dummy to capture init kwargs
    captured = {}
    class DummyLiveStatus:
        def __init__(self, *args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs

    monkeypatch.setattr(mod, "LiveStatusAppConversationService", DummyLiveStatus)

    # Make the module treat sandbox_service as DockerSandboxService by monkeypatching that name to our DummyDocker class
    monkeypatch.setattr(mod, "DockerSandboxService", DummyDocker)

    # Create injector with a tavily_api_key and let defaults apply for access_token_hard_timeout
    injector = mod.LiveStatusAppConversationServiceInjector(tavily_api_key=SecretStr("SECRET_TOKEN"))

    # Run the async generator to get the yielded object
    agen = injector.inject(state=None, request=None)
    svc = await agen.__anext__()  # yields our DummyLiveStatus instance
    # Close generator to execute __aexit__ of context managers
    await agen.aclose()

    # Assertions: ensure DummyLiveStatus was constructed with expected kwargs
    kwargs = captured.get('kwargs', {})
    assert kwargs.get('web_url') == f'http://host.docker.internal:{sandbox_obj.host_port}'
    # tavily_api_key should be the raw secret value string
    assert kwargs.get('tavily_api_key') == "SECRET_TOKEN"
    # access_token_hard_timeout should be a timedelta (converted from default int)
    from datetime import timedelta
    assert isinstance(kwargs.get('access_token_hard_timeout'), timedelta)
    # Ensure other passed-through objects exist in kwargs
    assert kwargs.get('user_context') is user_context_obj
    assert kwargs.get('sandbox_service') is sandbox_obj
    assert kwargs.get('httpx_client') is httpx_client_obj
    assert kwargs.get('openhands_provider_base_url') == global_cfg.openhands_provider_base_url

@pytest.mark.asyncio
async def test_inject_preserves_web_url_and_excludes_tavily_on_saas(monkeypatch):
    """
    Exercise branch where:
    - get_global_config().web_url is already set -> preserved
    - server_config exists and app_mode == AppMode.SAAS -> tavily_api_key is excluded (None)
    """

    # Prepare dummy objects
    user_context_obj = object()
    class DummyDocker2:
        pass
    sandbox_obj = DummyDocker2()
    sandbox_obj.host_port = 11111

    sandbox_spec_obj = object()
    app_conversation_info_obj = object()
    app_conversation_start_task_obj = object()
    event_callback_obj = object()
    event_service_obj = object()
    jwt_service_obj = object()
    httpx_client_obj = object()
    pending_message_obj = object()

    # Monkeypatch the config functions
    monkeypatch.setattr(config_mod, "get_user_context", lambda state, request: AsyncCM(user_context_obj))
    monkeypatch.setattr(config_mod, "get_sandbox_service", lambda state, request: AsyncCM(sandbox_obj))
    monkeypatch.setattr(config_mod, "get_sandbox_spec_service", lambda state, request: AsyncCM(sandbox_spec_obj))
    monkeypatch.setattr(config_mod, "get_app_conversation_info_service", lambda state, request: AsyncCM(app_conversation_info_obj))
    monkeypatch.setattr(config_mod, "get_app_conversation_start_task_service", lambda state, request: AsyncCM(app_conversation_start_task_obj))
    monkeypatch.setattr(config_mod, "get_event_callback_service", lambda state, request: AsyncCM(event_callback_obj))
    monkeypatch.setattr(config_mod, "get_event_service", lambda state, request: AsyncCM(event_service_obj))
    monkeypatch.setattr(config_mod, "get_jwt_service", lambda state, request: AsyncCM(jwt_service_obj))
    monkeypatch.setattr(config_mod, "get_httpx_client", lambda state, request: AsyncCM(httpx_client_obj))
    monkeypatch.setattr(config_mod, "get_pending_message_service", lambda state, request: AsyncCM(pending_message_obj))

    # Also patch module-level reference
    monkeypatch.setattr(mod, "get_event_callback_service", lambda state, request: AsyncCM(event_callback_obj))

    # get_global_config returns a config with web_url set
    global_cfg = SimpleNamespace(web_url="https://example.com", openhands_provider_base_url="https://provider.example")
    monkeypatch.setattr(config_mod, "get_global_config", lambda: global_cfg)

    # Provide a dummy server_config module with app_mode == AppMode.SAAS
    import openhands.server.types as types_mod
    AppMode = types_mod.AppMode
    srv = types.SimpleNamespace(app_mode=types.SimpleNamespace(value=AppMode.SAAS))
    shared_mod = types.ModuleType("openhands.server.shared")
    shared_mod.server_config = srv
    monkeypatch.setitem(sys.modules, "openhands.server.shared", shared_mod)

    # Replace LiveStatusAppConversationService in module with dummy to capture kwargs
    captured = {}
    class DummyLiveStatus2:
        def __init__(self, *args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs

    monkeypatch.setattr(mod, "LiveStatusAppConversationService", DummyLiveStatus2)

    # Ensure DockerSandboxService type exists (not needed to trigger host.docker branch since web_url is set)
    monkeypatch.setattr(mod, "DockerSandboxService", DummyDocker2)

    # Create injector with tavily_api_key set
    injector = mod.LiveStatusAppConversationServiceInjector(tavily_api_key=SecretStr("SHOULD_NOT_BE_INCLUDED"))

    # Run async generator
    agen = injector.inject(state=None, request=None)
    svc = await agen.__anext__()
    await agen.aclose()

    kwargs = captured.get('kwargs', {})
    # web_url should be preserved from config
    assert kwargs.get('web_url') == "https://example.com"
    # Because app_mode is SAAS, tavily_api_key must be None
    assert kwargs.get('tavily_api_key') is None
    # access_token_hard_timeout still set to timedelta
    from datetime import timedelta
    assert isinstance(kwargs.get('access_token_hard_timeout'), timedelta)
    # check openhands_provider_base_url passed through
    assert kwargs.get('openhands_provider_base_url') == global_cfg.openhands_provider_base_url
