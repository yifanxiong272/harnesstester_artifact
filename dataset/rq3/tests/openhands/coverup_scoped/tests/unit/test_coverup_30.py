# file: openhands/app_server/app_conversation/live_status_app_conversation_service.py:667-735
# asked: {"lines": [672, 674, 675, 679, 680, 681, 682, 685, 686, 688, 690, 691, 693, 694, 695, 698, 699, 702, 703, 704, 705, 707, 708, 711, 714, 715, 718, 719, 722, 727, 730, 731, 732, 733, 734], "branches": [[672, 674], [672, 690], [675, 679], [675, 688], [693, 694], [693, 695], [714, 715], [714, 718], [718, 719], [718, 722], [722, 727], [722, 730]]}
# gained: {"lines": [672, 674, 675, 679, 680, 681, 685, 686, 688, 690, 691, 693, 694, 698, 699, 702, 703, 704, 705, 707, 708, 711, 714, 715, 718, 719, 722, 727, 730, 731, 732, 733, 734], "branches": [[672, 674], [672, 690], [675, 679], [675, 688], [693, 694], [714, 715], [714, 718], [718, 719], [718, 722], [722, 727], [722, 730]]}

import types
from types import SimpleNamespace, MethodType
import pytest
import asyncio

from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationStartTaskStatus,
)
from openhands.app_server.sandbox.sandbox_models import SandboxStatus
from openhands.app_server.errors import SandboxError

from openhands.app_server.app_conversation import live_status_app_conversation_service as ls_module

# Helper to bind the class method to a simple namespace instance
def bind_wait_method():
    fn = ls_module.LiveStatusAppConversationService._wait_for_sandbox_start
    self = SimpleNamespace()
    # sensible defaults; tests will override as needed
    self.sandbox_startup_timeout = 123
    self.sandbox_startup_poll_frequency = 1.5
    self.httpx_client = "httpx-client-placeholder"
    return MethodType(fn, self), self


@pytest.mark.asyncio
async def test_no_sandbox_id_starts_new_sandbox_and_resumes_and_waits():
    wait_method, self = bind_wait_method()

    # Capture calls
    called = {}

    async def _find_running_sandbox_for_user():
        called['find_running'] = True
        return None

    async def start_sandbox(sandbox_id=None):
        # Should receive sandbox_id from conversation_id.hex
        called['started_with'] = sandbox_id
        # Return sandbox in PAUSED state to exercise resume path
        return SimpleNamespace(id="s1", status=SandboxStatus.PAUSED)

    async def resume_sandbox(sandbox_id):
        called['resumed'] = sandbox_id
        # simulate resume by doing nothing; status remains as originally returned

    async def wait_for_sandbox_running(sandbox_id, timeout, poll_interval, httpx_client):
        called['wait_called'] = {
            "id": sandbox_id,
            "timeout": timeout,
            "poll_interval": poll_interval,
            "httpx_client": httpx_client,
        }
        # simulate some async wait
        await asyncio.sleep(0)

    # Attach sandbox_service and helper to self
    self._find_running_sandbox_for_user = _find_running_sandbox_for_user
    self.sandbox_service = SimpleNamespace(
        start_sandbox=start_sandbox,
        resume_sandbox=resume_sandbox,
        wait_for_sandbox_running=wait_for_sandbox_running,
    )

    # Prepare a fake task with request.conversation_id having .hex and str conversion
    conversation_obj = SimpleNamespace(hex="convhex123")
    request = SimpleNamespace(sandbox_id=None, conversation_id=conversation_obj)
    task = SimpleNamespace(request=request, sandbox_id=None, status=None)

    agen = wait_method(task)
    # First yield returns the task
    yielded = await agen.__anext__()
    assert yielded is task
    # After first yield, task status and sandbox_id should be set
    assert task.status == AppConversationStartTaskStatus.WAITING_FOR_SANDBOX
    assert task.sandbox_id == "s1"
    # ensure start_sandbox received the conversation_id.hex
    assert called.get('started_with') == "convhex123"

    # Resume the generator to run resume and wait logic; generator is expected to complete,
    # so StopAsyncIteration is the normal outcome.
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    # Verify resume and wait were called with expected parameters
    assert called.get('resumed') == "s1"
    wait_info = called.get('wait_called')
    assert wait_info is not None
    assert wait_info["id"] == "s1"
    assert wait_info["timeout"] == self.sandbox_startup_timeout
    assert wait_info["poll_interval"] == self.sandbox_startup_poll_frequency
    assert wait_info["httpx_client"] == self.httpx_client


@pytest.mark.asyncio
async def test_provided_sandbox_id_not_found_raises_sandbox_error():
    wait_method, self = bind_wait_method()

    async def get_sandbox(sandbox_id):
        return None

    # Attach sandbox_service
    self.sandbox_service = SimpleNamespace(get_sandbox=get_sandbox)
    # request has sandbox_id set, so code will call get_sandbox and raise when None
    request = SimpleNamespace(sandbox_id="missing-id", conversation_id=None)
    task = SimpleNamespace(request=request, sandbox_id=None, status=None)

    agen = wait_method(task)
    with pytest.raises(SandboxError) as excinfo:
        await agen.__anext__()  # should raise before yielding
    assert "Sandbox not found" in str(excinfo.value)
    assert "missing-id" in str(excinfo.value)


@pytest.mark.asyncio
async def test_sandbox_status_none_raises_after_yield():
    wait_method, self = bind_wait_method()

    # Provide a running sandbox via _find_running_sandbox_for_user
    async def _find_running_sandbox_for_user():
        return SimpleNamespace(id="s2", status=None)

    self._find_running_sandbox_for_user = _find_running_sandbox_for_user
    # sandbox_service not needed for this path beyond having the attribute
    self.sandbox_service = SimpleNamespace()

    request = SimpleNamespace(sandbox_id=None, conversation_id=None)
    task = SimpleNamespace(request=request, sandbox_id=None, status=None)

    agen = wait_method(task)
    # first yield should succeed
    yielded = await agen.__anext__()
    assert yielded is task
    # second iteration should raise SandboxError due to None status
    with pytest.raises(SandboxError) as excinfo:
        await agen.__anext__()
    assert "Sandbox status: None" in str(excinfo.value)


@pytest.mark.asyncio
async def test_sandbox_not_startable_raises_after_yield():
    wait_method, self = bind_wait_method()

    # Provide a sandbox with a status that's not startable (e.g., MISSING)
    async def _find_running_sandbox_for_user():
        return SimpleNamespace(id="s3", status=SandboxStatus.MISSING)

    self._find_running_sandbox_for_user = _find_running_sandbox_for_user
    self.sandbox_service = SimpleNamespace()

    request = SimpleNamespace(sandbox_id=None, conversation_id=None)
    task = SimpleNamespace(request=request, sandbox_id=None, status=None)

    agen = wait_method(task)
    yielded = await agen.__anext__()
    assert yielded is task
    with pytest.raises(SandboxError) as excinfo:
        await agen.__anext__()
    assert "Sandbox not startable: s3" in str(excinfo.value)
