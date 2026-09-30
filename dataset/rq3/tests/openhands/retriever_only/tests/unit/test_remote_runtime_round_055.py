import types
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.core.exceptions import AgentRuntimeNotFoundError


def make_stub_runtime():
    # Create an uninitialized RemoteRuntime instance (bypass __init__)
    r = object.__new__(RemoteRuntime)

    # recorders for assertions
    r.logged = []
    r.actions = []
    r.status_set = []

    # simple logger that records messages for assertions
    def _log(level, message, exc_info=None):
        r.logged.append((level, str(message)))

    r.log = _log

    # default attributes used by _start_or_attach_to_runtime
    r.runtime_id = None
    r.runtime_url = None
    r.sid = "SOME-SID"
    r.attach_to_existing = False
    r.container_image = None

    # default config sandbox
    r.config = SimpleNamespace(sandbox=SimpleNamespace(runtime_container_image=None, base_container_image="base-img"))

    # default no-op implementations (can be replaced per-test)
    r._check_existing_runtime = lambda: False

    def _build_runtime():
        r.actions.append("build")
        # building sets runtime id/url in our test stub to satisfy later asserts
        r.runtime_id = "built-id"
        r.runtime_url = "http://built"

    r._build_runtime = _build_runtime

    def _start_runtime():
        r.actions.append("start")
        # starting sets runtime id/url if not already set
        if r.runtime_id is None:
            r.runtime_id = "started-id"
        if r.runtime_url is None:
            r.runtime_url = "http://started"

    r._start_runtime = _start_runtime

    r._wait_until_alive = lambda: r.actions.append("waited")
    r.set_runtime_status = lambda s: r.status_set.append(s)

    return r


def test_existing_runtime_logs_and_ready_when_attach_false_round_055():
    r = make_stub_runtime()

    # Simulate that an existing runtime is present
    r._check_existing_runtime = lambda: True

    # Provide runtime id/url as would be available for existing runtime
    r.runtime_id = "existing-id"
    r.runtime_url = "http://existing"

    # Ensure attach_to_existing is False so logs about waiting/ready appear
    r.attach_to_existing = False

    # Call the method under test
    r._start_or_attach_to_runtime()

    # Assertions on logged messages to prove the existing-runtime branch ran
    messages = [m for _, m in r.logged]
    assert any("Starting or attaching to runtime" in m for m in messages), "start log missing"
    assert any("Using existing runtime with ID: existing-id" in m for m in messages), "existing runtime log missing"
    # Because attach_to_existing is False, we should see waiting/ready logs
    assert any("Waiting for runtime to be alive" in m for m in messages), "waiting log missing"
    assert any("Runtime is ready." in m for m in messages), "ready log missing"

    # Wait should have been invoked and status set to READY
    assert "waited" in r.actions
    assert RuntimeStatus.READY in r.status_set


def test_existing_runtime_with_attach_true_skips_waiting_logs_round_055():
    r = make_stub_runtime()

    # Existing runtime present
    r._check_existing_runtime = lambda: True
    r.runtime_id = "existing2"
    r.runtime_url = "http://existing2"

    # When attach_to_existing is True, code should not log waiting/ready messages
    r.attach_to_existing = True

    r._start_or_attach_to_runtime()

    messages = [m for _, m in r.logged]
    assert any("Using existing runtime with ID: existing2" in m for m in messages)
    # Ensure waiting/ready messages are NOT present
    assert not any("Waiting for runtime to be alive" in m for m in messages)
    assert not any("Runtime is ready." in m for m in messages)

    # _wait_until_alive should still be called even when attach_to_existing is True (the implementation calls it unconditionally)
    assert "waited" in r.actions
    assert RuntimeStatus.READY in r.status_set


def test_attach_to_existing_true_and_no_existing_raises_round_055():
    r = make_stub_runtime()

    # No existing runtime
    r._check_existing_runtime = lambda: False
    r.attach_to_existing = True
    r.sid = "MISSING-SID-123"

    with pytest.raises(AgentRuntimeNotFoundError) as excinfo:
        r._start_or_attach_to_runtime()

    # The exception message should include the SID to be observable
    assert "MISSING-SID-123" in str(excinfo.value)

    # The code logs an informational message about failing to find existing runtime
    assert any("Failed to find existing runtime for SID: MISSING-SID-123" in m for _, m in r.logged)


def test_start_new_runtime_build_and_start_when_no_image_round_055():
    r = make_stub_runtime()

    # No existing runtime and not attaching
    r._check_existing_runtime = lambda: False
    r.attach_to_existing = False

    # Ensure sandbox runtime_container_image is None -> triggers build path
    r.config.sandbox.runtime_container_image = None
    r.config.sandbox.base_container_image = "the-base"

    # Replace build/start to record and set ids
    called = {"built": False, "started": False}

    def build_stub():
        called["built"] = True
        r.runtime_id = "built-xyz"
        r.runtime_url = "http://built-xyz"

    def start_stub():
        called["started"] = True

    r._build_runtime = build_stub
    r._start_runtime = start_stub

    r._start_or_attach_to_runtime()

    # build and start must have been called
    assert called["built"] is True
    assert called["started"] is True

    # container_image should remain None (only set when runtime_container_image is provided)
    assert r.container_image is None

    # Status set to READY
    assert RuntimeStatus.READY in r.status_set
