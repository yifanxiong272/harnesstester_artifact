import types
import pytest
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.core.exceptions import AgentRuntimeNotFoundError
from openhands.runtime.runtime_status import RuntimeStatus


def _make_runtime_stub(**attrs):
    """Create a RemoteRuntime instance without calling __init__ and attach attrs."""
    rt = object.__new__(RemoteRuntime)
    # Ensure a no-op logger exists to satisfy calls to self.log
    rt.log = lambda level, message, exc_info=None: None
    # Attach provided attributes
    for k, v in attrs.items():
        setattr(rt, k, v)
    return rt


def test_existing_runtime_uses_existing_round_055(monkeypatch):
    # Arrange: simulate that an existing runtime is found and runtime_id/runtime_url are set
    config = types.SimpleNamespace(sandbox=types.SimpleNamespace(runtime_container_image=None, base_container_image="base-img"))
    rt = _make_runtime_stub(
        config=config,
        attach_to_existing=False,
        sid="S-123",
        runtime_id="existing-rid",
        runtime_url="http://existing",
        container_image=None,
    )

    called = {}

    def fake_check():
        called["check"] = True
        return True

    def fake_wait():
        called["wait"] = True

    def fake_set_status(s):
        called["status"] = s

    # Patch instance methods used by _start_or_attach_to_runtime
    monkeypatch.setattr(rt, "_check_existing_runtime", fake_check, raising=False)
    # Ensure build/start are not called by making them raise if invoked
    monkeypatch.setattr(rt, "_build_runtime", lambda: (_ for _ in ()).throw(RuntimeError("_build_runtime should not be called")), raising=False)
    monkeypatch.setattr(rt, "_start_runtime", lambda: (_ for _ in ()).throw(RuntimeError("_start_runtime should not be called")), raising=False)
    monkeypatch.setattr(rt, "_wait_until_alive", fake_wait, raising=False)
    monkeypatch.setattr(rt, "set_runtime_status", fake_set_status, raising=False)

    # Act
    rt._start_or_attach_to_runtime()

    # Assert: existing path used, wait called, and runtime status set to READY
    assert called.get("check") is True
    assert called.get("wait") is True
    assert called.get("status") == RuntimeStatus.READY


def test_attach_to_existing_raises_round_055(monkeypatch):
    # Arrange: no existing runtime and attach_to_existing True should raise AgentRuntimeNotFoundError
    config = types.SimpleNamespace(sandbox=types.SimpleNamespace(runtime_container_image=None, base_container_image="base-img"))
    rt = _make_runtime_stub(
        config=config,
        attach_to_existing=True,
        sid="S-attach",
        runtime_id=None,
        runtime_url=None,
    )

    monkeypatch.setattr(rt, "_check_existing_runtime", lambda: False, raising=False)

    # Act & Assert: calling should raise the specific error
    with pytest.raises(AgentRuntimeNotFoundError):
        rt._start_or_attach_to_runtime()


def test_start_new_runtime_with_build_round_055(monkeypatch):
    # Arrange: no existing runtime, not attaching, and sandbox specifies no runtime_container_image => build path
    config = types.SimpleNamespace(sandbox=types.SimpleNamespace(runtime_container_image=None, base_container_image="base-img"))
    rt = _make_runtime_stub(
        config=config,
        attach_to_existing=False,
        sid="S-new-build",
        runtime_id=None,
        runtime_url=None,
        container_image=None,
    )

    called = {}

    def fake_check():
        called["check"] = True
        return False

    def fake_build():
        # Simulate that building sets runtime id/url
        called["build"] = True
        rt.runtime_id = "built-rid"
        rt.runtime_url = "http://built"

    def fake_start():
        called["start"] = True

    def fake_wait():
        called["wait"] = True

    def fake_set_status(s):
        called["status"] = s

    monkeypatch.setattr(rt, "_check_existing_runtime", fake_check, raising=False)
    monkeypatch.setattr(rt, "_build_runtime", fake_build, raising=False)
    monkeypatch.setattr(rt, "_start_runtime", fake_start, raising=False)
    monkeypatch.setattr(rt, "_wait_until_alive", fake_wait, raising=False)
    monkeypatch.setattr(rt, "set_runtime_status", fake_set_status, raising=False)

    # Act
    rt._start_or_attach_to_runtime()

    # Assert: build/start/wait executed and status set; runtime id/url available
    assert called.get("check") is True
    assert called.get("build") is True
    assert called.get("start") is True
    assert called.get("wait") is True
    assert called.get("status") == RuntimeStatus.READY
    assert rt.runtime_id == "built-rid"
    assert rt.runtime_url == "http://built"


def test_start_new_runtime_with_image_round_055(monkeypatch):
    # Arrange: no existing runtime, not attaching, and sandbox provides runtime_container_image => set container_image branch
    config = types.SimpleNamespace(sandbox=types.SimpleNamespace(runtime_container_image="provided-image", base_container_image="ignored"))
    rt = _make_runtime_stub(
        config=config,
        attach_to_existing=False,
        sid="S-new-image",
        runtime_id=None,
        runtime_url=None,
        container_image=None,
    )

    called = {}

    def fake_check():
        called["check"] = True
        return False

    def fake_start():
        called["start"] = True
        # Simulate start establishing runtime id/url
        rt.runtime_id = "started-rid"
        rt.runtime_url = "http://started"

    def fake_wait():
        called["wait"] = True

    def fake_set_status(s):
        called["status"] = s

    monkeypatch.setattr(rt, "_check_existing_runtime", fake_check, raising=False)
    monkeypatch.setattr(rt, "_start_runtime", fake_start, raising=False)
    monkeypatch.setattr(rt, "_wait_until_alive", fake_wait, raising=False)
    monkeypatch.setattr(rt, "set_runtime_status", fake_set_status, raising=False)

    # Act
    rt._start_or_attach_to_runtime()

    # Assert: chosen container image was applied, start/wait executed, status set, and runtime id/url present
    assert called.get("check") is True
    assert called.get("start") is True
    assert called.get("wait") is True
    assert called.get("status") == RuntimeStatus.READY
    assert rt.container_image == "provided-image"
    assert rt.runtime_id == "started-rid"
    assert rt.runtime_url == "http://started"
