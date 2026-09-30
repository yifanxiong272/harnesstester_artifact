import types
import pytest

from openhands.runtime.impl.remote import remote_runtime as rrmodule

# shortcut to the bound function under test
_start_or_attach = rrmodule.RemoteRuntime._start_or_attach_to_runtime
AgentRuntimeNotFoundError = rrmodule.AgentRuntimeNotFoundError
RuntimeStatus = rrmodule.RuntimeStatus


class _FakeSandbox:
    def __init__(self, base_container_image=None, runtime_container_image=None):
        self.base_container_image = base_container_image
        self.runtime_container_image = runtime_container_image


class _FakeConfig:
    def __init__(self, sandbox: _FakeSandbox):
        self.sandbox = sandbox


def _make_fake_runtime(**overrides):
    """Create a minimal fake 'self' object suitable for calling the instance method.

    We purposely avoid constructing a real RemoteRuntime to keep tests deterministic
    and not depend on side effects. The fake object exposes the attributes and
    methods referenced by _start_or_attach_to_runtime.
    """
    fake = types.SimpleNamespace()
    # defaults
    fake.log_calls = []

    def log(level, message, exc_info=None):
        fake.log_calls.append((level, message))

    # default behaviours (can be overridden by passing in overrides)
    fake.log = log
    fake._check_existing_runtime = lambda: False
    fake._build_runtime = lambda: setattr(fake, "_built", True)
    fake._start_runtime = lambda: setattr(fake, "_started", True)
    fake._wait_until_alive = lambda: setattr(fake, "_waited", True)
    fake.set_runtime_status = lambda status: setattr(fake, "_status_set", status)

    # base attributes required by method
    fake.attach_to_existing = False
    fake.sid = "SOME-SID"
    fake.runtime_id = "RUNTIME-ID"
    fake.runtime_url = "http://runtime"
    fake.container_image = None

    # config.sandbox holds base_container_image and runtime_container_image
    fake.config = _FakeConfig(_FakeSandbox(base_container_image="base:latest"))

    # apply overrides
    for k, v in overrides.items():
        setattr(fake, k, v)

    return fake


def test_existing_runtime_keeps_runtime_and_waits_round_055():
    fake = _make_fake_runtime()
    # simulate existing runtime found
    fake._check_existing_runtime = lambda: True
    # ensure we are attaching to an existing runtime to exercise the branch
    fake.attach_to_existing = True

    # ensure runtime_id/runtime_url are present (avoid assertion)
    fake.runtime_id = "existing-id"
    fake.runtime_url = "http://existing"

    _start_or_attach(fake)

    # assert that the log recorded the use of existing runtime
    assert any("Using existing runtime" in msg for _, msg in fake.log_calls), (
        "Expected a log message indicating using existing runtime"
    )
    # _wait_until_alive is always called regardless of attach_to_existing
    assert getattr(fake, "_waited", False) is True
    # after finishing, set_runtime_status should be called with RuntimeStatus.READY
    assert getattr(fake, "_status_set") == RuntimeStatus.READY


def test_attach_to_existing_not_found_raises_round_055():
    fake = _make_fake_runtime()
    # no existing runtime
    fake._check_existing_runtime = lambda: False
    # but configured to attach to an existing runtime
    fake.attach_to_existing = True
    fake.sid = "SID-XYZ"

    with pytest.raises(AgentRuntimeNotFoundError) as excinfo:
        _start_or_attach(fake)

    # error message should reference the SID we set
    assert "SID-XYZ" in str(excinfo.value)
    # verify the failed-to-find log message was emitted prior to raising
    assert any("Failed to find existing runtime" in msg for _, msg in fake.log_calls)


def test_start_new_runtime_builds_image_when_runtime_image_missing_round_055():
    fake = _make_fake_runtime()
    # no existing runtime and not attaching -> start a new runtime
    fake._check_existing_runtime = lambda: False
    fake.attach_to_existing = False

    # runtime image not provided -> should build and use base image
    fake.config = _FakeConfig(_FakeSandbox(base_container_image="base:1.0", runtime_container_image=None))

    # ensure runtime id/url exist to avoid assertion (simulating build/start set them)
    fake.runtime_id = "new-id"
    fake.runtime_url = "http://new"

    # Replace _build_runtime/_start_runtime with functions that mark calls
    def build():
        fake._built = True
        # emulate that building sets some attribute (no real network call)
    def start():
        fake._started = True

    fake._build_runtime = build
    fake._start_runtime = start

    _start_or_attach(fake)

    # ensure build was invoked and container_image was set to base
    assert getattr(fake, "_built", False) is True
    assert fake.container_image == "base:1.0"
    # ensure start and wait were invoked
    assert getattr(fake, "_started", False) is True
    assert getattr(fake, "_waited", False) is True
    # final status set
    assert getattr(fake, "_status_set") == RuntimeStatus.READY


def test_start_new_runtime_uses_provided_runtime_image_round_055():
    fake = _make_fake_runtime()
    fake._check_existing_runtime = lambda: False
    fake.attach_to_existing = False

    # Provide a runtime image; code should set container_image to that and skip build
    fake.config = _FakeConfig(_FakeSandbox(base_container_image="base:1.0", runtime_container_image="custom:2.3"))
    fake.runtime_id = "rid"
    fake.runtime_url = "rurl"

    called = {"built": False}

    def build_mark():
        called["built"] = True

    fake._build_runtime = build_mark
    fake._start_runtime = lambda: setattr(fake, "_started", True)

    _start_or_attach(fake)

    # since runtime_container_image provided, _build_runtime should not be called
    assert called["built"] is False
    # container_image should reflect provided runtime image
    assert fake.container_image == "custom:2.3"
    assert getattr(fake, "_started", False) is True
    assert getattr(fake, "_waited", False) is True
    assert getattr(fake, "_status_set") == RuntimeStatus.READY
